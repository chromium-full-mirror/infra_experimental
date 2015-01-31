# Copyright (c) 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os

import endpoints
from protorpc import messages
from protorpc import message_types
from protorpc import remote


class Metric(messages.Message):
  # TODO(sergeyberezin): make it enum type.
  metric_type = messages.StringField(1, required=True)
  # TODO(sergeyberezin): check if union of types is needed.
  value = messages.StringField(2)


class Field(messages.Message):
  field_name = messages.StringField(1, required=True)
  # TODO(sergeyberezin): see if we need a union of types.
  field_value = messages.StringField(2)


# TODO(sergeyberezin): add a check for #fields <= 7.
class Point(messages.Message):
  metric = messages.MessageField(Metric, 1, required=True)
  fields = messages.MessageField(Field, 2, repeated=True)


@endpoints.api(
    name='timeseries', version='v1',
    description=('Accept time series metrics and forwards to '
                'internal monitoring tools..'))
class Handler(remote.Service):
  """Handle Cloud Endpoints."""
  @endpoints.method(Point, message_types.VoidMessage,
                    name='point.add')
  def add(self, request):
    """Add an entry with a set of key:value tags."""
    logging.info('Hit point.add()')
    return message_types.VoidMessage()

app = endpoints.api_server([Handler])
