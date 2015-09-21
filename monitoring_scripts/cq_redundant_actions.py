#!/usr/bin/python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
'''Generate stats of CQ usage.'''

import argparse
import calendar
import collections
import copy
import datetime
from xml.etree import ElementTree
import json
import logging
from multiprocessing.pool import ThreadPool
import numbers
import numpy
import re
import subprocess
import sys
import time
import urllib
import urllib2
import urlparse


STATS_URL = 'http://chromium-cq-status.appspot.com'


def parse_args():
  parser = argparse.ArgumentParser(description=sys.modules['__main__'].__doc__)
  parser.add_argument(
      '--project',
      help=('Collect stats about this project. '
            'Default: collect for all projects.'))
  parser.add_argument(
      '-v', '--verbose',
      default='warning',
      choices=['debug', 'info', 'warning', 'error', 'critical'],
      help='Set verbosity level. Default=%(default)s.')
  parser.add_argument(
      '--seq', action='store_true',
      help='Run everything sequentially for debugging.')
  parser.add_argument(
      '--thread-pool', type=int, default=200,
      help='Fetch data using this many parallel threads. Default=%(default)s.')
  parser.add_argument(
      '--from-date',
      required=True,
      help='Start date of stats YYYY-MM-DD[ HH[:MM]].')
  parser.add_argument(
      '--to-date',
      required=True,
      help='End date of stats YYYY-MM-DD[ HH[:MM]].')
  args = parser.parse_args()

  args.from_date = date_from_string(args.from_date)
  args.to_date = date_from_string(args.to_date)

  if args.from_date >= args.to_date:
    logging.error('--from-date needs to be before --to-date.')

  verbosity_map = {
      'debug': logging.DEBUG,
      'info': logging.INFO,
      'warning': logging.WARNING,
      'error': logging.ERROR,
      'critical': logging.CRITICAL,
  }
  args.verbose = verbosity_map[args.verbose]

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


def fetch_json(url):
  result = {'error': '404'}
  delays = [0.0, 0.5, 1.0, 2.0]
  for retry in range(len(delays)):
    if retry:
      time.sleep(delays[retry])
    try:
      result = json.loads(urllib2.urlopen(url).read())
      return result
    except Exception as e:
      logging.info('Failed to fetch (attempt %d) %s: %s', retry + 1, url, e)
  logging.error('Permanently failed to fetch %s: %s', url, e)
  return result


# "Dangerous default value []": pylint: disable=W0102
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
    params = {'count': 20} # reduce to prevent server OOM.
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
    logging.debug('  %s', '\n  '.join(['%s %s' % (
        patch_url((r['fields']['issue'], r['fields']['patchset'])),
        r['fields'].get('action', '')) for r in results]))
    cursor = data.get('cursor', None)
    if not data.get('more', False) or not cursor:
      break

  return results


def patch_url(patch_id):
  return '%s/patch-status/%s/%s' % ((STATS_URL,) + patch_id)


def parse_json(obj):
  """Attempt to interpret a string as JSON, pass through otherwise."""
  result = obj
  if type(obj) in [str, unicode]:
    try:
      result = json.loads(obj)
    except Exception as e:
      logging.error('Could not decode json in "%s": %s', obj, e)
  return result


def maybe_min(series):
  series_list = list(series)
  if not series_list:
    return 0
  return min(series_list)


def maybe_max(series):
  series_list = list(series)
  if not series_list:
    return 0
  return max(series_list)


def fetch_attempts(patch_id):
  """|patch_id| is a tuple (issue, patchset).

  Return:
    patch_id, attempts (list of list of events).
  """
  # Assume the results are in descendent order by timestamp.
  results = fetch_cq_logs(filters=[
      'issue=%s' % patch_id[0], 'patchset=%s' % patch_id[1]])
  logging.debug('fetch_attempts(%r): fetched %d entries.',
                patch_id, len(results))
  # Group by attempts, list of lists of events.
  attempts = []

  # An attempt is a set of actions between the first patch_start and
  # the last patch_stop actions. Repeated patch_start / patch_stop
  # actions are all included - we are looking for those.
  attempt = []
  results.reverse()
  state = 'stop'
  for r in results:
    action = r['fields'].get('action')
    if state == 'stop':
      if action == 'patch_start':
        state = 'start'
        if attempt:
          attempts.append(attempt)
          attempt = []
    attempt.append(r)
    if action == 'patch_stop':
      state = 'stop'
  if attempt:
    attempts.append(attempt)

  logging.info('fetch_attempts: %s has %d attempts',
               patch_url(patch_id), len(attempts))

  return patch_id, attempts


def has_action(record, action):
  return record['fields'].get('action') == action


def main():
  args = parse_args()
  logging.basicConfig(level=args.verbose)
  filters = ['action=patch_stop']
  if args.project:
    filters.append('project=%s' % args.project)
  records = fetch_cq_logs(args.from_date, args.to_date, filters=filters)
  patchsets = set((r['fields']['issue'], r['fields']['patchset'])
                  for r in records)
  logging.warning('Found %d patchsets, and %d patch_stop events',
                  len(patchsets), len(records))
  pool = ThreadPool(min(args.thread_pool, len(records) or 1))
  if args.seq or not args.thread_pool:
    iterable = map(fetch_attempts, patchsets)
  else:
    iterable = pool.imap_unordered(fetch_attempts, patchsets)
  num_attempts = 0
  for patch_id, attempts in iterable:
    num_attempts += len(attempts)
    for n, attempt in enumerate(attempts, start=1):
      stops = [r for r in attempt if has_action(r, 'patch_stop')]
      if len(stops) != 1:
        logging.error('Attempt %d has %d patch_stop events: %s',
                      n, len(stops), patch_url(patch_id))
      failed = [r for r in attempt if has_action(r, 'patch_failed')]
      if len(failed) > 1:
        logging.error('Attempt %d has %d patch_failed events: %s',
                      n, len(failed), patch_url(patch_id))
      for record in failed:
        fail_type = record['fields'].get('reason', {}).get('fail_type')
        if not fail_type:
          logging.error(
              'Attempt %d has patch_failed event without fail_type: %s',
              n, patch_url(patch_id))
      # starts = [r for r in attempt
      #           if r['fields'].get('action') == 'patch_start']
      # if len(starts) != 1:
      #   logging.error('Patchset has %d patch_start events: %s',
      #                 len(starts), patch_url(patch_id))

  logging.warning('Total number of attempts: %d', num_attempts)


if __name__ == '__main__':
  sys.exit(main())
