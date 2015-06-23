// Copyright 2015 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package gcs

import (
	"errors"
	"flag"
	"io/ioutil"
	"net/http"

	log "github.com/luci/luci-go/common/logging"
	"golang.org/x/net/context"
	"golang.org/x/oauth2"
	"golang.org/x/oauth2/google"
	"google.golang.org/cloud"
)

var (
	DefaultScopes = []string{
		ScopeEmail,
	}
)

type ContextFlags struct {
	Project string // The project name to authenticate to.

	AuthGce            string // If not zero, authenticate using GCE metadata server.
	AuthSdk            string // If not zero, authenticate using local SDK credentials.
	ServiceAccountJson string // If not zero, load authentication from a service account JSON.
}

// Function for a method of generating an authenticated HTTP client.
type contextClientFunc func(context.Context, []string) (*http.Client, error)

// Add standard ContextFlags flags to a FlagSet.
func (f *ContextFlags) AddFlags(fs *flag.FlagSet) {
	fs.StringVar(&f.Project, "auth_project", "",
		"The project name to authenticate to.")
	fs.StringVar(&f.AuthGce, "auth_gce", "",
		"Authenticate using the Google Compute Engine (GCE) metadata server. "+
			"Set to '-' for default account. Only valid on GCE systems.")
	fs.StringVar(&f.AuthSdk, "auth_sdk", "",
		"Authenticate using an SDK account. Set to '-' to use the current `gcloud auth login`.")
	fs.StringVar(&f.ServiceAccountJson, "auth_sa_json", "",
		"Authenticate using a service account credentials stored at this path.")
}

// Returns the configured client function.
func (f *ContextFlags) getClientFunc() (contextClientFunc, error) {
	var cf []contextClientFunc

	if f.AuthGce != "" {
		cf = append(cf, f.createGceClient)
	}
	if f.AuthSdk != "" {
		cf = append(cf, f.createSdkClient)
	}
	if f.ServiceAccountJson != "" {
		cf = append(cf, f.createServiceAccountClient)
	}

	switch len(cf) {
	case 0:
		return f.defaultClient, nil

	case 1:
		return cf[0], nil

	default:
		return nil, errors.New("gcs: At most one authentication method may be supplied.")
	}
}

// Validates that the context flag configuration is reasonable.
func (f *ContextFlags) Validate() error {
	if f.Project == "" {
		return errors.New("Missing authentication project (-auth_project).")
	}

	if _, err := f.getClientFunc(); err != nil {
		return err
	}
	return nil
}

// Creates a new OAuth2-authenticated http.Client.
func (f *ContextFlags) CreateClient(ctx context.Context, scopes ...string) (
	*http.Client, error) {
	cf, err := f.getClientFunc()
	if err != nil {
		return nil, err
	}

	c, err := cf(ctx, scopes)
	if err != nil {
		log.Errorf(log.SetError(ctx, err),
			"Failed to create authenticated HTTP client.")
		return nil, err
	}
	return c, nil
}

// Creates a new OAuth2 Context.
func (f *ContextFlags) CreateContext(ctx context.Context, scopes ...string) (
	context.Context, error) {
	if f.Project == "" {
		return nil, errors.New("gcs: No project specified.")
	}

	c, err := f.CreateClient(ctx, scopes...)
	if err != nil {
		return nil, err
	}
	return cloud.WithContext(ctx, f.Project, c), nil
}

func (f *ContextFlags) defaultClient(ctx context.Context, scopes []string) (
	*http.Client, error) {
	return google.DefaultClient(context.Background(), scopes...)
}

// Returns an HTTP client authenticated using an OAuth2 token supplied by the
// Google Compute Engine token service.
func (f *ContextFlags) createGceClient(ctx context.Context, scopes []string) (
	*http.Client, error) {
	var account string
	if f.AuthGce != "-" {
		account = f.AuthGce
	}

	return &http.Client{
		Transport: &oauth2.Transport{
			Source: google.ComputeTokenSource(account),
		},
	}, nil
}

// Returns an HTTP client authenticated using an OAuth2 token supplied by the
// Google Compute Engine token service.
func (f *ContextFlags) createSdkClient(ctx context.Context, scopes []string) (
	*http.Client, error) {
	var account string
	if f.AuthSdk != "-" {
		account = f.AuthSdk
	}

	conf, err := google.NewSDKConfig(account)
	if err != nil {
		log.Errorf(log.SetFields(ctx, log.Fields{
			log.ErrorKey: err,
			"component":  "gcs",
			"account":    account,
		}), "gcs: Failed to create SDK context.")
		return nil, errors.New("Failed to create SDK config instance.")
	}

	return conf.Client(oauth2.NoContext), nil
}

// Returns an HTTP client authenticated using an OAuth2 token supplied by the
// Google Compute Engine token service.
func (f *ContextFlags) createServiceAccountClient(ctx context.Context, scopes []string) (
	*http.Client, error) {
	data, err := ioutil.ReadFile(f.ServiceAccountJson)
	if err != nil {
		log.Errorf(log.SetFields(ctx, log.Fields{
			log.ErrorKey: err,
			"component":  "gcs",
			"jsonPath":   f.ServiceAccountJson,
		}), "gcs: Failed to read service account credentials JSON.")
		return nil, errors.New("Invalid 'auth_sa_json' parameter.")
	}

	conf, err := google.JWTConfigFromJSON(data, scopes...)
	if err != nil {
		log.Errorf(log.SetFields(ctx, log.Fields{
			log.ErrorKey: err,
			"component":  "gcs",
			"jsonPath":   f.ServiceAccountJson,
		}), "gcs: Failed to create config from service account credentials JSON.")
		return nil, errors.New("Failed to load 'auth_sa_json' config.")
	}
	return conf.Client(oauth2.NoContext), nil
}
