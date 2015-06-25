// Copyright 2015 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package main

import (
	"errors"
	"io/ioutil"
	"net/http"
	"time"

	log "github.com/luci/luci-go/common/logging"
	"github.com/luci/luci-go/common/retry"
	"golang.org/x/net/context"
	"golang.org/x/oauth2/google"
)

// retryCall is a wrapper around the retry library that logs information about
// the retry attempts.
func retryCall(ctx context.Context, title string, f func() error) error {
	log.Debugf(ctx, "Executing retriable call %s.", title)
	err := retry.Retry(ctx, func() error {
		return f()
	}, func(err error, delay time.Duration) {
		log.Fields{
			log.ErrorKey: err,
			"delay":      delay,
		}.Warningf(ctx, "Transient error encountered during %s; retrying.", title)
	})
	if err != nil {
		log.Errorf(log.SetError(ctx, err), "Failed to %s.", title)
		return err
	}
	return nil
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

// createServiceAccountClient creates an http.Client instance that uses service
// account credentials loaded from a JSON file.
func createServiceAccountClient(ctx context.Context, path string, scopes ...string) (*http.Client, error) {
	ctx = log.SetField(ctx, "jsonPath", path)

	data, err := ioutil.ReadFile(path)
	if err != nil {
		log.Errorf(log.SetError(ctx, err), "client: Failed to read service account credentials JSON.")
		return nil, errors.New("Invalid 'auth_sa_json' parameter.")
	}

	conf, err := google.JWTConfigFromJSON(data, scopes...)
	if err != nil {
		log.Errorf(log.SetError(ctx, err),
			"client: Failed to create config from service account credentials JSON.")
		return nil, errors.New("Failed to load 'auth_sa_json' config.")
	}
	return conf.Client(ctx), nil
}
