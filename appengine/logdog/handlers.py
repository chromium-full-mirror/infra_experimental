# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import webapp2


class MainHandler(webapp2.RequestHandler):
  def get(self):
    self.redirect('/_ah/api/explorer')


def get_frontend_routes():  # pragma: no cover
  return [
      webapp2.Route(r'/', MainHandler),
  ]


def get_backend_routes():
  return [
  ]
