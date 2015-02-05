# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os
import urllib
import urllib2
import webapp2

import endpoints
from protorpc import messages
from protorpc import message_types
from protorpc import remote

from google.appengine.api import app_identity


VM_MODULE = 'vm'


def is_development_server():
  return os.environ['SERVER_SOFTWARE'].startswith('Development')


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
    logging.info('Hit timeseries.add()')
    hostname = app_identity.get_default_version_hostname()
    # For local testing in dev server.
    if is_development_server():
      hostname = 'localhost:8081'
    else:
      hostname = '%s.%s' % (VM_MODULE, hostname)
    logging.info('hostname for VM module: %s', hostname)
    url = 'http://%s/vm' % hostname
    raw_data = {
        'metric': {'type': request.metric.metric_type,
                   'value': request.metric.value},
    }
    data = urllib.urlencode(raw_data)
    request = urllib2.Request(url, data)
    try:
      response = urllib2.urlopen(request)
    except urllib2.HTTPError as e:
      logging.error('Error in the VM backend: %s', e)
      raise endpoints.InternalServerErrorException(
          'Error in the VM backend, url=%s: %s' % (url, e))
    except urllib2.URLError as e:
      logging.error('Error reaching the VM backend: %s', e)
      raise endpoints.InternalServerErrorException(
          'Error reaching the VM backend: %s' % e)
    return message_types.VoidMessage()

app_endpoints = endpoints.api_server([Handler])

class MainHandler(webapp2.RequestHandler):
  def get(self):
    msg = 'There is nothing here. Go away.\n'
    self.response.headers['Content-Type'] = 'text/plain'
    self.response.out.write(msg)
    logging.debug('Hit /')

logging.basicConfig(level=logging.DEBUG)
app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ], debug=True)
