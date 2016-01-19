# Copyright (c) 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Datastore models don't define __init__ methods, but sometimes you have to
# assign values to the implied .key attribute. Pylint doesn't like that.
# pylint: disable=attribute-defined-outside-init

from google.appengine.ext import ndb


class BigQueryTable(ndb.Model):
  table = ndb.StringProperty(default='')


class Report(ndb.Model):
  generated = ndb.DateTimeProperty(auto_now_add=True)
  violations = ndb.JsonProperty()
  week_of = ndb.StringProperty()
  daily_scores = ndb.JsonProperty()
  total_score = ndb.JsonProperty()


class LatestReport(ndb.Model):
  generated = ndb.DateTimeProperty(auto_now=True)
  latest = ndb.KeyProperty()
