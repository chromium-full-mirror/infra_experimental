// Copyright 2015 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package main

import (
	"bytes"
	"errors"
	"flag"
	"fmt"
	"io/ioutil"
	"net/http"
	"os"
	"os/signal"
	"runtime"
	"sync"
	"time"

	"infra_experimental/services/monitoring_proxy/gcs"

	"github.com/luci/luci-go/client/internal/flags/nestedflagset"
	"github.com/luci/luci-go/common/clock"
	luciErrors "github.com/luci/luci-go/common/errors"
	"github.com/luci/luci-go/common/logging"
	"github.com/luci/luci-go/common/logging/gologger"
	"github.com/luci/luci-go/common/parallel"
	"github.com/luci/luci-go/common/retry"
	"golang.org/x/net/context"
	"google.golang.org/cloud"
	"google.golang.org/cloud/compute/metadata"
	"google.golang.org/cloud/pubsub"
)

const (
	// The maximum number of items that can be pulled from a subscription at once.
	maxSubscriptionPullSize = 100

	// noMessageDelay is the amount of time to sleep after receiving no messages.
	noMessageDelay = 1 * time.Second

	// protobufContentType is MIME type for a protobuf header.
	protobufContentType = "application/x-protobuf"

	// monitoringEndpoint is the URL of the monitoring endpoint.
	monitoringEndpoint = "https://www.googleapis.com/acquisitions/v1_mon_shared/storage"

	// monitoringEndpointUserAgent is the user agent string that should be
	// supplied to acquisitions endpoint requests.
	monitoringEndpointUserAgent = "Google-Acquisitions-Storage/1.1/python"

	// EMail Scope.
	userInfoEmailScope = "https://www.googleapis.com/auth/userinfo.email"
)

var (
	// OAuth2 scopes to generate.
	pubsubScopes = []string{
		pubsub.ScopePubSub,
		userInfoEmailScope,
	}

	endpointScopes = []string{
		userInfoEmailScope,
		"https://www.googleapis.com/auth/acquisitionsstorage",
	}
)

// application represents the main application state.
type application struct {
	monitoringEndpoint string // The URL of the monitoring endpoint.
	project            string // The PubSub project name.
	topic              string // The PubSub topic name.
	subscription       string // The PubSub subscription name.
	batchSize          int    // The number of elements to pull from a subscription per batch.

	pubsubAuth              gcs.ContextFlags
	endpointAuth            gcs.ContextFlags
	endpointMetadataAccount string

	numWorkers     int // Number of subscription worker goroutines.
	endpointClient *http.Client

	shutdownOnce sync.Once
	shutdownC    chan struct{} // When closed, signals application to shut down.
}

func newApplication() *application {
	return &application{
		shutdownC: make(chan struct{}),
	}
}

func (a *application) addFlags(fs *flag.FlagSet) {
	fs.StringVar(&a.monitoringEndpoint, "monitoring_endpoint", monitoringEndpoint,
		"The URL of the monitoring endpoint.")
	fs.StringVar(&a.project, "pubsub_project", "", "The name of the Pub/Sub project.")
	fs.StringVar(&a.subscription, "pubsub_subscription", "", "The name of the Pub/Sub subscription.")
	fs.StringVar(&a.topic, "pubsub_topic", "",
		"The name of the Pub/Sub topic. Needed if subscription must be created.")
	fs.IntVar(&a.batchSize, "pubsub_batch_size", maxSubscriptionPullSize,
		"The Pub/Sub batch size.")
	fs.IntVar(&a.numWorkers, "workers", 1, "The number of subscription worker goroutines.")

	pubsubAuth := nestedflagset.FlagSet{}
	a.pubsubAuth.AddFlags(&pubsubAuth.F)
	fs.Var(&pubsubAuth, "pubsub_auth", "Pub/Sub Authentication parameters.")

	endpointAuth := nestedflagset.FlagSet{}
	a.endpointAuth.AddFlags(&endpointAuth.F)
	fs.Var(&endpointAuth, "endpoint_auth", "Endpoint authentication parameters.")
	fs.StringVar(&a.endpointMetadataAccount, "endpoint_metadata_auth", "",
		"Configure endpoint authentication using GCE-stored metadata. If supplied, this "+
			"parameter is the name of the account (can use 'default'), and preempts the "+
			"-endpoint_auth flag.")
}

