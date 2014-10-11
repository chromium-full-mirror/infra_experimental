#!/usr/bin/python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
'''Generate stats of CQ usage.'''

import argparse
import copy
import datetime
import json
import logging
from multiprocessing.pool import ThreadPool
import numpy
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
  parser.add_argument(
      '--seq', action='store_true',
      help='Run everything sequentially for debugging.')
  parser.add_argument(
      '--list-rejected', action='store_true',
      help='List rejected CLs and reasons for rejection.')
  parser.add_argument(
      '--list-false-rejections', action='store_true',
      help='List CLs that were committed in more than one attempt.')
  # parser.add_argument(
  #     '--top-rejecting-jobs',
  #     default=0,
  #     type=int,
  #     dest='top_rejecting_jobs',
  #     help=('List N fastests jobs that failed on a CL rejected by CQ.'))
  # parser.add_argument(
  #     '--rejecting-jobs',
  #     default='',
  #     type=str,
  #     dest='rejecting_jobs',
  #     help=('Comma-separated list of bots: listed in this order if any '
  #           'of them fail on a CLs rejected by CQ. '
  #           'This can be used to compare bot coverage.'))
  # parser.add_argument('--list-flaky-jobs', action='store_true',
  #                     dest='list_flaky_jobs',
  #                     help='List build URLs of all flaky try jobs.')
  # parser.add_argument(
  #   '--top-jobs',
  #   dest='top_jobs',
  #   type=int,
  #   default=0,
  #   help='Print top N issues with maxium number of jobs (default=%(default)s)')
  # parser.add_argument(
  #   '--top-flakes',
  #   dest='top_flakes',
  #   type=int,
  #   default=20,
  #   help='Print top N flaky builders (default=%(default)s)')
  parser.add_argument(
      '--use-logs', action='store_true',
      default=True,
      help=('On by default. '
            'Fetch the detailed logs and recompute the stats in this script, '
            'instead of fetching precomputed stats. '
            'Slower, but more accurate, and helps validate the cached stats.'))
  parser.add_argument(
      '--use-cache',
      dest='use_logs',
      action='store_false',
      help=('Fetch the cached stats from the app. Opposite to --use-logs.'))
  parser.add_argument(
      '--date',
      help='Date of stats YYYY-MM-DD[ HH[:MM]]. Default: now.')
  parser.add_argument('--range',
                      choices=INTERVALS.keys(),
                      default='week',
                      help='Time range to print stats for.')
  # parser.add_argument('--owner', default=None,
  #                     help=('search for issues of specified owner'))
  args = parser.parse_args()

  # if args.rejecting_jobs:
  #   args.rejecting_jobs = args.rejecting_jobs.split(',')
  #   print 'Rejecting jobs: [%s]' % ', '.join(args.rejecting_jobs)
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
    logging.debug('  %s', '\n  '.join(['%s %s' % (patch_url((r['fields']['issue'], r['fields']['patchset'])), r['fields'].get('action', '')) for r in results]))
    cursor = data.get('cursor', None)
    if not data.get('more', False) or not cursor:
      break

  return results


def default_stats():
  """Generate all the required stats fields with default values."""
  stats = {
      'begin': 0.0,
      'end': 0.0,
      'issue-count': 0,
      'patchset-count': 0,
      'attempt-count': 0,
      'patch_stats': {},
      'patchset-false-reject-count': 0,
      'attempt-reject-count': 0, # Num. of rejected attempts
      'false-rejections': [], # patches with falsely rejected attempts
      'rejections': [],       # patches with rejected attempts
      'rejected-patches': set(), # Patches that never committed
      'missing-lgtm': [],
      'manual-cancel': [],
      'failed-commit': [],
      'failed-presubmit-bot': [],
      'patchset-commit-count': 0,
      'patchset-total-commit-queue-durations': derive_list_stats([0]),
      'patchset-durations': derive_list_stats([0]),
      'patchset-attempts': derive_list_stats([0]),
      'jobs': {},
  }
  return stats


def organize_stats(stats):
  """Changes cached lists of stats into dictionaries.

  Return a dict mapping ('latest' | 'previous') -> stat.name -> <stats json>.
  """
  if 'results' not in stats:
    return None
  result = {'latest' : default_stats(), 'previous': default_stats()}
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


