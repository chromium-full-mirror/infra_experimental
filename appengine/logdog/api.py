# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import datetime
import functools
import json
import logging
import random

from components import auth
from components import utils
from google.appengine.api import app_identity
from protorpc import messages
from protorpc import message_types
from protorpc import remote
import endpoints

LABEL_MASTER = 'master'
LABEL_BUILD_LOG = 'build_log'
MASTER_LOG_PREFIX = 'master'
MASTER_MAX_SHARDS = 10
BUILD_LOG_PREFIX = 'build'
BUILD_MAX_SHARDS = 90


@endpoints.api(name='logs', version='v1', title='Log Service')
class LogApi(remote.Service):

  class StartLogResponseMessage(messages.Message):
    class Label(messages.Message):
      key = messages.StringField(1, required=True)
      value = messages.StringField(2, required=True)

    log_name = messages.StringField(1, required=True)
    labels = messages.MessageField(Label, 2, repeated=True)

  START_BUILDBOT_SLAVE_LOG_RESOURCE_CONTAINER = endpoints.ResourceContainer(
      message_types.VoidMessage,
      master=messages.StringField(1, required=True),
      builder=messages.StringField(2, required=True),
      build_number=messages.StringField(3, required=True),
      step=messages.StringField(4, required=True),
      log=messages.StringField(5, required=True, default='stdio'),
  )

  @endpoints.method(
      START_BUILDBOT_SLAVE_LOG_RESOURCE_CONTAINER, StartLogResponseMessage,
      http_method='POST',
      path=(
          'buildbot/masters/{master}/builders/{builder}'
          '/builds/{build_number}/steps/{step}/logs/{log}'),
      name='startBuildbotSlaveLog')
  def start_buildbot_slave_log(self, request):
    return self.StartLogResponseMessage(
        log_name='projects/{project}/logs/{log}'.format(
            project=app_identity.get_application_id(),
            log=get_log_shard(BUILD_LOG_PREFIX, BUILD_MAX_SHARDS),
        ),
        labels=[
          self.StartLogResponseMessage.Label(
              key=LABEL_BUILD_LOG,
              value='%s/%s/%s/%s/%s' % (
                  request.master, request.builder,
                  request.build_number, request.step, request.log),
          ),
        ],
    )

  START_BUILDBOT_MASTER_LOG_RESOURCE_CONTAINER = endpoints.ResourceContainer(
      message_types.VoidMessage,
      master=messages.StringField(1, required=True),
  )

  @endpoints.method(
      START_BUILDBOT_MASTER_LOG_RESOURCE_CONTAINER, StartLogResponseMessage,
      http_method='POST',
      path='buildbot/masters/{master}/log',
      name='startBuildbotMasterLog')
  def start_buildbot_master_log(self, request):
    return self.StartLogResponseMessage(
        log_name='projects/{project}/logs/{log}'.format(
            project=app_identity.get_application_id(),
            log=get_log_shard(MASTER_LOG_PREFIX, MASTER_MAX_SHARDS),
        ),
        labels=[
          self.StartLogResponseMessage.Label(
              key=LABEL_MASTER,
              value=request.master,
          ),
        ],
    )


def get_log_shard(prefix, max_shards):
  shard = random.randint(1, max_shards)
  return '%s_shard%s' % (prefix, shard)
