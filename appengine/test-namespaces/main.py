# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os
import webapp2

from google.appengine.api import namespace_manager
from google.appengine.api import users
from google.appengine.ext import ndb
from webapp2_extras import jinja2

from components import auth


class BaseAuthHandler(auth.AuthenticatingHandler):
  """Provide a cached Jinja environment to each request."""

  @staticmethod
  def template_params(params=None):
    """Create jinja2 template parameters based on ``params``."""
    account = users.get_current_user()
    data = {
      'username': account.email() if account else None,
      'signin_link': users.create_login_url('/') if not account else None,
      'title': 'Test Namespaces',
    }
    data.update(params or {})
    return data

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
        app=self.app, factory=BaseAuthHandler.jinja2_factory)

  def render_response(self, _template, **context):
    # Renders a template and writes the result to the response.
    context = self.template_params(context)
    rv = self.jinja2.render_template(_template, **context)
    self.response.write(rv)


def can_write_internal():
  user = users.get_current_user()
  if not user:
    return False
  return user.email().endswith('@google.com')


def can_read_internal():
  return can_write_internal()


def can_write_public():
  """Any authenticated user can modify public data."""
  return True


class Data(ndb.Model):
  text = ndb.StringProperty(default='')


class MainHandler(BaseAuthHandler):
  @auth.public
  def get(self):
    self.render_response('main.html', title='Test Namespaces')


class PublicHandler(BaseAuthHandler):
  @auth.public
  def get(self, arg):
    namespace_manager.set_namespace('Public')
    data = Data.query()
    self.render_response('public.html', title='Public stuff', data=data)

  @auth.require(can_write_public)
  def post(self, arg):
    namespace_manager.set_namespace('Public')
    # TODO(sergeyberezin): implement.
    pass


class InternalHandler(BaseAuthHandler):
  @auth.require(can_read_internal)
  def get(self, arg):
    namespace_manager.set_namespace('Internal')
    data = Data.query()
    self.render_response('internal.html', title='Internal stuff', data=data)

  @auth.require(can_write_internal)
  def post(self, arg):
    namespace_manager.set_namespace('Internal')
    # TODO(sergeyberezin): implement.
    pass


def create_app():
  logging.basicConfig(level=logging.DEBUG)
  main_handlers = [
      (r'/', MainHandler),
      (r'/internal/(.*)', InternalHandler),
      (r'/public/(.*)', PublicHandler),
  ]


  return webapp2.WSGIApplication(main_handlers, debug=True)


app = create_app()