def derive_list_stats(series):
  return {
      '10': numpy.percentile(series, 10),
      '25': numpy.percentile(series, 25),
      '50': numpy.percentile(series, 50),
      '75': numpy.percentile(series, 75),
      '90': numpy.percentile(series, 90),
      '95': numpy.percentile(series, 95),
      '99': numpy.percentile(series, 99),
      'min': min(series),
      'max': max(series),
      'mean': numpy.mean(series),
      'size': len(series),
  }


def sort_by_count(elements):
  return sorted(elements, key=lambda p: p['count'], reverse=True)


def stats_by_count(patch_stats, name):
  return sort_by_count([
      {'count': patch_stats[p][name], 'patch_id': p}
      for p in patch_stats if patch_stats[p][name]])


def derive_stats(args, end_date):
  """Process raw CQ updates log and derive stats.

  Return the same format as organize_stats().
  Assumes |results| are action=patch_stop logs sorted by timestamp in
  descending order.
  """
  stats = default_stats()
  filters = ['project=%s' % args.project, 'action=patch_stop']
  results = fetch_logs(end_date, args.range, filters)
  if not results:
    return stats

  stats['begin'] = date_from_timestamp(results[-1]['timestamp'])
  stats['end'] = date_from_timestamp(results[0]['timestamp'])
  # Create map issue:patchset -> #attempts
  patches = set()
  issues = set()
  for r in results:
    issues.add(r['fields']['issue'])
    patches.add((r['fields']['issue'], r['fields']['patchset']))
  stats['issue-count'] = len(issues)
  stats['patchset-count'] = len(patches)
  patch_stats = {}
  # Fetch and process each patchset log
  if args.seq:
    iterable = map(derive_patch_stats, patches)
  else:
    pool = ThreadPool(min(100, len(patches)))
    iterable = pool.imap_unordered(derive_patch_stats, patches)
  for patch_id, pstats in iterable:
    patch_stats[patch_id] = pstats

  stats['patch_stats'] = patch_stats
  stats['attempt-count'] = sum([
      patch_stats[p]['attempts'] for p in patch_stats])
  stats['patchset-false-reject-count'] = sum([
      patch_stats[p]['false-rejections'] for p in patch_stats])
  stats['attempt-reject-count'] = sum([
      patch_stats[p]['rejections'] for p in patch_stats])

  stats['rejected-patches'] = set([
      p for p in patch_stats if not patch_stats[p]['committed']])
  stats['false-rejections'] = stats_by_count(patch_stats, 'false-rejections')
  stats['rejections'] = stats_by_count(patch_stats, 'rejections')
  stats['missing-lgtm'] = stats_by_count(patch_stats, 'missing-lgtm')
  stats['manual-cancel'] = stats_by_count(patch_stats, 'manual-cancel')
  stats['failed-commit'] = stats_by_count(patch_stats, 'failed-commit')
  stats['failed-presubmit-bot'] = stats_by_count(
      patch_stats, 'failed-presubmit-bot')
  stats['patchset-commit-count'] = len([
      p for p in patch_stats if patch_stats[p]['committed']])
  stats['patchset-total-commit-queue-durations'] = derive_list_stats([
      patch_stats[p]['patchset-duration-wallclock'] for p in patch_stats])
  stats['patchset-durations'] = derive_list_stats([
      patch_stats[p]['patchset-duration'] for p in patch_stats])
  stats['patchset-attempts'] = derive_list_stats([
      patch_stats[p]['attempts'] for p in patch_stats])
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
  attempt_empty = {
      'id': 0,
      'begin': 0.0,
      'end': 0.0,
      'duration': 0.0,
      'actions': [],
      'committed': False,
      'reason': {},
      'manual-cancel': False,
      'missing-lgtm': False,
      'failed-commit': False,
      'failed-jobs': [],
      'failed-presubmit-bot': False,
  }
  attempt_id = {'id': 0}

  def add_attempt(attempt):
    if attempt['actions']:
      attempt_id['id'] += 1
      attempt['id'] = attempt_id['id']
      attempt['duration'] = attempt['end'] - attempt['begin']
      logging.debug(
          'add_attempt: #%d (%s%s%s)',
          attempt['id'],
          ' committed' if attempt['committed'] else '',
          ' missing-lgtm' if attempt['missing-lgtm'] else '',
          ' manually cancelled' if attempt['manual-cancel'] else '')
      attempts.append(copy.deepcopy(attempt))
      attempt.update(copy.deepcopy(attempt_empty))

  # An attempt is a set of actions between patch_start and patch_stop
  # actions. Repeated patch_start / patch_stop actions are ignored.
  attempt = copy.deepcopy(attempt_empty)
  results.reverse()
  state = 'stop'
  for r in results:
    action = r['fields'].get('action')
    if state == 'stop':
      if action == 'patch_start':
        state = 'start'
        attempt['begin'] = r['timestamp']
    if state != 'start':
      continue
    attempt['actions'].append(r)
    if action == 'patch_stop':
      attempt['end'] = r['timestamp']
      message = r['fields'].get('message', '')
      if 'CQ bit was unchecked on CL' in message:
        attempt['manual-cancel'] = True
      if 'No LGTM' in message:
        attempt['missing-lgtm'] = True
      if 'Failed to commit' in message:
        attempt['failed-commit'] = True
      if 'Try jobs failed' in message and 'presubmit' in message:
        attempt['failed-presubmit-bot'] = True
      add_attempt(attempt)
      assert attempt == attempt_empty, 'attempt=%r' % attempt
      state = 'stop'
      continue
    if action == 'patch_committed':
      attempt['committed'] = True
    if action == 'patch_failed':
      attempt['reason'] = r['fields'].get('reason', {})
      if type(attempt['reason']) in [str, unicode]:
        try:
          attempt['reason'] = json.loads(attempt['reason'])
        except Exception as e:
          logging.error('Could not decode reason "%s": %s',
                        attempt['reason'], e)
      logging.info('Attempt reason: %r', attempt['reason'])
      if attempt['reason'].get('fail_type') == 'reviewer_lgtm':
        attempt['missing-lgtm'] = True
      if attempt['reason'].get('fail_type') == 'commit':
        attempt['failed-commit'] = True
      if attempt['reason'].get('fail_type') == 'simple try job':
        attempt['failed-jobs'] = attempt['reason'].get(
            'fail_details', [('unknown_master', 'unknown_bot')])

  stats = {}
  committed_set = set([a['id'] for a in attempts if a['committed']])
  stats['committed'] = len(committed_set)
  stats['attempts'] = len(attempts)
  stats['rejections'] = stats['attempts'] - stats['committed']

  logging.info('derive_patch_stats: %s has %d attempts, committed=%d',
               patch_url(patch_id), len(attempts), stats['committed'])

  missing_lgtm_set = set([
      a['id'] for a in attempts if a['missing-lgtm']])
  stats['missing-lgtm'] = len(missing_lgtm_set)
  manual_cancel_set = set([
      a['id'] for a in attempts if a.get('manual-cancel')])
  stats['manual-cancel'] = len(manual_cancel_set)
  failed_commit_set = set([
      a['id'] for a in attempts if a['failed-commit']])
  stats['failed-commit'] = len(failed_commit_set)
  failed_jobs_set = set([
      a['id'] for a in attempts if a['failed-jobs']])
  stats['failed-jobs'] = len(failed_jobs_set)
  failed_presubmit_bot_set = set([
      a['id'] for a in attempts if a['failed-presubmit-bot']])
  stats['failed-presubmit-bot'] = len(failed_presubmit_bot_set)
  stats['false-rejections'] = 0
  if stats['committed']:
    stats['false-rejections'] = len(
        set([a['id'] for a in attempts]) - committed_set
        - missing_lgtm_set - manual_cancel_set - failed_presubmit_bot_set)
  # Sum of attempt duration.
  stats['patchset-duration'] = sum([a['duration'] for a in attempts])
  if attempts:
    stats['patchset-duration-wallclock'] = (
        attempts[-1]['end'] - attempts[0]['begin'])
  else:
    stats['patchset-duration-wallclock'] = 0.0
  return patch_id, stats


