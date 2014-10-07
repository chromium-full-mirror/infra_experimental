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
import re
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
      required=True,
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


def date_from_timestamp(timestamp):
  return datetime.datetime.fromtimestamp(int(timestamp))


def fetch_stats(args):
  if args.date:
    timestamp = int(calendar.timegm(args.date.timetuple()))
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


def organize_stats(stats):
  """Changes flat lists of stats into dictionaries.

  'latest' | 'previous' -> stat.name -> stats json.
  """
  if 'results' not in stats:
    return None
  result = {'latest' : {}, 'previous': {}}
  for dataset, name in zip(stats['results'], ['latest', 'previous']):
    result[name]['begin'] = date_from_timestamp(dataset['begin'])
    result[name]['end'] = date_from_timestamp(dataset['end'])
    re_trybot_pass_count = re.compile('^trybot-(.+)-pass-count$')
    re_trybot_false_reject_count = re.compile('^trybot-(.+)-false-reject-count$')
    result[name]['jobs'] = {}
    for data in dataset['stats']:
      if data['type'] == 'count':
        result[name][data['name']] = data['count']
        match_pass = re_trybot_pass_count.match(data['name'])
        match_false_reject = re_trybot_false_reject_count.match(data['name'])
        if match_pass:
          job_name = match_pass.group(1)
          result[name]['jobs'].setdefault(job_name, {})
          result[name]['jobs'][job_name]['pass-count'] = data['count']
          logging.debug('Job %s passed %d times. Jobs: %r', job_name, data['count'], result[name]['jobs'])
        if match_false_reject:
          job_name = match_false_reject.group(1)
          result[name]['jobs'].setdefault(job_name, {})
          result[name]['jobs'][job_name]['false-reject-count'] = data['count']
          logging.debug('Job %s flakily failed %d times', job_name, data['count'])
      elif data['type'] == 'list':
        result[name][data['name']] = {
            '10': data['percentile_10'],
            '25': data['percentile_25'],
            '50': data['percentile_50'],
            '75': data['percentile_75'],
            '90': data['percentile_90'],
            '95': data['percentile_95'],
            '99': data['percentile_99'],
            'min': data['min'],
            'max': data['max'],
            'mean': data['mean'],
            'size': data['sample_size'],
        }
  return result


def percentage(n, total):
  if total:
    return 100. * n / total
  return 0.


def round_timedelta(seconds):
  # We never care about the milliseconds when printing timedeltas:
  return datetime.timedelta(seconds=round(seconds))


def print_stats(args, stats):
  latest = stats.get('latest')
  previous = stats.get('previous')
  if not latest:
    print 'No stats to display.'
  print 'Statistics for project %s, interval: %s beginning %s.' % (
      args.project, args.range, latest['begin'])

  print '%4d issues (%d patchsets) were tried by CQ, resulting in' % (
      latest['issue-count'], latest['patchset-count'])
  print '%4d CQ attempts.' % latest['attempt-count']
  print '%4d patches (%.1f%% of tried patchsets) were committed by CQ,' % (
      latest['patchset-commit-count'],
      percentage(latest['patchset-commit-count'], latest['patchset-count']))
  # TODO(sergeyberezin): add gave up count (committed manually after trying CQ).
  # TODO(sergeyberezin): add count of NOTRY=true (if possible).
  # TODO(sergeyberezin): add counts of rejection reasons (missing
  # LGTM, failing jobs, etc.)

  print
  cq_only = round_timedelta(latest['patchset-durations']['mean'])
  wallclock = round_timedelta(
      latest['patchset-total-commit-queue-durations']['mean'])
  prev_cq_only = 'unknown'
  prev_wallclock = 'unknown'
  if previous:
    prev_cq_only = round_timedelta(previous['patchset-durations']['mean'])
    prev_wallclock = round_timedelta(
        previous['patchset-total-commit-queue-durations']['mean'])
  print 'Mean duration in CQ trying a patch:'
  print '  wallclock:       %8s (%3d min). Previously: %8s (%3d min).' % (
      wallclock, round(wallclock.total_seconds() / 60.0),
      prev_wallclock, round(prev_wallclock.total_seconds() / 60.0))
  print '  sum of attempts: %8s (%3d min). Previously: %8s (%3d min).' % (
      cq_only, round(cq_only.total_seconds() / 60.0),
      prev_cq_only, round(prev_cq_only.total_seconds() / 60.0))

  cq_only = round_timedelta(latest['patchset-durations']['50'])
  wallclock = round_timedelta(
      latest['patchset-total-commit-queue-durations']['50'])
  prev_cq_only = 'unknown'
  prev_wallclock = 'unknown'
  if previous:
    prev_cq_only = round_timedelta(previous['patchset-durations']['50'])
    prev_wallclock = round_timedelta(
        previous['patchset-total-commit-queue-durations']['50'])
  print 'Median duration in CQ trying a patch:'
  print '  wallclock:       %8s (%3d min). Previously: %8s (%3d min).' % (
      wallclock, round(wallclock.total_seconds() / 60.0),
      prev_wallclock, round(prev_wallclock.total_seconds() / 60.0))
  print '  sum of attempts: %8s (%3d min). Previously: %8s (%3d min).' % (
      cq_only, round(cq_only.total_seconds() / 60.0),
      prev_cq_only, round(prev_cq_only.total_seconds() / 60.0))

  print
  print('%d CQ starts (%.1f%% of %d CQ attempts) were due to a previous '
        'false-negative\n'
        '  (CQ landed a patch it previously rejected)' % (
      latest['patchset-false-reject-count'],
      percentage(latest['patchset-false-reject-count'],
                 latest['patchset-count']),
      latest['patchset-count']))
  # TODO(sergeyberezin): add breakdown by #attempts.

  print
  print 'Patches which eventually land percentiles:'
  for p in ['10', '25', '50', '75', '90', '95', '99']:
    print '%s: %4.1f hrs, %2d attempts' % (
        p, latest['patchset-durations'][p] / 3600.0,
        latest['patchset-attempts'][p])

  # TODO(sergeyberezin): add total try jobs / by CQ / unknown. Get it from CBE.
  # TODO(sergeyberezin): recompute bot flakiness from CBE. CQ does not
  # have enough info.
  print
  print 'Top flaky builders (which fail and succeed in the same patchset):'

  logging.debug('Found %d jobs', len(latest['jobs'].keys()))

  jobs = sorted(latest['jobs'].iterkeys(),
                key=lambda j: latest['jobs'][j]['false-reject-count'],
                reverse=True)
  print '%-40s %-15s %-15s %-15s' % (
      'Builder Name', 'Succeeded', 'Flaky Failures', 'Flakiness (%)')
  for job in jobs:
    passes = latest['jobs'][job]['pass-count']
    failures = latest['jobs'][job]['false-reject-count']
    print '%-40s %-15s %-15s %-15s' % (
        job, passes, failures, percentage(failures, passes + failures))


def main():
  args = parse_args()
  logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARN)
  stats = organize_stats(fetch_stats(args))
  print_stats(args, stats)


if __name__ == '__main__':
  sys.exit(main())
