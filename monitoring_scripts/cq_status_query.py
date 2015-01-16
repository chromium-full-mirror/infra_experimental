#!/usr/bin/python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
'''Query chromium-cq-status.appspot.com stats from command line.'''

import argparse
import datetime
import json
import logging
import sys
import time
import urllib
import urllib2
import urlparse


STATS_URL = 'http://chromium-cq-status.appspot.com'
LOCAL_URL = 'http://localhost:8080'


def fetch_json(url):
  result = {'error': '404'}
  delays = [0.0, 0.5, 1.0, 2.0]
  for retry in range(len(delays)):
    if retry:
      time.sleep(delays[retry])
    try:
      result = json.loads(urllib2.urlopen(url, timeout=60).read())
      return result
    except Exception as e:
      logging.warning('Failed to fetch (attempt %d) %s: %s', retry + 1, url, e)
  logging.error('Permanently failed to fetch %s: %s', url, e)
  return result


def fetch_cq_logs(start_date=None, end_date=None, filters=[]):
  begin_time = None
  end_time = None
  if start_date:
    begin_time = int(time.mktime(start_date.timetuple()))
  if end_date:
    end_time = int(time.mktime(end_date.timetuple()))
  results = []
  cursor = None
  while(True):
    # AE app sometimes fails with
    # "Values may not be more than 1000000 bytes in length;
    # received 1174060 bytes". Reducing the limit.
    params = {'count': 20}
    if begin_time:
      params['begin'] = begin_time
    if end_time:
      params['end'] = end_time
    if cursor:
      params['cursor'] = cursor
    query = 'query/%s?%s' % ('/'.join(filters), urllib.urlencode(params))
    url = urlparse.urljoin(STATS_URL, query)
    logging.debug('Fetching %s', url)
    try:
      data = fetch_json(url)
    except Exception as e:
      logging.error('Failed to fetch %s: %s', url, e)
      data = {'error': '404'}
    results.extend(data.get('results', []))
    logging.info('fetch_cq_logs: Got %d results', len(results))
    cursor = data.get('cursor', None)
    if not data.get('more', False) or not cursor:
      break

  return results


def parse_args():
  parser = argparse.ArgumentParser(description=sys.modules['__main__'].__doc__)
  parser.add_argument(
      '--tags',
      help='Comma-separated list of tags to query.')
  parser.add_argument(
      '-v', '--verbose',
      default='error',
      choices=['debug', 'info', 'warning', 'error', 'critical'],
      help='Set verbosity level. Default=%(default)s.')
  parser.add_argument(
      '--from-date',
      required=True,
      help='Start date of stats YYYY-MM-DD[ HH[:MM]].')
  parser.add_argument(
      '--to-date',
      required=True,
      help='End date of stats YYYY-MM-DD[ HH[:MM]]. Default: --range ago.')
  args = parser.parse_args()

  args.from_date = date_from_string(args.from_date)
  args.to_date = date_from_string(args.to_date)

  verbosity_map = {
      'debug': logging.DEBUG,
      'info': logging.INFO,
      'warning': logging.WARNING,
      'error': logging.ERROR,
      'critical': logging.CRITICAL,
  }
  args.verbose = verbosity_map[args.verbose]
  args.tags = args.tags.split(',') if args.tags else []

  return args


def date_from_string(iso_str):
  formats = ['%Y-%m-%d %H:%M:%S.%f',
             '%Y-%m-%d %H:%M:%S',
             '%Y-%m-%d %H:%M',
             '%Y-%m-%d %H',
             '%Y-%m-%d']
  for fmt in formats:
    try:
      return datetime.datetime.strptime(iso_str, fmt)
    except ValueError:
      pass
  raise ValueError('Unrecognized date/time format: %s' % iso_str)


def date_from_timestamp(timestamp):
  return datetime.datetime.fromtimestamp(int(timestamp))


def patch_url(issue, patchset):
  return LOCAL_URL + ('/recent#issue=%s,patchset=%s' % (issue, patchset))


def match_verifiers(data):
  """Make sure both "simple try job" and "try job" verifier report an event

  for each issue/patchset.
  """
  # dict: (issue, patchset) -> list of verifiers
  patches = {}
  count_new = 0
  count_old = 0
  for entry in data:
    k = (entry['fields']['issue'], entry['fields']['patchset'])
    if 'verifier' in entry['fields']:
      patches.setdefault(k, []).append(entry['fields']['verifier'])
  for k, verifiers in patches.iteritems():
    if 'try job' not in verifiers:
      print 'Missing "try job": %s' % patch_url(*k)
      count_new += 1
    if 'simple try job' not in verifiers:
      print 'Missing "simple try job": %s' % patch_url(*k)
      count_old += 1
  print 'Missing %d "try job" and %d "simple try job"' % (
      count_new, count_old)


def main():
  args = parse_args()
  logging.basicConfig(level=args.verbose)
  data = fetch_cq_logs(args.from_date, args.to_date, args.tags)
  print 'Fetched %d entries' % len(data)
  match_verifiers(data)


if __name__ == '__main__':
  sys.exit(main())
