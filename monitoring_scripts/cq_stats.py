#!/usr/bin/python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
'''Generate stats of CQ usage.'''

import argparse
import calendar
import datetime
import json
import logging
import sys
import time
import urllib
import urllib2
import urlparse


STATS_URL = 'http://chromium-cq-status.appspot.com'
# Map of intervals to minutes.
INTERVALS = {
    'week': 60 * 24 * 7,
    'day': 60 * 24,
    'hour': 60,
    '15min': 15,
}


def parse_args():
  parser = argparse.ArgumentParser(description=sys.modules['__main__'].__doc__)
  parser.add_argument(
      '--project',
#      choices=project_choices,
      help='Collect stats about this project.')
  parser.add_argument('-v', '--verbose', action='store_true')
  parser.add_argument('--list-rejected', action='store_true',
                      dest='list_rejected',
                      help='List rejected CLs and reasons for rejection.')
  parser.add_argument(
      '--top-rejecting-jobs',
      default=0,
      type=int,
      dest='top_rejecting_jobs',
      help=('List N fastests jobs that failed on a CL rejected by CQ.'))
  parser.add_argument(
      '--rejecting-jobs',
      default='',
      type=str,
      dest='rejecting_jobs',
      help=('Comma-separated list of bots: listed in this order if any '
            'of them fail on a CLs rejected by CQ. '
            'This can be used to compare bot coverage.'))
  parser.add_argument('--list-flaky-jobs', action='store_true',
                      dest='list_flaky_jobs',
                      help='List build URLs of all flaky try jobs.')
  parser.add_argument(
    '--top-jobs',
    dest='top_jobs',
    type=int,
    default=0,
    help='Print top N issues with maxium number of jobs (default=%(default)s)')
  parser.add_argument(
    '--top-flakes',
    dest='top_flakes',
    type=int,
    default=20,
    help='Print top N flaky builders (default=%(default)s)')
  parser.add_argument(
      '--date',
      help='Date of stats YYYY-MM-DD[ HH[:MM]]. Default: now.')
  parser.add_argument('--range',
                      choices=INTERVALS.keys(),
                      default='week',
                      help='Time range to print stats for.')
  parser.add_argument('--owner', default=None,
                      help=('search for issues of specified owner'))
  args = parser.parse_args()

  if args.rejecting_jobs:
    args.rejecting_jobs = args.rejecting_jobs.split(',')
    print 'Rejecting jobs: [%s]' % ', '.join(args.rejecting_jobs)
  if args.date:
    args.date = date_from_string(args.date)

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


def fetch_stats(args):
  if args.date:
    timestamp = int(calendar.timegm(d.timetuple()))
  else:
    timestamp = int(time.time())

  params = {
      'interval_minutes': INTERVALS[args.range],
      'end': timestamp,
      'count': 2, # Fetch requested and previous set, for comparison.
  }
  if args.project:
    params['project'] = args.project

  query = 'stats/query?' + urllib.urlencode(params)
  url = urlparse.urljoin(STATS_URL, query)
  logging.debug('Fetching %s', url)
  try:
    stats = json.loads(urllib2.urlopen(url).read())
  except Exception as e:
    logging.error('Failed to fetch %s: %s', url, e)
    stats = {'error': '404'}
  return stats


def print_stats(args, stats):
  print '%r' % stats


def main():
  args = parse_args()
  logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARN)
  stats = fetch_stats(args)
  print_stats(args, stats)


if __name__ == '__main__':
  sys.exit(main())
