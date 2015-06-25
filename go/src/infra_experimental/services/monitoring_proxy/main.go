// Copyright 2015 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package main

import (
	"errors"
	"flag"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"runtime"
	"sync"
	"time"

	"github.com/luci/luci-go/common/clock"
	luciErrors "github.com/luci/luci-go/common/errors"
	log "github.com/luci/luci-go/common/logging"
	"github.com/luci/luci-go/common/parallel"
	"github.com/luci/luci-go/common/retry"
	"golang.org/x/net/context"
	"google.golang.org/cloud/pubsub"
)

const (
	// noMessageDelay is the amount of time to sleep after receiving no messages.
	noMessageDelay = 1 * time.Second

	// protobufContentType is MIME type for a protobuf header.
	protobufContentType = "application/x-protobuf"

	// EMail Scope.
	userInfoEmailScope = "https://www.googleapis.com/auth/userinfo.email"
)

type config struct {
	pubsub   pubsubConfig
	endpoint endpointConfig

	numWorkers int // Number of subscription worker goroutines.
}

// addFlags adds configuration flags to the supplied FlagSet.
func (c *config) addFlags(fs *flag.FlagSet) {
	c.pubsub.addFlags(fs)
	c.endpoint.addFlags(fs)

	fs.IntVar(&c.numWorkers, "workers", 1, "The number of subscription worker goroutines.")
}

// application represents the main application state.
type application struct {
	config *config

	pubsub   *pubsubClient
	endpoint *endpointClient

	shutdownOnce sync.Once
	shutdownC    chan struct{} // When closed, signals application to shut down.
}

// newApplication instanties a new application instance and its associated
// client instances.
func newApplication(ctx context.Context, c *config) (*application, error) {
	// Setup common context parameters.
	ctx, cancelFunc := context.WithCancel(ctx)
	ctx = retry.WithTransientOnly(retry.Use(ctx, exponentialBackoff))

	// Configure Pub/Sub object.
	pubsubClient, err := newPubSubClient(ctx, &c.pubsub)
	if err != nil {
		return nil, errors.New("main: failed to configure Pub/Sub client")
	}

	endpointClient, err := newEndpointClient(ctx, &c.endpoint)
	if err != nil {
		return nil, errors.New("main: failed to configure endpoint client")
	}

	// Create Endpoint client.
	app := application{
		config:    c,
		pubsub:    pubsubClient,
		endpoint:  endpointClient,
		shutdownC: make(chan struct{}),
	}

	// Monitor our shutdown singal. Cancel our context if it is closed.
	go func() {
		<-app.shutdownC

		log.Infof(ctx, "Shutdown signal received; cancelling context.")
		cancelFunc()
	}()

	return &app, nil
}

// run executes the application.
func (a *application) run(ctx context.Context) error {
	wg := sync.WaitGroup{}
	for i := 0; i < a.config.numWorkers; i++ {
		i := i
		wg.Add(1)
		go func(id int) {
			defer wg.Done()

			a.process(log.SetField(ctx, "worker", i))
		}(i)
	}

	wg.Wait()
	return nil
}

// shutdown signals the application to terminate.
func (a *application) shutdown() {
	a.shutdownOnce.Do(func() {
		close(a.shutdownC)
	})
}

// isShutdown tests if the application has received a shutdown signal.
func (a *application) isShutdown() bool {
	select {
	case <-a.shutdownC:
		return true
	default:
		return false
	}
}

// process runs in its own goroutine and continuously processes data in the
// configured subscription.
func (a *application) process(ctx context.Context) {
	for !a.isShutdown() {
		err := a.pubsub.pullMessages(func(msgs []*pubsub.Message) bool {
			log.Fields{
				"count": len(msgs),
			}.Infof(ctx, "Pull()ed messages from subscription.")

			if err := a.proxyMessages(ctx, msgs); err != nil {
				log.Errorf(log.SetError(ctx, err), "Error sending messages to proxy.")
			}
			return false
		})
		if err == errNoMessages {
			log.Fields{
				"delay": noMessageDelay,
			}.Infof(ctx, "Received no messages; sleeping for next round.")
			a.sleepWithInterrupt(ctx, noMessageDelay)
		} else if err != nil {
			log.Errorf(log.SetError(ctx, err), "process: Failed to Pull() round of messages.")
		}
	}
}

// sleepWithInterrupt attempts to sleep for the specified duration, aborting
// early if the application is shutdown, returning true.
func (a *application) sleepWithInterrupt(ctx context.Context, amount time.Duration) bool {
	select {
	case <-clock.After(ctx, noMessageDelay):
		return false
	case <-a.shutdownC:
		return true
	}
}

// proxyMessages forwards a set of pubsub messages to the endpoint proxy.
func (a *application) proxyMessages(ctx context.Context, msgs []*pubsub.Message) error {
	log.Fields{
		"size": len(msgs),
	}.Debugf(ctx, "Sending messages to Proxy.")

	// TODO: Batch messages together into larger pushes.
	err := parallel.FanOutIn(func(c chan<- func() error) {
		for _, msg := range msgs {
			c <- func() error {
				msg := msg
				ctx := log.SetFields(ctx, log.Fields{
					"size":      len(msg.Data),
					"messageID": msg.ID,
				})
				log.Debugf(ctx, "Sending data to monitoring endpoint.")

				// Execute the request.
				if err := a.endpoint.send(msg.Data); err != nil {
					log.Errorf(log.SetError(ctx, err), "Failed to push message to proxy.")
					return err
				}
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

// mainImpl is the main execution function.
func mainImpl(args []string) int {
	// Use all of teh corez.
	if os.Getenv("GOMAXPROCS") == "" {
		runtime.GOMAXPROCS(runtime.NumCPU())
	}

	// Increase idle connections per host, since we connect to basically two
	// hosts.
	if t, ok := http.DefaultTransport.(*http.Transport); ok {
		t.MaxIdleConnsPerHost = 10000
	}

	ctx := context.Background()
	loggerConfig := newLoggerConfig() // Internal logging config (cloud logging).
	logConfig := log.Config{Level: log.Debug}
	config := &config{}

	fs := flag.CommandLine
	config.addFlags(fs)
	loggerConfig.addFlags(fs)
	logConfig.AddFlags(fs)
	fs.Parse(args)

	// Setup local logging configuration.
	ctx, logFlushFunc, err := loggerConfig.use(ctx)
	if err != nil {
		fmt.Println("ERROR: Failed to setup logging:", err)
		return 2
	}
	defer logFlushFunc()

	// HACK: Fix this once LUCI logging CL lands.
	ctx = logConfig.Set(ctx)
	ctx = log.SetLevel(ctx, log.Debug)

	app, err := newApplication(ctx, config)
	if err != nil {
		log.Errorf(log.SetError(ctx, err), "Failed to setup application.")
		return 1
	}

	// Set up interrupt handler.
	signalC := make(chan os.Signal, 1)
	go func() {
		triggered := false
		for sig := range signalC {
			if !triggered {
				triggered = true

				log.Infof(log.SetField(ctx, "signal", sig),
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

	log.Infof(ctx, "Starting application execution...")
	if err := app.run(ctx); err != nil {
		log.Errorf(log.SetError(ctx, err), "Error during application execution.")
		return 1
	}

	return 0
}

func main() {
	os.Exit(mainImpl(os.Args[1:]))
}
