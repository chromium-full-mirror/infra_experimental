# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import logging
import os
import urllib2
import webtest

from google.appengine.api import users
from testing_utils import testing

import common
import test_module
from components import auth


class TestHandlerTest(testing.AppengineTestCase):

  @property
  def app_module(self):
    return test_module.test

  def tearDown(self):
    super(TestHandlerTest, self).tearDown()

  def test_require_group_membership(self):
    # This is a smoke test for coverage. The function is otherwise trivial.
    self.mock(os, 'environ', {'SERVER_SOFTWARE': 'Development server'})
    test_module.require_group_membership('foo')
    self.mock(os, 'environ', {'SERVER_SOFTWARE': 'GAE production server'})
    test_module.require_group_membership('foo')

  def test_get(self):
    response = self.test_app.get('/test')
    logging.info('response = %s', response)
    self.assertEquals(200, response.status_int)

  def test_post(self):
    response = self.test_app.post('/test', 'deadbeefdata')
    logging.info('response = %s', response)
    self.assertEquals(200, response.status_int)


class LoadTestHandlerTest(testing.AppengineTestCase):

  @property
  def app_module(self):
    return test_module.test

  def test_get(self):
    class LoadTestDataMock(object):
      def __init__(self, data):
        self.data = data

      def get_or_insert(self, _id):
        return self.data

    class DataMock(object):
      def __init__(self, qps=0):
        self.qps = qps
        self.updated = False

      def to_dict(self):
        return {'qps': self.qps}

      def put(self):
        self.updated = True
        logging.debug('Saving NDB data: %s', self.to_dict())

    # Read data.
    data_0 = DataMock(0)
    self.mock(test_module, 'LoadTestData', LoadTestDataMock(data_0))
    response = self.test_app.get('/loadtest/')
    logging.info('response = %s', response)
    self.assertEquals(200, response.status_int)
    self.assertEquals(data_0.to_dict(), json.loads(response.body))
    
    # Write data, unauthorized.
    self.mock(users, 'is_current_user_admin', lambda: False)
    response = self.test_app.get('/loadtest/5')
    logging.info('response = %s', response)
    self.assertEquals(302, response.status_int)
    
    # Write qps data, authorized.
    self.mock(users, 'is_current_user_admin', lambda: True)
    data_1 = DataMock(0)
    self.mock(test_module, 'LoadTestData', LoadTestDataMock(data_1))
    response = self.test_app.get('/loadtest/5')
    logging.info('response = %s', response)
    self.assertEquals(200, response.status_int)
    self.assertTrue(data_1.updated)
    self.assertEquals(data_1.to_dict(), json.loads(response.body))
    
    # Write qps + size data, authorized.
    self.mock(users, 'is_current_user_admin', lambda: True)
    data_1 = DataMock(0)
    self.mock(test_module, 'LoadTestData', LoadTestDataMock(data_1))
    response = self.test_app.get('/loadtest/5?size=2048')
    logging.info('response = %s', response)
    self.assertEquals(200, response.status_int)
    self.assertTrue(data_1.updated)
    self.assertEquals(data_1.to_dict(), json.loads(response.body))

    # Attempt to write bad data, authorized.
    self.mock(users, 'is_current_user_admin', lambda: True)
    data_2 = DataMock(0)
    self.mock(test_module, 'LoadTestData', LoadTestDataMock(data_2))
    response = self.test_app.get('/loadtest/-5')
    logging.info('response = %s', response)
    self.assertEquals(200, response.status_int)
    self.assertFalse(data_2.updated)
