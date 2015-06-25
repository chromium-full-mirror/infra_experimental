// Copyright 2015 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package main

import (
	"errors"
	"flag"
	"fmt"

	luciErrors "github.com/luci/luci-go/common/errors"
	log "github.com/luci/luci-go/common/logging"
	"golang.org/x/net/context"
	"google.golang.org/cloud"
	"google.golang.org/cloud/pubsub"
)

const (
	// The maximum number of items that can be pulled from a subscription at once.
	maxSubscriptionPullSize = 100
)

var (
	// OAuth2 scopes to generate.
	pubsubScopes = []string{
		pubsub.ScopePubSub,
		userInfoEmailScope,
	}

	// Error returned by pullMessages to indicate that no messages were available.
	errNoMessages = errors.New("pubsub: no messages")
)

// pubsubConfig is the set of configuration parameters for a pubsubClient.
type pubsubConfig struct {
	project      string // The project name.
	topic        string // The topic name.
	subscription string // The subscription name.
	create       bool
	batchSize    int // The number of elements to pull from a subscription per batch.

	serviceAccountJSONPath string // The path to the service account JSON file.
}

// addFlags adds this configuration's set of flags to a FlagSet.
func (c *pubsubConfig) addFlags(fs *flag.FlagSet) {
	fs.StringVar(&c.serviceAccountJSONPath, "pubsub_auth_path", "",
		"The path to the Pub/Sub service account JSON credentials.")
	fs.StringVar(&c.project, "pubsub_project", "", "The name of the Pub/Sub project.")
	fs.StringVar(&c.subscription, "pubsub_subscription", "", "The name of the Pub/Sub subscription.")
	fs.StringVar(&c.topic, "pubsub_topic", "",
		"The name of the Pub/Sub topic. Needed if subscription must be created.")
	fs.IntVar(&c.batchSize, "pubsub_batch_size", maxSubscriptionPullSize,
		"The Pub/Sub batch size.")
	fs.BoolVar(&c.create, "pubsub_create", false,
		"Create the subscription and/or topic if they don't exist.")
}

// A pubsubClient interfaces with a Cloud Pub/Sub subscription.
type pubsubClient struct {
	*pubsubConfig

	ctx context.Context // A Context bound to PubSub authentication parameters.
}

// newPubSubClient instantiates a new Pub/Sub client.
//
// This method will also perform authentication and setup the topic/subscription
// if it isn't already set up.
func newPubSubClient(ctx context.Context, config *pubsubConfig) (*pubsubClient, error) {
	if config.project == "" {
		return nil, errors.New("pubsub: you must supply a project")
	}
	if config.subscription == "" {
		return nil, errors.New("pubsub: you must supply a subscription")
	}
	if config.batchSize <= 0 {
		return nil, errors.New("pubsub: batch size must be at least 1")
	} else if config.batchSize > maxSubscriptionPullSize {
		return nil, fmt.Errorf("pubsub: batch size cannot exceed %d", maxSubscriptionPullSize)
	}

	client, err := createServiceAccountClient(ctx, config.serviceAccountJSONPath, pubsubScopes...)
	if err != nil {
		log.Errorf(log.SetError(ctx, err), "Failed to load credentials.")
		return nil, err
	}

	p := pubsubClient{
		pubsubConfig: config,
		ctx:          cloud.WithContext(ctx, config.project, client),
	}

	// Ensure that our Subscription (and topic) exist.
	if err := p.setupSubscription(); err != nil {
		log.Errorf(log.SetError(ctx, err), "Failed to set up subscription.")
		return nil, err
	}

	return &p, nil
}

