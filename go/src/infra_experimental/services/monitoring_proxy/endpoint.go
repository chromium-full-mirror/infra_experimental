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

	luciErrors "github.com/luci/luci-go/common/errors"
	log "github.com/luci/luci-go/common/logging"
	"golang.org/x/net/context"
)

const (
	// monitoringEndpoint is the URL of the monitoring endpoint.
	monitoringEndpoint = "https://www.googleapis.com/acquisitions/v1_mon_shared/storage"

	// monitoringEndpointUserAgent is the user agent string that should be
	// supplied to acquisitions endpoint requests.
	monitoringEndpointUserAgent = "Google-Acquisitions-Storage/1.1/python"
)

var (
	// endpointScopes are the set of OAuth2 scopes to request for the endpoint
	// client.
	endpointScopes = []string{
		userInfoEmailScope,
		"https://www.googleapis.com/auth/acquisitionsstorage",
	}
)

// endpointConfig is the set of configuration parameters for an endpoint client.
type endpointConfig struct {
	url string // The URL of the monitoring endpoint.

	serviceAccountJSONPath string // The path to the service account JSON file.
}

// addFlags adds the configuration's flags to the supplied FlagSet.
func (c *endpointConfig) addFlags(fs *flag.FlagSet) {
	fs.StringVar(&c.serviceAccountJSONPath, "endpoint_auth_path", "",
		"The path to the endpoint service account JSON credentials.")
	fs.StringVar(&c.url, "endpoint_url", c.url,
		"The URL of the monitoring endpoint.")
}

// endpointClient is a client for a proxy endpoint.
type endpointClient struct {
	*endpointConfig

	ctx    context.Context // The client's context.
	client *http.Client    // The authenticated HTTP client instance.
}

// newEndpointClient instantiates an endpoint client.
func newEndpointClient(ctx context.Context, config *endpointConfig) (*endpointClient, error) {
	if config.url == "" {
		return nil, errors.New("endpoint: you must supply a monitoring endpoint")
	}

	client, err := createServiceAccountClient(ctx, config.serviceAccountJSONPath, endpointScopes...)
	if err != nil {
		log.Errorf(log.SetError(ctx, err), "Failed to configure endpoint client.")
		return nil, errors.New("main: failed to configure endpoint client")
	}

	return &endpointClient{
		endpointConfig: config,
		ctx:            ctx,
		client:         client,
	}, nil
}

// send pushes the supplied binary blob to the endpoint proxy.
func (e *endpointClient) send(data []byte) error {
	return retryCall(e.ctx, "endpoint.send", func() error {
		var err error
		req, err := http.NewRequest("POST", e.url, bytes.NewReader(data))
		if err != nil {
			log.Errorf(log.SetError(e.ctx, err), "Failed to create HTTP request.")
			return err
		}
		req.Header.Add("content-type", protobufContentType)
		req.Header.Add("user-agent", monitoringEndpointUserAgent)

		resp, err := e.client.Do(req)
		if err != nil {
			// Treat a client error as transient.
			log.Warningf(log.SetError(e.ctx, err), "Failed proxy client request.")
			return luciErrors.Transient{Err: err}
		}
		defer resp.Body.Close()

		// Read the full response body. This will enable us to re-use the
		// connection.
		ioutil.ReadAll(resp.Body)

		if resp.StatusCode >= http.StatusOK {
			log.Debugf(e.ctx, "Message pushed successfully.")
			return nil
		}

		err = fmt.Errorf("http: server error (%s)", resp.StatusCode)
		if resp.StatusCode >= http.StatusInternalServerError {
			err = luciErrors.Transient{Err: err}
		}

		log.Fields{
			log.ErrorKey: err,
			"status":     resp.Status,
			"statusCode": resp.StatusCode,
		}.Warningf(e.ctx, "Proxy error.")
		return err
	})
}
