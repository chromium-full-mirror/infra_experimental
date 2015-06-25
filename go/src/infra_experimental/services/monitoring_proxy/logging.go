// Copyright 2015 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package main

import (
	"crypto/rand"
	"encoding/base64"
	"errors"
	"flag"
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/luci/luci-go/common/clock"
	log "github.com/luci/luci-go/common/logging"
	"github.com/luci/luci-go/common/logging/gologger"
	"github.com/luci/luci-go/common/retry"
	"golang.org/x/net/context"
	"golang.org/x/oauth2"
	"golang.org/x/oauth2/google"
	cloudlog "google.golang.org/api/logging/v1beta3"
	"google.golang.org/cloud/compute/metadata"
)

const (
	cloudLoggingGCEService = "compute.googleapis.com"

	// cloudLoggingBatchSize is the number of log messages that will be sent in a
	// single cloud logging publish request.
	cloudLoggingBatchSize = 20

	// Number of bytes of random number to read for a unique session ID.
	loggingSessionIDSize = 36
)

// loggerConfig is the configuration for logging.
type loggerConfig struct {
	gceAccount             string
	serviceAccountJSONPath string

	projectName string
	logsID      string

	serviceName  string
	zone         string
	resourceType string
	resourceID   string
	region       string
	userID       string
}

func newLoggerConfig() *loggerConfig {
	c := &loggerConfig{
		gceAccount: "default",
		logsID:     "monitoring_proxy",
	}
	if metadata.OnGCE() {
		c.preloadFromGCEMetadata()
	}
	return c
}

func (c *loggerConfig) addFlags(fs *flag.FlagSet) {
	fs.StringVar(&c.gceAccount, "logging_gce_account", c.gceAccount,
		"When using GCE logging, the name of the account to bind to.")
	fs.StringVar(&c.serviceAccountJSONPath, "logging_cloud_auth_path", "",
		"When specified, use these credentials and force cloud logging.")
	fs.StringVar(&c.logsID, "logging_cloud_logs_id", c.logsID,
		"For cloud logging, the log stream ID.")
	fs.StringVar(&c.serviceName, "logging_cloud_service", c.serviceName,
		"For cloud logging, the service name.")
	fs.StringVar(&c.projectName, "logging_cloud_project_name", c.projectName,
		"For cloud logging, the project name.")
	fs.StringVar(&c.resourceType, "logging_cloud_resource_type", c.resourceType,
		"For cloud logging, the instance name.")
	fs.StringVar(&c.resourceID, "logging_cloud_resource_id", c.resourceID,
		"For cloud logging, the instance ID.")
	fs.StringVar(&c.region, "logging_cloud_region", c.region,
		"For cloud logging, the region.")
	fs.StringVar(&c.userID, "logging_cloud_user", c.userID,
		"For cloud logging, the user ID.")
	fs.StringVar(&c.zone, "logging_cloud_zone", c.zone,
		"For cloud logging, the zone.")
}

// getLogger chooses a base logger instance to use.
//
// If we're running on GCE, we will use a "cloud logging" logger; otherwise,
// we will use a console logger.
//
// The returned function should be called on application termination to flush
// the logger.
func (c *loggerConfig) use(ctx context.Context) (context.Context, func(), error) {
	var client *http.Client
	if metadata.OnGCE() && c.gceAccount != "" {
		ts := google.ComputeTokenSource(c.gceAccount)
		client = oauth2.NewClient(ctx, ts)
	} else if c.serviceAccountJSONPath != "" {
		var err error
		client, err = createServiceAccountClient(ctx, c.serviceAccountJSONPath, cloudlog.CloudPlatformScope)
		if err != nil {
			return nil, nil, err
		}
	} else {
		// Not using cloud logging.
		return gologger.Use(ctx), func() {}, nil
	}

	if c.projectName == "" {
		return nil, nil, errors.New("logging: You must supply a project name")
	}
	if c.resourceType == "" {
		return nil, nil, errors.New("logging: You must supply a resource type")
	}
	if c.logsID == "" {
		return nil, nil, errors.New("logging: You must supply a logs ID")
	}

	// Generate a unique session ID via cyrpto.
	sessionID := make([]byte, loggingSessionIDSize)
	if _, err := rand.Read(sessionID); err != nil {
		return nil, nil, err
	}

	// Load GCE credentials for cloud logger.
	service, err := cloudlog.New(client)
	if err != nil {
		return nil, nil, err
	}
	clog := &cloudLogging{
		loggerConfig: c,

		ctx:          retry.Use(ctx, exponentialBackoff),
		sessionID:    base64.URLEncoding.EncodeToString(sessionID),
		service:      service,
		logC:         make(chan *logEntry),
		finishedC:    make(chan struct{}),
		commonLabels: make(map[string]string),
	}

	if c.resourceType != "" {
		clog.commonLabels["compute.googleapis.com/resource_type"] = c.resourceType
	}
	if c.resourceID != "" {
		clog.commonLabels["compute.googleapis.com/resource_id"] = c.resourceID
	}

	go func() {
		defer close(clog.finishedC)
		clog.process()
	}()

	ctx = log.SetFactory(ctx, func(c context.Context) log.Logger {
		return &boundCloudLogger{
			ctx:    c,
			logger: clog,
		}
	})

	return ctx, clog.finish, nil
}

