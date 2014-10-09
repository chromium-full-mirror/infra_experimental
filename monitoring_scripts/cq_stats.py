#!/usr/bin/python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
'''Generate stats of CQ usage.'''

import argparse
import copy
import datetime
import json
import logging
from multiprocessing.pool import ThreadPool
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
  parser.add_argument(
      '-v', '--verbose',
      default='error',
      choices=['debug', 'info', 'warning', 'error', 'critical'],
      help='Set verbosity level. Default=%(default)s.')
  parser.add_argument('--list-rejected', action='store_true',
                      help='List rejected CLs and reasons for rejection.')
  parser.add_argument('--list-false-rejections', action='store_true',
                      help='List CLs that were committed in more than one attempt.')
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
      '--use-logs', action='store_true',
      help=('Fetch the detailed logs and recompute the stats in this script, '
            'instead of fetching precomputed stats (default). '
            'Slower, but more accurate, and helps validate the cached stats.'))
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


def fetch_stats(args):
  if args.date:
    timestamp = int(time.mktime(args.date.timetuple()))
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


def fetch_logs(date=None, time_range=None, filters=[]):
  begin_time = None
  end_time = None
  if date:
    end_time = int(time.mktime(date.timetuple()))
  if time_range:
    begin_time = end_time - 60 * INTERVALS[time_range]
  results = []
  cursor = None
  while(True):
    params = {}
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
      data = json.loads(urllib2.urlopen(url).read())
    except Exception as e:
      logging.error('Failed to fetch %s: %s', url, e)
      data = {'error': '404'}
    results.extend(data.get('results', []))
    logging.info('fetch_logs: Got %d results', len(results))
    cursor = data.get('cursor', None)
    if not data.get('more', False) or not cursor:
      break

  return results


def organize_stats(stats):
  """Changes cached lists of stats into dictionaries.

  Return a dict mapping ('latest' | 'previous') -> stat.name -> <stats json>.
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


def derive_stats(args, end_date):
  """Process raw CQ updates log and derive stats.

  Return the same format as organize_stats().
  Assumes |results| are action=patch_stop logs sorted by timestamp in
  descending order.
  """
  stats = {}
  filters = ['project=%s' % args.project, 'action=patch_stop']
  results = fetch_logs(end_date, args.range, filters)
  if not results:
    return stats

  stats['begin'] = date_from_timestamp(results[-1]['timestamp'])
  stats['end'] = date_from_timestamp(results[0]['timestamp'])
  # Create map issue:patchset -> #attempts
  patches = set()
  attempts_count = 0
  issues = set()
  for r in results:
    issues.add(r['fields']['issue'])
    patches.add((r['fields']['issue'], r['fields']['patchset']))
    attempts_count += 1
  stats['issue-count'] = len(issues)
  stats['patchset-count'] = len(patches)
  stats['attempt-count'] = attempts_count
  patch_stats = {}
  # Fetch and process each patchset log
  pool = ThreadPool(min(100, len(patches)))
  for patch_id, pstats in pool.imap_unordered(derive_patch_stats, patches):
    patch_stats[patch_id] = pstats
  # TODO(sergeyberezin): refine this count: exclude missing LGTMs and
  # possibly presubmit bot failures.
  stats['patchset-false-reject-count'] = sum([
      patch_stats[p]['false-rejections'] for p in patch_stats])
  stats['false-rejections'] = [
      p for p in patch_stats if patch_stats[p]['false-rejections']]
  stats['rejections'] = [
      p for p in patch_stats if not patch_stats[p]['committed']]
  # TODO(sergeyberezin): fill these in.
  stats['patchset-commit-count'] = -1
  list_stats_stub = {
      '10': -1,
      '25': -1,
      '50': -1,
      '75': -1,
      '90': -1,
      '95': -1,
      '99': -1,
      'min': -1,
      'max': -1,
      'mean': -1,
      'size': -1,
  }
  stats['patchset-durations'] = list_stats_stub
  stats['patchset-total-commit-queue-durations'] = list_stats_stub
  stats['patchset-durations'] = list_stats_stub
  stats['patchset-attempts'] = list_stats_stub
  stats['jobs'] = {}
  return stats


def patch_url(patch_id):
  return '%s/patch-status/%s/%s' % ((STATS_URL,) + patch_id)


def derive_patch_stats(patch_id):
  """|patch_id| is a tuple (issue, patchset)."""
  # Assume the results are in descendent order by timestamp.
  results = fetch_logs(filters=[
      'issue=%s' % patch_id[0], 'patchset=%s' % patch_id[1]])
  logging.debug('derive_patch_stats(%r): fetched %d entries.',
                patch_id, len(results))
  # Group by attempts
  attempts = []
  attempt_empty = {'actions': [], 'committed': False}

  def add_attempt(attempt):
    attempts.append(attempt)
    attempt = copy.copy(attempt_empty)

  attempt = copy.copy(attempt_empty)
  results.reverse()
  for r in results:
    attempt['actions'].append(r)
    action = r['fields'].get('action')
    if action == 'patch_committed':
      attempt['committed'] = True
    if action == 'patch_stop':
      add_attempt(attempt)
  # Handle the last, possibly unfinished attempt.
  if attempt:
    add_attempt(attempt)

  logging.info('derive_patch_stats: %s has %d attempts, committed=%r',
               patch_url(patch_id), len(attempts), attempt['committed'])

  stats = {}
  stats['committed'] = len([a for a in attempts if a['committed']])
  stats['attempts'] = len(attempts)
  stats['rejections'] = stats['attempts'] - stats['committed']
  stats['false-rejections'] = 0
  if stats['committed']:
    stats['false-rejections'] = stats['rejections']
  return patch_id, stats


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
  print 'Statistics for project %s' % args.project
  print 'from %s till %s (local time).' % (
      latest['begin'], latest['end'])

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
  logging.basicConfig(level=args.verbose)
  if args.use_logs:
    stats = {}
    stats['latest'] = derive_stats(args, args.date)
    prev_date = args.date - datetime.timedelta(minutes=INTERVALS[args.range])
    stats['previous'] = derive_stats(args, prev_date)
  else:
    stats = organize_stats(fetch_stats(args))

  print_stats(args, stats)


if __name__ == '__main__':
  sys.exit(main())
