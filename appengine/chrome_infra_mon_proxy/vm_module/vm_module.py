# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import logging
import os
import webapp2

from google.appengine.api import app_identity


def is_development_server():
  return os.environ['SERVER_SOFTWARE'].startswith('Development')


class VMHandler(webapp2.RequestHandler):
  def get(self):
    msg = 'This endpoint is for POST requests only. Go away.\n'
    self.response.headers['Content-Type'] = 'text/plain'
    self.response.out.write(msg)
    logging.info('Hit / (info)')
    logging.debug('Hit / (debug)')

  def post(self):
    requester_id = self.request.headers.get('X-Appengine-Inbound-Appid', None)
    my_id = app_identity.get_application_id()
    hostname = app_identity.get_default_version_hostname()
    logging.debug('dev: %s, requester id: %s, my app id: %s, hostname: %s',
                  is_development_server(), requester_id, my_id, hostname)
    if not is_development_server() and requester_id != my_id:
      self.abort(403)
    logging.debug('Authenticated post request to a VM')

    try:
      packets = map(json.loads, self.request.get_all('p'))
      for packet in packets:
        if not isinstance(packet, dict):
          raise ValueError('JSON dictionary expected.')
    except ValueError as e:
      logging.warning('Invalid packet: %s\n%s', e, traceback.format_exc())
      self.response.write('Invalid packet: %s' % e)
      return

    logging.debug('Got %d packets', len(packets))
    for packet in packets:
      # TODO(sergeyberezin): call ts_mon library here.
      logging.debug('Got packet: %r', packet)


logging.basicConfig(level=logging.DEBUG)
app = webapp2.WSGIApplication([
    (r'/vm', VMHandler),
    ], debug=True)