func (c *loggerConfig) preloadFromGCEMetadata() {
	get := func(f func() (string, error), val *string) {
		v, err := f()
		if err == nil {
			*val = v
		}
	}

	c.serviceName = cloudLoggingGCEService
	get(metadata.ProjectID, &c.projectName)
	get(metadata.InstanceName, &c.resourceType)
	get(metadata.InstanceID, &c.resourceID)
	get(metadata.Zone, &c.zone)
}

// Snapshot of a log entry.
type logEntry struct {
	timestamp time.Time
	level     log.Level
	fmt       string
	args      []interface{}
	fields    log.Fields
}

func (e *logEntry) String() string {
	return fmt.Sprintf("Log[timestamp=%s, level=%s, message=%s, fields=%s]",
		e.timestamp, e.level, fmt.Sprintf(e.fmt, e.args...), e.fields)
}

// cloudLogging is a logger instance that logs to Google Cloud Logging.
type cloudLogging struct {
	*loggerConfig

	ctx       context.Context // The context that we were created with.
	sessionID string
	service   *cloudlog.Service
	logC      chan *logEntry
	finishedC chan struct{}

	commonLabels map[string]string
}

func (l *cloudLogging) finish() {
	close(l.logC)
	<-l.finishedC
}

// process is run in a separate goroutine to pull log entries and publish them
// to cloud logging.
func (l *cloudLogging) process() {
	entries := make([]*logEntry, cloudLoggingBatchSize)
	index := int64(0)
	for e := range l.logC {
		// Pull up to our entry capacity.
		entries[0] = e
		count := 1
		for count < len(entries) {
			found := false
			select {
			case moreE := <-l.logC:
				entries[count] = moreE
				count++
				found = true
			default:
				break
			}

			if !found {
				break
			}
		}

		if err := l.sendLogEntries(entries[:count], index); err != nil {
			// Output our transmission errors to STDOUT :(
			for idx, e := range entries[:count] {
				fmt.Printf("ERROR: Failed to publish log entry #%d. {error=%s, log=%s}\n", idx, err, e)
			}
		}
		index++
	}
}

func (l *cloudLogging) sendLogEntries(entries []*logEntry, index int64) error {
	if len(entries) == 0 {
		return nil
	}

	logEntries := make([]*cloudlog.LogEntry, len(entries))
	for idx, e := range entries {
		logEntries[idx] = l.buildLogEntry(e, index, int64(idx))
	}

	req := cloudlog.WriteLogEntriesRequest{
		CommonLabels: l.commonLabels,
		Entries:      logEntries,
	}

	svc := cloudlog.NewProjectsLogsEntriesService(l.service)
	call := svc.Write(l.projectName, l.logsID, &req)
	return retry.Retry(l.ctx, func() error {
		_, err := call.Do()
		return err
	}, func(err error, delay time.Duration) {
		// Write error to STDOUT.
		fmt.Printf("WARNING: Failed to send log entries {err=%s, delay=%s, entries=%s}\n",
			err, delay, entries)
	})
}

func (l *cloudLogging) buildLogEntry(e *logEntry, streamIndex, logIndex int64) *cloudlog.LogEntry {
	// Add logging fields to labels.
	labels := make(map[string]string, len(e.fields))
	for k, v := range e.fields {
		labels[k] = fmt.Sprintf("%v", v)
	}

	md := cloudlog.LogEntryMetadata{
		Labels:      l.commonLabels,
		ProjectId:   l.projectName,
		Region:      l.region,
		ServiceName: l.serviceName,
		Severity:    l.getSeverity(e.level),
		Timestamp:   l.formatTimestamp(e.timestamp),
		UserId:      l.userID,
		Zone:        l.zone,
	}

	text := fmt.Sprintf(e.fmt, e.args...)
	if len(e.fields) > 0 {
		text = strings.Join([]string{text, e.fields.FieldString(true)}, " ")
	}

	return &cloudlog.LogEntry{
		InsertId:    l.generateInsertID(streamIndex, logIndex),
		Metadata:    &md,
		TextPayload: text,
	}
}

func (l *cloudLogging) generateInsertID(streamIndex, logIndex int64) string {
	return fmt.Sprintf("%s-%d-%d", l.sessionID, streamIndex, logIndex)
}

func (*cloudLogging) getSeverity(l log.Level) string {
	switch l {
	case log.Debug:
		return "DEBUG"
	case log.Info:
		return "INFO"
	case log.Warning:
		return "WARNING"
	case log.Error:
		return "ERROR"

	default:
		return "DEFAULT"
	}
}

func (*cloudLogging) formatTimestamp(t time.Time) string {
	return t.UTC().Format(time.RFC3339Nano)
}

type boundCloudLogger struct {
	ctx    context.Context
	logger *cloudLogging
}

func (l *boundCloudLogger) Debugf(fmt string, args ...interface{}) {
	l.LogCall(log.Debug, 0, fmt, args)
}
func (l *boundCloudLogger) Infof(fmt string, args ...interface{}) {
	l.LogCall(log.Info, 0, fmt, args)
}
func (l *boundCloudLogger) Warningf(fmt string, args ...interface{}) {
	l.LogCall(log.Warning, 0, fmt, args)
}
func (l *boundCloudLogger) Errorf(fmt string, args ...interface{}) {
	l.LogCall(log.Error, 0, fmt, args)
}

func (l *boundCloudLogger) LogCall(level log.Level, calldepth int, fmt string, args []interface{}) {
	if len(fmt) == 0 {
		return
	}

	l.logger.logC <- &logEntry{
		timestamp: clock.Now(l.ctx),
		level:     level,
		fmt:       fmt,
		args:      args,
		fields:    log.GetFields(l.ctx),
	}
}
