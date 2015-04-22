# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import hashlib
import json
import logging
import os
import sys
import webapp2

from google.appengine.ext import ndb
from google.appengine.api import users
from webapp2_extras import jinja2

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, 'components', 'third_party'))

from components import auth


CONFIG_DATA_KEY = 'config_data_key'


def is_development_server():
  return os.environ.get('SERVER_SOFTWARE', '').startswith('Development')


def require_group_membership(group_name):
  """Skip authorization for dev appserver."""
  if is_development_server():
    auth_decorator = auth.public
  else:
    auth_decorator = auth.require( # pragma: no branch
        lambda: auth.is_group_member(group_name))

  def decorator(fn):
    return auth_decorator(fn)
  return decorator


class LoadTestData(ndb.Model):
  """Store load test data.

  To start a load test, set qps to a positive value.
  """
  url = ndb.StringProperty()
  qps = ndb.IntegerProperty(default=0)
  payload_size = ndb.IntegerProperty(default=1024)
#  instances = ndb.IntegerProperty(default=1)
  credentials = ndb.JsonProperty()
  scopes = ndb.StringProperty(repeated=True)
  headers = ndb.JsonProperty(default={})


def payload_stats(data):
  md5 = hashlib.md5()
  md5.update(data)
  md5hex = md5.hexdigest()
  return 'type=%s, %d bytes, md5=%s' % (type(data), len(data), md5hex)


class BaseHandler(webapp2.RequestHandler):
  """Provide a cached Jinja environment to each request."""

  def __init__(self, *args, **kwargs):
    webapp2.RequestHandler.__init__(self, *args, **kwargs)

  @staticmethod
  def jinja2_factory(app):
    template_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), 'templates'))
    config = {'template_path': template_dir}
    jinja = jinja2.Jinja2(app, config=config)
    return jinja

  @webapp2.cached_property
  def jinja2(self):
    # Returns a Jinja2 renderer cached in the app registry.
    return jinja2.get_jinja2(
        app=self.app, factory=BaseHandler.jinja2_factory)

  def render_response(self, _template, **context):
    # Renders a template and writes the result to the response.
    rv = self.jinja2.render_template(_template, **context)
    self.response.write(rv)


class AdminCommand(object):
  """Base class for administrative commands.

  Implement get() and post() methods in the subclasses.
  """

  def __init__(self, handler):
    self._handler = handler

  @property
  def request(self):
    return self._handler.request

  @property
  def response(self):
    return self._handler.response

  def render_response(self, _template, **context):
    self._handler.render_response(_template, **context)


class AdminPage(AdminCommand):
  """Display the admin page."""

  def get(self):
    context = {'title': 'Admin: Chrome Infra Loadtest'}
    self.render_response('admin.html', **context)

  def post(self):
    self.response.set_status(403)
    return


def setParams(params, data):
  params['url'] = data.url
  params['qps'] = data.qps
  params['payload_size'] = data.payload_size
  params['credentials'] = json.dumps(data.credentials)
  params['scopes'] = '\n'.join(data.scopes)
  params['headers'] = json.dumps(data.headers)

_parsers = {
    'url': lambda v: v,
    'qps': lambda v: int(v),
    'payload_size': lambda v: int(v),
    'credentials': json.loads,
    'scopes': lambda v: [l for l in v.splitlines() if l],
    'headers': json.loads,
}


class SetCredentials(AdminCommand):
  """Save new credentials for the Monacq endpoint."""

  def get(self):
    params = {
        'message': '',
        'title': 'Config: Chrome Infra Loadtest',
    }
    data = LoadTestData.get_by_id(CONFIG_DATA_KEY)
    if data:
      setParams(params, data)
    self.render_response('set_credentials.html', **params)

  def post(self):
    params = {
        'message': '',
        'title': 'Config: Chrome Infra Loadtest',
    }
    data = LoadTestData.get_or_insert(CONFIG_DATA_KEY)
    setParams(params, data)

    updated_fields = False
    failed_fields = []
    for field, parser in _parsers.iteritems():
      if not self.request.get(field):
        continue
      try:
        setattr(data, field, parser(self.request.get(field)))
        updated_fields = True
      except ValueError:
        failed_fields.append(field)
      params[field] = self.request.get(field)

    if failed_fields:
      params['message'] = 'Failed to update %s. Please try again.' % (
          ', '.join(failed_fields))
    elif updated_fields:
      data.put()
      setParams(params, data)
      params['message'] = 'Updated configuration.'
      logging.info('Updated configuration: %r', data)
    self.render_response('set_credentials.html', **params)


commands = {
  '': AdminPage,
  'set-credentials': SetCredentials,
}

class AdminDispatch(BaseHandler):
  """Provide a cached Jinja environment to each request."""

  def get(self, command):
    if not users.is_current_user_admin():
      self.redirect(users.create_login_url(self.request.url))
      return
    commands[command](self).get()

  def post(self, command):
    if not users.is_current_user_admin():
      self.response.set_status(403)
      return
    commands[command](self).post()


class TestHandler(auth.AuthenticatingHandler):
  """A /dev/null endpoint to test the entire pipeline.

  This endpoint can be used in place of the MonAcq official endpoint
  for testing the proxy.
  """
  # Disable XSRF in local dev appserver; otherwise requests will fail.
  if is_development_server():
    xsrf_token_enforce_on = [] # pragma: no cover
  @require_group_membership('service-account-monitoring-proxy-test')
  def get(self):
    msg = 'Received GET request.'
    self.response.headers['Content-Type'] = 'text/plain'
    self.response.out.write(msg)
    logging.debug('Received GET at /test')

  @require_group_membership('service-account-monitoring-proxy-test')
  def post(self):
    logging.info('Received POST /test: %s',
                  payload_stats(self.request.body))


class LoadTestHandler(webapp2.RequestHandler):
  """Store and publish load test parameters.

  Admins can set QPS, and anyone can retrieve it.  This endpoint controls
  distributed machines sending load test traffic to the proxy.
  """
  def get(self):
    data = LoadTestData.get_or_insert(CONFIG_DATA_KEY)
    # if qps: # Only admins can set a qps value.
    #   if not users.is_current_user_admin():
    #     self.redirect(users.create_login_url(self.request.url))
    #     return
    #   qps = int(qps)
    #   if qps < 0:
    #     self.response.write('Error: cannot set QPS to negative value.')
    #     return
    #   data.qps = qps
    #   payload_size = self.request.get('size')
    #   if payload_size:
    #     data.payload_size = int(payload_size)
    #   data.put()
    # # Return JSON either way.
    result_json = {
        'qps': data.qps,
        'payload_size': data.payload_size,
    }
    self.response.write(json.dumps(result_json))


class MainHandler(BaseHandler):
  def get(self):
    self.render_response('main.html', title='Chrome Infra Loadtest')


logging.basicConfig(level=logging.DEBUG)

test_handlers = [
    (r'/', MainHandler),
    (r'/admin/(.*)', AdminDispatch),
    (r'/test', TestHandler),
    (r'/loadtest.*', LoadTestHandler),
]

app = webapp2.WSGIApplication(test_handlers, debug=True)