// setupSubscription asserts that the configured subscription exists. In doing
// so, it also asserts that the client credentials are valid with respect to the
// configured project/subscription.
//
// If the subscription doesn't exist, this method can create the subscription
// and (if missing) its topic, if the "create" flag is set.
func (p *pubsubClient) setupSubscription() error {
	exists := false
	log.Fields{
		"subscription": p.topic,
	}.Infof(p.ctx, "Checking for subscription existence.")
	if err := retryCall(p.ctx, "SubExists()", func() error {
		var err error
		exists, err = pubsub.SubExists(p.ctx, p.subscription)
		return p.wrapTransient(err)
	}); err != nil {
		log.Warningf(log.SetError(p.ctx, err),
			"Failed to test for subscription; assuming it doesn't exist.")
	}
	if exists {
		return nil
	}

	if !p.create {
		return errors.New("pubsub: subscription doesn't exist, not configured to create")
	}

	// Create the subscription if it doesn't exist.
	if p.topic == "" {
		log.Errorf(p.ctx, "Cannot create subscription; no topic was specified.")
		return errors.New("pubsub: cannot create subscription")
	}

	// Test if the topic exists...
	log.Fields{
		"topic": p.topic,
	}.Infof(p.ctx, "Checking for topic existence.")
	if err := retryCall(p.ctx, "TopicExists()", func() error {
		var err error
		exists, err = pubsub.TopicExists(p.ctx, p.topic)
		return p.wrapTransient(err)
	}); err != nil {
		log.Warningf(log.SetError(p.ctx, err),
			"Failed to test for topic; assuming it doesn't exist.")
	}

	if !exists {
		log.Fields{
			"topic": p.topic,
		}.Infof(p.ctx, "Creating topic.")
		if err := retryCall(p.ctx, "CreateTopic()", func() error {
			return pubsub.CreateTopic(p.ctx, p.topic)
		}); err != nil {
			log.Warningf(log.SetError(p.ctx, err),
				"Failed to create topic.")
			return errors.New("pubsub: cannot create topic")
		}
	}

	log.Fields{
		"topic":        p.topic,
		"subscription": p.subscription,
	}.Infof(p.ctx, "Creating pull subscription for topic.")
	if err := retryCall(p.ctx, "CreateSub()", func() error {
		return pubsub.CreateSub(p.ctx, p.subscription, p.topic, 0, "")
	}); err != nil {
		log.Warningf(log.SetError(p.ctx, err),
			"Failed to test for subscription; assuming it doesn't exist.")
		return errors.New("pubsub: failed to create subscription")
	}

	return nil
}

// pullMessages pulls a set of messages from the configured Subscription.
// If no messages are available, errNoMessages will be returned.
//
// handler is a method that returns true if there was a transient failure,
// indicating that the messages shouldn't be ACK'd.
func (p *pubsubClient) pullMessages(handler func([]*pubsub.Message) bool) error {
	var msgs []*pubsub.Message
	err := retryCall(p.ctx, "Pull()", func() error {
		var err error
		msgs, err = pubsub.Pull(p.ctx, p.subscription, p.batchSize)
		return p.wrapTransient(err)
	})
	if err != nil {
		return err
	}

	if len(msgs) == 0 {
		return errNoMessages
	}

	shouldAck := true
	defer func() {
		if shouldAck {
			if err := p.ackMessages(msgs); err != nil {
				log.Warningf(log.SetError(p.ctx, err), "Failed to ACK messages!")
			}
		} else {
			log.Debugf(p.ctx, "Refraining from ACKing messages.")
		}
	}()

	shouldAck = !handler(msgs)
	return nil
}

// ackMessages ACKs the supplied messages.
func (p *pubsubClient) ackMessages(messages []*pubsub.Message) error {
	messageIds := make([]string, len(messages))
	for idx, msg := range messages {
		messageIds[idx] = msg.AckID
	}

	ctx := log.SetFields(p.ctx, log.Fields{
		"count": len(messageIds),
	})
	err := retryCall(ctx, "Ack()", func() error {
		return p.wrapTransient(pubsub.Ack(ctx, p.subscription, messageIds...))
	})
	if err != nil {
		log.Errorf(log.SetError(ctx, err), "Failed to ACK messages.")
		return err
	}

	log.Debugf(ctx, "Successfully ACK messages.")
	return nil
}

// wrapTransient examines the supplied error. If it's not a recognized error
// value, it is treated as transient.
//
// This is because, at the moment, the transiant nature of the pubsub return
// codes is not discernable, so we will error on the side of caution (retry).
func (*pubsubClient) wrapTransient(err error) error {
	switch err {
	case nil:
		return nil

	case context.Canceled:
		return err

	default:
		return luciErrors.Transient{Err: err}
	}
}