func (a *application) run(ctx context.Context) error {
	if a.monitoringEndpoint == "" {
		return errors.New("main: you must supply a monitoring endpoint")
	}
	if a.project == "" {
		return errors.New("main: you must supply a project")
	}
	if a.subscription == "" {
		return errors.New("main: you must supply a subscription")
	}
	if a.batchSize <= 0 {
		return errors.New("main: batch size must be at least 1")
	} else if a.batchSize > maxSubscriptionPullSize {
		return fmt.Errorf("main: batch size cannot exceed %d", maxSubscriptionPullSize)
	}

	// Increase idle connections per host, since we connect to basically two
	// hosts.
	if t, ok := http.DefaultTransport.(*http.Transport); ok {
		t.MaxIdleConnsPerHost = 10000
	}

	// Configure Pub/Sub Authentication context.
	pubsubClient, err := a.pubsubAuth.CreateClient(ctx, pubsubScopes...)
	if err != nil {
		logging.Errorf(logging.SetError(ctx, err), "Failed to configure Pub/Sub client.")
		return errors.New("main: failed to configure Pub/Sub client")
	}

	// Create Endpoint client.
	a.endpointClient, err = a.getEndpointClient(ctx)
	if err != nil {
		return errors.New("main: failed to configure endpoint client")
	}

	// Use Pub/Sub context as the primary context.
	ctx = cloud.WithContext(ctx, a.project, pubsubClient)

	// Test subscription availability.
	ctx, cancelFunc := context.WithCancel(ctx)
	go func() {
		<-a.shutdownC

		logging.Infof(ctx, "Shutdown signal received; cancelling context.")
		cancelFunc()
	}()
	ctx = retry.WithTransientOnly(retry.Use(ctx, exponentialBackoff))

	exists := false
	logging.Fields{
		"subscription": a.topic,
	}.Infof(ctx, "Checking for subscription existence.")
	if err := retryCall(ctx, "SubExists()", func() (err error) {
		exists, err = pubsub.SubExists(ctx, a.subscription)
		return
	}); err != nil {
		logging.Warningf(logging.SetError(ctx, err),
			"Failed to test for subscription; assuming it doesn't exist.")
	}

	// Create the subscription if it doesn't exist.
	if !exists {
		if a.topic == "" {
			logging.Errorf(ctx, "Cannot create subscription; no topic was specified.")
			return errors.New("main: cannot create subscription.")
		}

		// Test if the topic exists...
		exists = false
		logging.Fields{
			"topic": a.topic,
		}.Infof(ctx, "Checking for topic existence.")
		if err := retryCall(ctx, "TopicExists()", func() (err error) {
			exists, err = pubsub.TopicExists(ctx, a.topic)
			return
		}); err != nil {
			logging.Warningf(logging.SetError(ctx, err),
				"Failed to test for topic; assuming it doesn't exist.")
		}

		if !exists {
			logging.Fields{
				"topic": a.topic,
			}.Infof(ctx, "Creating topic.")
			if err := retryCall(ctx, "CreateTopic()", func() error {
				return pubsub.CreateTopic(ctx, a.topic)
			}); err != nil {
				logging.Warningf(logging.SetError(ctx, err),
					"Failed to create topic.")
				return errors.New("main: cannot create topic")
			}
		}

		logging.Fields{
			"topic":        a.topic,
			"subscription": a.subscription,
		}.Infof(ctx, "Creating pull subscription for topic.")
		if err := retryCall(ctx, "CreateSub()", func() error {
			return pubsub.CreateSub(ctx, a.subscription, a.topic, 0, "")
		}); err != nil {
			logging.Warningf(logging.SetError(ctx, err),
				"Failed to test for subscription; assuming it doesn't exist.")
			return errors.New("main: failed to create subscription")
		}
	}

	wg := sync.WaitGroup{}
	for i := 0; i < a.numWorkers; i++ {
		i := i
		wg.Add(1)
		go func(id int) {
			defer wg.Done()

			a.process(logging.SetField(ctx, "worker", i))
		}(i)
	}

	wg.Wait()
	return nil
}

func (a *application) shutdown() {
	a.shutdownOnce.Do(func() {
		close(a.shutdownC)
	})
}

func (a *application) isShutdown() bool {
	select {
	case <-a.shutdownC:
		return true
	default:
		return false
	}
}

// Continuously processes data in the configured subscription.
func (a *application) process(ctx context.Context) {
	for !a.isShutdown() {
		var msgs []*pubsub.Message
		if err := retryCall(ctx, "Pull()", func() (err error) {
			msgs, err = pubsub.Pull(ctx, a.subscription, a.batchSize)
			return
		}); err != nil {
			logging.Errorf(logging.SetError(ctx, err), "process: Failed to Pull() round of messages.")
			continue
		}

		if len(msgs) == 0 {
			logging.Fields{
				"delay": noMessageDelay,
			}.Infof(ctx, "Received no messages; sleeping for next round.")

			select {
			case <-clock.After(ctx, noMessageDelay):
				break
			case <-a.shutdownC:
				break
			}
			continue
		}

		// Process messages.
		func() {
			logging.Fields{
				"count": len(msgs),
			}.Infof(ctx, "Pull()ed messages from subscription.")

			messageIds := make([]string, len(msgs))
			for idx, msg := range msgs {
				messageIds[idx] = msg.AckID
			}

			// Acknowledge after processing.
			defer func() {
				logging.Fields{
					"count": len(messageIds),
				}.Infof(ctx, "ACK()ing messages.")
				if err := retryCall(ctx, "Ack()", func() error {
					return pubsub.Ack(ctx, a.subscription, messageIds...)
				}); err != nil {
					logging.Errorf(logging.SetError(ctx, err), "Failed to ACK messages.")
				}
			}()

			if err := a.proxyMessages(ctx, msgs); err != nil {
				logging.Errorf(logging.SetError(ctx, err), "Failed to proxy messages.")
			}
		}()
	}
}

