#!/usr/bin/python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
'''Buildbucket job'''

import apiclient
import argparse
import collections
import copy
import datetime
import httplib2
import json
import logging
import re
import sys
import time
import urllib
import urllib2
import urlparse


RIETVELD_URL = 'https://codereview.chromium.org'
SEARCH_URL = ('https://codereview.chromium.org/search?format=json&commit=1&closed=2&keys_only=True'
              '&limit=1000&created_after=%s&created_before=%s&owner=commit-bot%%40chromium.org'
              '&project=chromium')
DISCOVERY_URL = (
    'https://cr-buildbucket.appspot.com/_ah/api/discovery/v1/apis/'
    '{api}/{apiVersion}/rest')
BUILDSET_STR = 'patch/rietveld/codereview.chromium.org/%d/1'

# UTC datetime corresponding to zero Unix timestamp.
EPOCH = datetime.datetime.utcfromtimestamp(0)

def str_to_datetime(text):
	return datetime.datetime.strptime(text, '%Y-%m-%d')

def get_buildbucket():
  return apiclient.discovery.build(
      'buildbucket', 'v1',
      http=httplib2.Http(),
      discoveryServiceUrl=DISCOVERY_URL,
  )

def _prefix_master(master):
  prefix = 'master.'
  if master.startswith(prefix):
    return master
  else:
    return '%s%s' % (prefix, master)

def validate_pending(pending, patchset, bucket_obj):
  exp_jobs = {}
  exp_masters = {}
  for result in patchset['try_job_results']:
    if result.get('category', '') == 'cq_experimental':
      exp_jobs[(result['master'], result['builder'])] = result['timestamp']
      exp_masters[_prefix_master(result['master'])] = True

  if not exp_jobs:
    logging.info('Issue %d does not have experimental tryjobs.', pending['issue'])
    return

  logging.info('Issue %d has experimental tryjobs.', pending['issue'])

  exp_buckets = exp_masters.keys()

  try:
    req = bucket_obj.search(
        tag=['buildset:%s' % (BUILDSET_STR % pending['issue']),],
        bucket=exp_buckets,
    )
    response = req.execute()
  except Exception as e:
    logging.warning('Exception when search for issue %d: %s.', pending['issue'], e)

  bucket_exp_jobs = {}
  for bucket_result in response.get('builds', []):
    parameters = json.loads(bucket_result['parameters_json'])
    if parameters['properties']['category'] != 'cq_experimental':
      continue
    builder = parameters['builder_name']
    master = parameters['properties']['master']
    bucket_exp_jobs[(master, builder)] = (EPOCH +
        datetime.timedelta(microseconds=int(bucket_result['status_changed_ts'])))

  for key in exp_jobs:
    if not key in bucket_exp_jobs:
      logging.error('  %s missed tryjob for %s.', pending['issue'], (key,))
    else:
      logging.info('  %s timestamp for %s: Rietveld:%s; Bucket:%s.', pending['issue'], (key,),
                    exp_jobs[key], bucket_exp_jobs[key])

def parse_args():
  parser = argparse.ArgumentParser(description=sys.modules['__main__'].__doc__)
  parser.add_argument(
      '-v', '--verbose', default=False, action='store_true',
      help='Enables debugging log messages.')
  parser.add_argument(
      '--from_date',
      default='2015-02-02',
      help='Start date of stats YYYY-MM-DD. Default: 2015-02-02.')
  parser.add_argument(
      '--to_date',
      default='',
      help='End date of stats YYYY-MM-DD.')
  options = parser.parse_args()
  return options

def main():
  args = parse_args()
  logging.basicConfig(level=args.verbose)
  bucket_obj = get_buildbucket()
  url = SEARCH_URL % (args.from_date, args.to_date)
  logging.info('Requesting: %s', url)
  response = json.load(urllib2.urlopen(url))
  for issue_id in response.get('results', []):
    pending = json.load(urllib2.urlopen('%s/api/%d' % (RIETVELD_URL, issue_id)))
    patchset = json.load(urllib2.urlopen('%s/api/%d/1' % (RIETVELD_URL, issue_id)))
    validate_pending(pending, patchset, bucket_obj)


if __name__ == '__main__':
  sys.exit(main())