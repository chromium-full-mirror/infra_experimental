# Copyright (c) 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os

import endpoints
from google.appengine.ext import ndb
from protorpc import messages
from protorpc import message_types
from protorpc import remote


class Record(ndb.Expando):
  create_time = ndb.DateTimeProperty(auto_now_add=True)
  pass


class Tag(messages.Message):
  tag = messages.StringField(1, required=True)
  value = messages.StringField(2)


class Entry(messages.Message):
  tags = messages.MessageField(Tag, 1, repeated=True)

class Entries(messages.Message):
  entries = messages.MessageField(Entry, 1, repeated=True)


@endpoints.api(name='expando', version='v1',
               description='Testing Expando model index.')
class Handler(remote.Service):
  """Testing Expando model index."""
  @endpoints.method(Entry, message_types.VoidMessage,
                    name='tag.add')
  def add(self, request):
    """Add an entry with a set of key:value tags."""
    params = {}
    for tag in request.tags:
      params[tag.tag] = tag.value
      logging.info('adding %s = %s', tag.tag, tag.value)
    Record(**params).put()
    return message_types.VoidMessage()

  @endpoints.method(Entry, Entries, name='tag.search')
  def search(self, request):
    """Search for entries with the given key:value tags.

    Returns a list of complete entries that match.
    """
    query = Record.query().order(Record.create_time)
    for tag in request.tags:
      query = query.filter(ndb.GenericProperty(tag.tag) == tag.value)
      logging.info('search: %s = %s', tag.tag, tag.value)
    entries = []
    for entry in query:
      tags = [Tag(tag=tag, value=getattr(entry, tag))
              for tag, value in entry._properties.iteritems()]
      entries.append(Entry(tags=tags))
    return Entries(entries=entries)


app = endpoints.api_server([Handler])