def percentage(n, total):
  if total:
    return 100. * n / total
  return 0.


def round_timedelta(seconds):
  # We never care about the milliseconds when printing timedeltas:
  return datetime.timedelta(seconds=round(seconds))


def print_attempt_counts(stats, args, name, message):
  count = sum([p['count'] for p in stats[name]])
  print '  %4d attempt%s (%.1f%% of %d attempts) %s in %d patches' % (
      count, '' if count == 1 else 's',
      percentage(count, stats['attempt-count']),
      stats['attempt-count'],
      message,
      len(stats[name]))
  if args.list_rejected:
    print '\n'.join([
        '      %d %s %s' % (
        p['count'], message, patch_url(p['patch_id']))
        for p in stats[name]])
    print


def print_stats(args, stats):
  latest = stats.get('latest')
  previous = stats.get('previous')
  if not latest:
    print 'No stats to display.'
  print 'Statistics for project %s' % args.project
  print 'from %s till %s (local time).' % (
      latest['begin'], latest['end'])

  print (
      '%4d issues (%d patches) were tried by CQ, '
      'resulting in %d attempts.') % (
      latest['issue-count'], latest['patchset-count'], latest['attempt-count'])
  print('%4d patches (%.1f%% of tried patches, %.1f%% of attempts) '
        'were committed by CQ,' % (
      latest['patchset-commit-count'],
      percentage(latest['patchset-commit-count'], latest['patchset-count']),
      percentage(latest['patchset-commit-count'], latest['attempt-count'])))

  print_attempt_counts(latest, args, 'rejections', 'unsuccessful')
  print '  This includes:'
  print_attempt_counts(latest, args, 'missing-lgtm', 'missing LGTM')
  print_attempt_counts(latest, args, 'failed-commit', 'failed to commit')
  print_attempt_counts(latest, args, 'manual-cancel', 'stopped manually')
  print_attempt_counts(latest, args, 'failed-presubmit-bot',
                       'failed presubmit bot')

  if args.list_rejected:
    print
    print '%d uncommitted patches:' % len(latest['rejected-patches'])
    print '\n'.join(['  %s' % patch_url(p) for p in latest['rejected-patches']])

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
  print '  wallclock:       %8s (%3d min). Prev. %s: %8s (%3d min).' % (
      wallclock, round(wallclock.total_seconds() / 60.0), args.range,
      prev_wallclock, round(prev_wallclock.total_seconds() / 60.0))
  print '  sum of attempts: %8s (%3d min). Prev. %s: %8s (%3d min).' % (
      cq_only, round(cq_only.total_seconds() / 60.0), args.range,
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
  print '  wallclock:       %8s (%3d min). Prev. %s: %8s (%3d min).' % (
      wallclock, round(wallclock.total_seconds() / 60.0), args.range,
      prev_wallclock, round(prev_wallclock.total_seconds() / 60.0))
  print '  sum of attempts: %8s (%3d min). Prev. %s: %8s (%3d min).' % (
      cq_only, round(cq_only.total_seconds() / 60.0), args.range,
      prev_cq_only, round(prev_cq_only.total_seconds() / 60.0))

  print
  print('%d attempts (%.1f%% of %d attempts) were false rejections\n'
        '  (CQ eventually landed the patch it previously rejected)' % (
      latest['patchset-false-reject-count'],
      percentage(latest['patchset-false-reject-count'],
                 latest['attempt-count']),
      latest['attempt-count']))
  # TODO(sergeyberezin): add breakdown by #attempts.

  if args.list_false_rejections:
    print
    print '%d patches had false rejections:' % len(latest['false-rejections'])
    print '\n'.join(['  %2d false rejections: %s' % (
        p['count'], patch_url(p['patch_id']))
        for p in latest['false-rejections']])
    print
    print '%d patches committed that were first rejected for missing LGTM:' % (
        len(latest['missing-lgtm']),)
    print '\n'.join([
        '  %s' % patch_url(p['patch_id'])
        for p in latest['missing-lgtm']
        if latest['patch_stats'][p['patch_id']]['committed']])
    manual_cancels = [
        '  %d manual cancellations %s' % (p['count'], patch_url(p['patch_id']))
        for p in latest['manual-cancel']
        if latest['patch_stats'][p['patch_id']]['committed']]
    print '%d patches committed that were first stopped manually:' % (
        len(manual_cancels),)
    print '\n'.join(manual_cancels)

    failed_presubmit_bot = [
        '  %d failures %s' % (p['count'], patch_url(p['patch_id']))
        for p in latest['failed-presubmit-bot']
        if latest['patch_stats'][p['patch_id']]['committed']]
    print '%d patches committed that first failed presubmit bot:' % (
        len(failed_presubmit_bot),)
    print '\n'.join(failed_presubmit_bot)

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
  print 'Top flaky builders (which fail and succeed in the same patch):'

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
        job, '%5d' % passes, '%5d' % failures,
        '%6.2f%%' % percentage(failures, passes + failures))


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