func (a *application) proxyMessages(ctx context.Context, msgs []*pubsub.Message) error {
	ctx = logging.SetField(ctx, "endpoint", a.monitoringEndpoint)
	logging.Fields{
		"size": len(msgs),
	}.Debugf(ctx, "Sending messages to Proxy.")

	// TODO: Batch messages together into larger pushes.
	err := parallel.FanOutIn(func(c chan<- func() error) {
		for _, msg := range msgs {
			c <- func() error {
				logging.Fields{
					"url":  a.monitoringEndpoint,
					"size": len(msg.Data),
				}.Debugf(ctx, "Sending data to monitoring endpoint.")

				req, err := http.NewRequest("POST", a.monitoringEndpoint, bytes.NewReader(msg.Data))
				if err != nil {
					logging.Errorf(logging.SetError(ctx, err), "Failed to create HTTP request.")
					return err
				}
				req.Header.Add("content-type", protobufContentType)
				req.Header.Add("user-agent", monitoringEndpointUserAgent)

				// Execute the request.
				resp, err := a.endpointClient.Do(req)
				if err != nil {
					logging.Errorf(logging.SetError(ctx, err), "Failed to proxy message.")
					return err
				}
				defer resp.Body.Close()

				// Read the full response body. This will enable us to re-use the
				// connection.
				ioutil.ReadAll(resp.Body)
				return nil
			}
		}
	})

	if e, ok := err.(luciErrors.MultiError); ok {
		if len(e) == 0 {
			return nil
		}
	}
	return err
}

func (a *application) getEndpointClient(ctx context.Context) (*http.Client, error) {
	if a.endpointMetadataAccount != "" {
		if !metadata.OnGCE() {
			return nil, errors.New("main: not on GCE")
		}
		return nil, errors.New("main: metadata config not implemented")
	}

	endpointClient, err := a.endpointAuth.CreateClient(ctx, endpointScopes...)
	if err != nil {
		logging.Errorf(logging.SetError(ctx, err), "Failed to configure endpoint client.")
		return nil, errors.New("main: failed to configure endpoint client")
	}
	return endpointClient, nil
}

func retryCall(ctx context.Context, title string, f func() error) error {
	logging.Debugf(ctx, "Executing retriable call %s.", title)
	if err := retry.Retry(ctx, func() error {
		return maybeTransient(f())
	}, func(err error, delay time.Duration) {
		logging.Fields{
			logging.ErrorKey: err,
			"delay":          delay,
		}.Warningf(ctx, "process: Failed to %s, retrying.", title)
	}); err != nil {
		logging.Errorf(logging.SetError(ctx, err), "Failed to %s.", title)
		return err
	}
	return nil
}

func maybeTransient(err error) error {
	switch err {
	case nil:
		return nil

	case context.Canceled:
		return err

	default:
		return luciErrors.Transient{err}
	}
}

// exponentialBackoff is a retry.Factory that returns exponential backoff
// settings.
func exponentialBackoff(context.Context) retry.Iterator {
	return &retry.ExponentialBackoff{
		Limited: retry.Limited{
			Delay:   200 * time.Millisecond,
			Retries: 4,
		},
		Multiplier: 2,
	}
}

func mainImpl() int {
	if os.Getenv("GOMAXPROCS") == "" {
		runtime.GOMAXPROCS(runtime.NumCPU())
	}

	ctx := context.Background()

	app := newApplication()
	loggingConfig := logging.Config{Level: logging.Debug}

	fs := flag.CommandLine
	app.addFlags(fs)
	loggingConfig.AddFlags(fs)
	fs.Parse(os.Args[1:])

	// HACK: Fix this once LUCI logging CL lands.
	ctx = gologger.Use(ctx)
	ctx = loggingConfig.Set(ctx)
	ctx = logging.SetLevel(ctx, logging.Debug)

	// Set up interrupt handler.
	signalC := make(chan os.Signal, 1)
	go func() {
		triggered := false
		for sig := range signalC {
			if !triggered {
				triggered = true

				logging.Infof(logging.SetField(ctx, "signal", sig),
					"Received signal; starting shutdown.")
				app.shutdown()
			} else {
				// Triggered multiple times; immediately shut down.
				os.Exit(1)
			}
		}
	}()
	signal.Notify(signalC, os.Interrupt, os.Kill)
	defer func() {
		signal.Stop(signalC)
		close(signalC)
	}()

	logging.Infof(ctx, "Starting application execution...")
	if err := app.run(ctx); err != nil {
		logging.Errorf(logging.SetError(ctx, err), "Error during application execution.")
		return 1
	}

	return 0
}

func main() {
	os.Exit(mainImpl())
}
