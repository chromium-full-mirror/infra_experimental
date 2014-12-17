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
# Expects % project.
TREE_STATUS_URL = 'http://%s-status.appspot.com'
PROJECTS = {
    'chromium': {
        'tree-status': TREE_STATUS_URL % 'chromium',
        'type': 'git',
        'repo': 'https://chromium.googlesource.com/chromium/src',
    },
    'blink': {
        'tree-status': TREE_STATUS_URL % 'blink',
        'type': 'svn',
        'repo': 'svn://svn.chromium.org/blink/trunk/',
    },
    'infra': {
        'type': 'git',
        'repo': 'https://chromium.googlesource.com/infra/infra',
    },
}
# Map of intervals to minutes.
INTERVALS = {
    'week': 60 * 24 * 7,
    'day': 60 * 24,
    'hour': 60,
    '15min': 15,
}
VALID_REASONS = collections.OrderedDict([
    ('manual-cancel', {
        'item': 'stopped manually',
        'message': 'stopped manually (CQ box was unchecked)',
    }),
    ('missing-lgtm',  {
        'item': 'missed LGTM',
        'message': 'are missing LGTM',
    }),
    ('not-lgtm',  {
        'item': 'NOT LGTMs',
        'message': 'have been disapproved (NOT LGTM)',
    }),
    ('failed-patch', {
        'item': 'failures',
        'message': 'failed to apply patch',
    }),
    ('invalid-delimiter', {
        'item': 'errors',
        'message': 'have incorrect CQ_EXTRA_TRYBOTS flag',
    }),
    ('failed-presubmit-bot', {
        'item': 'failures',
        'message': 'failed presubmit bot (often due to missing OWNERS LGTM)',
    }),
])
FLAKY_REASONS = collections.OrderedDict([
    ('failed-commit', {
        'item': 'failures',
        'message': 'failed to commit',
    }),
    ('failed-jobs', {
        'item': 'failures',
        'message': 'failed jobs (excluding presubmit)',
    }),
    ('failed-to-trigger', {
        'item': 'failures',
        'message': 'failed to trigger jobs',
    }),
    ('failed-presubmit-check', {
        'item': 'failures',
        'message': 'failed presubmit check',
    }),
])
KNOWN_REASONS = collections.OrderedDict()
KNOWN_REASONS.update(VALID_REASONS)
KNOWN_REASONS.update(FLAKY_REASONS)

REASONS = collections.OrderedDict()
REASONS.update(KNOWN_REASONS)
REASONS['failed-unknown'] = {
    'item': 'failures',
    'message': 'failed for any other reason',
}


def parse_args():
  parser = argparse.ArgumentParser(description=sys.modules['__main__'].__doc__)
  parser.add_argument(
      '--project',
      required=True,
      choices=PROJECTS.keys(),
      help='Collect stats about this project.')
  parser.add_argument(
      '--bot', type=str, dest='bots',
      action='append',
      default=['blink-deps-roller@chromium.org',
               'chrome-admin@google.com',
               'chrome-release@google.com',
               'chromeos-commit-bot@chromium.org',
               'skia-deps-roller@chromium.org',
              ],
      help=('Add an author to be treated as a bot. '
            'Repeat to add several bots. Default: %(default)s.'))
  parser.add_argument(
      '-v', '--verbose',
      default='error',
      choices=['debug', 'info', 'warning', 'error', 'critical'],
      help='Set verbosity level. Default=%(default)s.')
  parser.add_argument(
      '--seq', action='store_true',
      help='Run everything sequentially for debugging.')
  parser.add_argument(
      '--thread-pool', type=int, default=200,
      help='Fetch data using this many parallel threads. Default=%(default)s.')
  parser.add_argument(
      '--list-rejections', action='store_true',
      help='List rejected CLs and reasons for rejection.')
  parser.add_argument(
      '--list-false-rejections', action='store_true',
      help='List CLs that were committed in more than one attempt.')
  parser.add_argument(
      '--date',
      help='Start date of stats YYYY-MM-DD[ HH[:MM]]. Default: --range ago.')
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
  else:
    args.date = (datetime.datetime.now() -
                 datetime.timedelta(minutes=INTERVALS[args.range]))

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


def date_from_git(date_str):
  """If date_str is not valid or None, return None."""
  if not date_str:
    return None
  date = None
  try:
    date = datetime.datetime.strptime(
        date_str, '%a %b %d %H:%M:%S %Y')
  except Exception:
    pass
  return date


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
      logging.warning('Failed to fetch (attempt %d) %s: %s', retry + 1, url, e)
  logging.error('Permanently failed to fetch %s: %s', url, e)
  return result


def fetch_tree_status(project, end_date, start_date=None, limit=1000):
  end_timestamp = int(time.mktime(end_date.timetuple()))
  params = {
      'format': 'json',
      'limit': limit,
      # Confusingly, the range is endTime <= t < startTime.
      'startTime': end_timestamp,
  }
  if start_date:
    params['endTime'] = int(time.mktime(start_date.timetuple()))
  query = 'allstatus?' + urllib.urlencode(params)
  if 'tree-status' not in PROJECTS[project]:
    return []
  url = urlparse.urljoin(PROJECTS[project]['tree-status'], query)
  logging.debug('Fetching %s', url)
  status = fetch_json(url)
  # Bug in AE app: it may return events outside of time range.
  def entry(event):
    date_utc = date_from_string(event['date'])
    date_local = date_from_timestamp(calendar.timegm(date_utc.utctimetuple()))
    return {'date': date_local,
            'open': event['general_state'] == 'open'}
  def in_range(entry):
    logging.debug('in_range(%r)', entry)
    if entry['date'] >= end_date:
      return False
    if not start_date:
      return True
    return start_date <= entry['date']

  if not status or type(status) is not list:
    status = []
  status = [entry(event) for event in status]
  status = sorted([e for e in status if in_range(e)], key=lambda e: e['date'])
  return status


def fetch_git_page(repo_url, cursor=None, page_size=2000):
  """Fetch one page worth of logs from gitiles."""
  params = {
      'pretty': 'full',
      'format': 'JSON',
      'n': page_size,
  }
  if cursor:
    params.update({'s': cursor})
  url = '%s/%s?%s' % (repo_url, '/+log/master', urllib.urlencode(params))
  logging.debug('fetch_git_page: url = %s', url)
  try:
    # Strip off the anti-XSS string from the response.
    response = urllib2.urlopen(url)
    lines = [l.rstrip() for l in response if l.rstrip() != ")]}'"]
    raw_data = ''.join(lines)
    page = json.loads(raw_data)
  except Exception as e:
    page = {}
    logging.error('Failed to fetch a page: %s', e)
  return page


def fetch_git_logs(repo, from_date, to_date):
  """Fetch all logs from Gitiles for the given date range.

  Gitiles does not natively support time ranges, so we just fetch
  everything until the range is covered. Assume that logs are ordered
  in reverse chronological order.
  """
  cursor = ''
  commit_date = to_date
  data = []
  while(cursor is not None):
    page = fetch_git_page(repo, cursor)
    logs = page.get('log', [])
    cursor = page.get('next')
    for log in logs:
      committer = log.get('committer', {})
      commit_date = date_from_git(committer.get('time'))
      if not commit_date:
        continue
      if commit_date > to_date:
        continue
      if commit_date < from_date:
        break
      data.append({
          'author': log.get('author', {}).get('email'),
          'date': commit_date,
          'commit-bot': bool('commit-bot' in committer.get('email', '')),
          'revision': log.get('commit'),
      })

    if commit_date < from_date:
      break
  return data


def fetch_svn_logs(repo, from_date, to_date):
  def local_to_utc(LocalTime):
    EpochSecond = time.mktime(LocalTime.timetuple())
    utcTime = datetime.datetime.utcfromtimestamp(EpochSecond)
    return utcTime

  from_date = local_to_utc(from_date)
  to_date = local_to_utc(to_date)
  range_str = (
      '{%s +0000}:{%s +0000}' % (from_date, to_date))
  out = subprocess.check_output(
      ['svn', 'log', '--with-all-revprops', '--xml', repo, '-r', range_str])
  data = []
  for logentry in ElementTree.XML(out).findall('logentry'):
    date_str = logentry.find('date').text
    date = datetime.datetime(*map(int, re.split('[^\d]', date_str)[:-1]))
    entry = {
        'author': logentry.find('author').text,
        'date': date,
        'revprops': {},
        'commit-bot': False,
    }
    revprops = logentry.find('revprops')
    if revprops is not None:
      for revprop in revprops.findall('property'):
        entry['revprops'][revprop.attrib['name']] = revprop.text
        if revprop.attrib['name'] == 'commit-bot':
          entry['commit-bot'] = True
    data.append(entry)
  return data

def fetch_stats(args, begin_date=None, stats_range=None):
  if not begin_date:
    begin_date = args.date
  if not stats_range:
    stats_range = args.range
  if begin_date:
    timestamp = (int(time.mktime(begin_date.timetuple())) +
                 INTERVALS[stats_range] * 60)
  else:
    timestamp = int(time.time())

  params = {
      'interval_minutes': INTERVALS[stats_range],
      'end': timestamp,
      'count': 2, # Fetch requested and previous set, for comparison.
  }
  if args.project:
    params['project'] = args.project

  query = 'stats/query?' + urllib.urlencode(params)
  url = urlparse.urljoin(STATS_URL, query)
  logging.debug('Fetching %s', url)
  return fetch_json(url)


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


def default_stats():
  """Generate all the required stats fields with default values."""
  stats = {
      'begin': datetime.datetime.now(),
      'end': datetime.datetime(1, 1, 1),
      'issue-count': 0,
      'patchset-count': 0,
      'attempt-count': 0,
      'patch_stats': {},
      'patchset-false-reject-count': 0, # Deprecated stats?
      'attempt-reject-count': 0, # Num. of rejected attempts
      'attempt-false-reject-count': 0, # Num. of falsely rejected attempts
      'false-rejections': [], # patches with falsely rejected attempts
      'rejections': [],       # patches with rejected attempts
      'rejected-patches': set(), # Patches that never committed
      'patchset-commit-count': 0,
      'patchset-total-commit-queue-durations': derive_list_stats([0]),
      'patchset-durations': derive_list_stats([0]),
      'patchset-committed-durations': derive_list_stats([0]),
      'patchset-attempts': derive_list_stats([0]),
      'patchset-committed-attempts': derive_list_stats([0]),
      'jobs': {},
      'tree': {'open': 0.0, 'total': 0.0},
      'usage': {},
  }
  for r in REASONS:
    stats[r] = []
  return stats


def organize_stats(stats, latest_init=None, previous_init=None):
  """Changes cached lists of stats into dictionaries.

  Return a dict mapping ('latest' | 'previous') -> stat.name -> <stats json>.
  If latest/previous_init are given, add to those stats rather than
  compute them from scratch.
  """
  if 'results' not in stats:
    return None
  result = {
      'latest' : latest_init if latest_init else default_stats(),
      'previous': previous_init if previous_init else default_stats()}
  for dataset, name in zip(stats['results'], ['latest', 'previous']):
    if not result[name]['begin']:
      result[name]['begin'] = date_from_timestamp(dataset['begin'])
    else:
      result[name]['begin'] = min(
          date_from_timestamp(dataset['begin']), result[name]['begin'])
    result[name]['end'] = max(date_from_timestamp(dataset['end']),
                              result[name]['end'])
    re_trybot_pass_count = re.compile('^trybot-(.+)-pass-count$')
    re_trybot_false_reject_count = re.compile(
        '^trybot-(.+)-false-reject-count$')
    assert 'jobs' in result[name] and type(result[name]['jobs']) is dict
    for data in dataset['stats']:
      if data['type'] == 'count':
        result[name][data['name']] = data['count']
        match_pass = re_trybot_pass_count.match(data['name'])
        match_false_reject = re_trybot_false_reject_count.match(data['name'])
        if match_pass:
          job_name = match_pass.group(1)
          result[name]['jobs'].setdefault(job_name, {
              'pass-count': 0,
              'false-reject-count': 0,
          })
          result[name]['jobs'][job_name]['pass-count'] += data['count']
          logging.debug('Job %s passed %d times. Jobs: %r',
                        job_name, data['count'], result[name]['jobs'])
        if match_false_reject:
          job_name = match_false_reject.group(1)
          result[name]['jobs'].setdefault(job_name, {
              'pass-count': 0,
              'false-reject-count': 0,
          })
          result[name]['jobs'][job_name]['false-reject-count'] += data['count']
          logging.debug('Job %s flakily failed %d times',
                        job_name, data['count'])
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
  if not series:
    series = [0]
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


def stats_by_count_entry(patch_stats, name, patch, reasons):
  entry = {
      'count': patch_stats[name],
      'patch_id': patch,
      'failed-jobs-details': patch_stats['failed-jobs-details']
  }
  for n in reasons:
    if n in patch_stats:
      entry[n] = patch_stats[n]
      assert type(entry[n]) is int, 'Bad type in %s[%s]: %r\nEntry=%r' % (
        patch, n, entry[n], entry)
  return entry


# "Dangerous default value []": pylint: disable=W0102
def stats_by_count(patch_stats, name, reasons=[]):
  return sort_by_count([
      stats_by_count_entry(patch_stats[p], name, p, reasons)
      for p in patch_stats if patch_stats[p].get(name)])


def derive_stats(args, begin_date, init_stats=None):
  """Process raw CQ updates log and derive stats.

  Return the same format as organize_stats().
  Assumes |results| are action=patch_stop logs sorted by timestamp in
  descending order.
  If |init_stats| are given, preserve the jobs stats and replace the
  other stats.
  """
  stats = init_stats if init_stats else default_stats()
  filters = ['project=%s' % args.project, 'action=patch_stop']
  end_date = begin_date + datetime.timedelta(minutes=INTERVALS[args.range])
  results = fetch_cq_logs(begin_date, end_date, filters=filters)
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
  def get_patch_stats(patch_id):
    return derive_patch_stats(end_date, patch_id)

  if args.seq or not args.thread_pool:
    iterable = map(get_patch_stats, patches)
  else:
    pool = ThreadPool(min(args.thread_pool, len(patches)))
    iterable = pool.imap_unordered(get_patch_stats, patches)
  for patch_id, pstats in iterable:
    patch_stats[patch_id] = pstats

  # stats['patch_stats'] = patch_stats
  # stats['attempt-count'] = sum([
  #     patch_stats[p]['attempts'] for p in patch_stats])
  # stats['patchset-false-reject-count'] = sum([
  #     patch_stats[p]['false-rejections'] for p in patch_stats])
  # stats['attempt-reject-count'] = sum([
  #     patch_stats[p]['rejections'] for p in patch_stats])
  # stats['rejected-patches'] = set([
  #     p for p in patch_stats if not patch_stats[p]['committed']])
  # stats['false-rejections'] = stats_by_count(
  #     patch_stats, 'false-rejections', REASONS)
  # stats['rejections'] = stats_by_count(patch_stats, 'rejections', REASONS)
  # for r in REASONS:
  #   stats[r] = stats_by_count(patch_stats, r, set(REASONS) - set([r]))

  # stats['patchset-commit-count'] = len([
  #     p for p in patch_stats if patch_stats[p]['committed']])
  # stats['patchset-total-commit-queue-durations'] = derive_list_stats([
  #     patch_stats[p]['patchset-duration-wallclock'] for p in patch_stats])
  # stats['patchset-durations'] = derive_list_stats([
  #     patch_stats[p]['patchset-duration'] for p in patch_stats])
  # stats['patchset-committed-durations'] = derive_list_stats([
  #     patch_stats[p]['patchset-duration'] for p in patch_stats
  #     if patch_stats[p]['committed']])
  # stats['patchset-attempts'] = derive_list_stats([
  #     patch_stats[p]['attempts'] for p in patch_stats])
  # stats['patchset-committed-attempts'] = derive_list_stats([
  #     patch_stats[p]['attempts'] for p in patch_stats
  #     if patch_stats[p]['committed']])
  return patch_stats


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

def parse_failing_tryjobs(message):
  """Parse the message of failing try jobs."""
  builders = []
  msg_ary = message.split('\n')
  for ln in msg_ary[1:]:
    builder = ln.split()[0]
    builders.append(builder)
  return builders

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


def derive_patch_stats(end_date, patch_id):
  """|patch_id| is a tuple (issue, patchset)."""
  # Assume the results are in descendent order by timestamp.
  results = fetch_cq_logs(end_date=end_date, filters=[
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
  }
  for r in REASONS:
    attempt_empty[r] = False
  attempt_empty['false-rejection'] = False

  attempt_id = {'id': 0}

  def add_attempt(attempt):
    if attempt['actions']:
      attempt_id['id'] += 1
      attempt['id'] = attempt_id['id']
      attempt['duration'] = attempt['end'] - attempt['begin']
      known_reasons = [r for r in KNOWN_REASONS if attempt[r]]
      if not attempt['committed'] and not known_reasons:
        attempt['failed-unknown'] = True
      logging.debug(
          'add_attempt: #%d (%s)',
          attempt['id'],
          ', '.join([r for r in REASONS if attempt[r]]))
      attempts.append(copy.deepcopy(attempt))
      attempt.update(copy.deepcopy(attempt_empty))

  # An attempt is a set of actions between patch_start and patch_stop
  # actions. Repeated patch_start / patch_stop actions are ignored.
  attempt = copy.deepcopy(attempt_empty)
  failing_builders = {}
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
      if 'A disapproval has been posted' in message:
        attempt['not-lgtm'] = True
      if 'Transient error: Invalid delimiter' in message:
        attempt['invalid-delimiter'] = True
      if 'Failed to commit' in message:
        attempt['failed-commit'] = True
      if('Failed to apply patch' in message or
         'Failed to apply the patch' in message):
        attempt['failed-patch'] = True
      if 'Presubmit check' in message:
        attempt['failed-presubmit-check'] = True
      if 'Try jobs failed' in message:
        if 'presubmit' in message:
          attempt['failed-presubmit-bot'] = True
        else:
          attempt['failed-jobs'] = message
          builders = parse_failing_tryjobs(message)
          for b in builders:
            failing_builders.setdefault(b, 0)
            failing_builders[b] += 1
      if 'Exceeded time limit waiting for builds to trigger' in message:
        attempt['failed-to-trigger'] = True
      add_attempt(attempt)
      assert attempt == attempt_empty, 'attempt=%r' % attempt
      state = 'stop'
      continue
    if action == 'patch_committed':
      attempt['committed'] = True
    # TODO(sergeyberezin): enable this after this action is stable in CQ.
    if False and action == 'patch_failed':
      attempt['reason'] = parse_json(r['fields'].get('reason', {}))
      logging.info('Attempt reason: %r', attempt['reason'])
      if attempt['reason'].get('fail_type') == 'reviewer_lgtm':
        attempt['missing-lgtm'] = True
      if attempt['reason'].get('fail_type') == 'commit':
        attempt['failed-commit'] = True
      if attempt['reason'].get('fail_type') == 'simple try job':
        failed_jobs = parse_json(attempt['reason'].get(
            'fail_details', [('unknown_master', 'unknown_bot')]))
        # Remove presubmit bot - it's accounted separately.
        if type(failed_jobs) is list:
          failed_jobs = [j for j in failed_jobs if 'presubmit' in j[1]]
        attempt['failed-jobs'] = failed_jobs

  stats = {'patch_id': patch_id}
  committed_set = set([a['id'] for a in attempts if a['committed']])
  stats['committed'] = len(committed_set)
  stats['attempts'] = len(attempts)
  stats['rejections'] = stats['attempts'] - stats['committed']

  logging.info('derive_patch_stats: %s has %d attempts, committed=%d',
               patch_url(patch_id), len(attempts), stats['committed'])

  valid_reasons_set = set()
  for r in VALID_REASONS:
    s = set([a['id'] for a in attempts if a[r]])
    stats[r] = len(s)
    valid_reasons_set.update(s)
  for r in set(REASONS) - set(VALID_REASONS):
    stats[r] = len(set([a['id'] for a in attempts if a[r]]))

  # Populate failed builders.
  stats['failed-jobs-details'] = failing_builders

  stats['false-rejections'] = 0
  if stats['committed']:
    stats['false-rejections'] = len(
        set([a['id'] for a in attempts]) - committed_set - valid_reasons_set)
  # Determine false rejection start and end times.
  last_false_rejection = 0
  if stats['false-rejections']:
    for a in attempts:
      for r in FLAKY_REASONS:
        if a[r]:
          a['false-rejection'] = True
    stats['begin_false_rejection'] = maybe_min(
        a['begin'] for a in attempts if a['false-rejection'])
    last_false_rejection = maybe_max(
        a['begin'] for a in attempts if a['false-rejection'])
    # The first attempt after the last false rejection.
    stats['end_false_rejection'] = maybe_min(
        a['begin'] for a in attempts if a['begin'] > last_false_rejection)

  # Sum of attempt duration.
  stats['patchset-duration'] = sum([a['duration'] for a in attempts])
  if attempts:
    stats['patchset-duration-wallclock'] = (
        attempts[-1]['end'] - attempts[0]['begin'])
  else:
    stats['patchset-duration-wallclock'] = 0.0
  return patch_id, stats


def percentage_tuple(data, total):
  num_data = data if isinstance(data, numbers.Number) else len(data)
  num_total = total if isinstance(total, numbers.Number) else len(total)
  percent = 100. * num_data / num_total if num_total else 0
  return num_data, num_total, percent


def percentage(data, total):
  return percentage_tuple(data, total)[2]


def round_timedelta(seconds):
  # We never care about the milliseconds when printing timedeltas:
  return datetime.timedelta(seconds=round(seconds))


def print_attempt_counts(stats, name, message, item_name='',
                         details=False, committed=None, indent=0,
                         print_zero=False):
  """Print a summary of a |name| slice of attempts.

  |committed|: None=print all, True=only committed patches, False=only
   rejected patches.

  |print_zero|: print stats even if no attempts match."""
  if not item_name:
    item_name = message
  patches = [
      p for p in stats[name]
      if committed is None or
      bool(stats['patch_stats'][p['patch_id']]['committed']) is committed]
  count = sum([p['count'] for p in patches])
  if not print_zero and not count:
    return

  failing_builders = {}
  for p in patches:
    for b, cnt in p['failed-jobs-details'].iteritems():
      failing_builders.setdefault(b, {})
      failing_builders[b][p['patch_id']] = cnt

  indent_str = ''.join([' ' for _ in range(indent)])
  if message.startswith('failed jobs'):
    print '%s%4d attempt%s (%.1f%% of %d attempts) %s: %d in %d%s patches' % (
        indent_str, count, ' ' if count == 1 else 's',
        percentage(count, stats['attempt-count']),
        stats['attempt-count'],
        message,
        sum([sum(d.values()) for d in failing_builders.values()]),
        len(patches),
        ' committed' if committed is True else
        ' uncommitted' if committed is False else '')
  else:
    print '%s%4d attempt%s (%.1f%% of %d attempts) %s in %d%s patches' % (
        indent_str, count, ' ' if count == 1 else 's',
        percentage(count, stats['attempt-count']),
        stats['attempt-count'],
        message,
        len(patches),
        ' committed' if committed is True else
        ' uncommitted' if committed is False else '')
  if details:
    lines = []
    for p in patches:
      line = '      %d %s %s'  % (
          p['count'], item_name, patch_url(p['patch_id']))
      extra = []
      for k in p:
        if k not in ['count', 'patch_id', 'failed-jobs-details']:
          extra.append(k)
      causes = []
      if extra:
        causes = ['%d %s' % (p[k], k) for k in extra if p[k]]
      if p['failed-jobs-details']:
        causes.extend(
            ['%d %s' % (p['failed-jobs-details'][k], k)
             for k in p['failed-jobs-details']])
      if causes:
        line += ' (%s)' % ', '.join(causes)
      lines.append(line)
    if lines:
      print '\n'.join(lines)
      print


def print_duration(name, args, latest, print_name=None):
  if not print_name:
    print_name = name.capitalize()
  print
  cq_only = round_timedelta(latest['patchset-durations'][name])
  wallclock = round_timedelta(
      latest['patchset-total-commit-queue-durations'][name])
  print '%s duration in CQ trying a patch:' % print_name
  print '  wallclock:       %8s (%3d min).' % (
      wallclock, round(wallclock.total_seconds() / 60.0))
  print '  sum of attempts: %8s (%3d min).' % (
      cq_only, round(cq_only.total_seconds() / 60.0))


def print_stats(args, stats):
  latest = stats.get('latest')
  if not latest:
    print 'No stats to display.'
  print 'Statistics for project %s' % args.project
  if latest['begin'] > latest['end']:
    print '  No stats since %s' % args.date
    return

  print 'from %s till %s (local time).' % (
      latest['begin'], latest['end'])

  print
  print (
      '%4d issues (%d patches) were tried by CQ, '
      'resulting in %d attempts.') % (
      latest['issue-count'], latest['patchset-count'], latest['attempt-count'])
  print('%4d patches (%.1f%% of tried patches, %.1f%% of attempts) '
        'were committed by CQ,' % (
      latest['patchset-commit-count'],
      percentage(latest['patchset-commit-count'], latest['patchset-count']),
      percentage(latest['patchset-commit-count'], latest['attempt-count'])))


  print
  print 'Rejections:'
  print_attempt_counts(latest, 'rejections', 'were unsuccessful',
                       item_name='failures',
                       committed=False)
  print '  This includes:'
  for r in REASONS:
    print_attempt_counts(latest, r, REASONS[r]['message'], indent=2,
                         details=args.list_rejections,
                         item_name=REASONS[r]['item'], committed=False)

  # TODO(sergeyberezin): add gave up count (committed manually after trying CQ).
  # TODO(sergeyberezin): add count of NOTRY=true (if possible).

  print
  print 'False Rejections:'
  print_attempt_counts(latest, 'false-rejections', 'were false rejections',
                       item_name='flakes', committed=True)
  print '  %4d attempts (%.1f%% of %d attempts) were false rejections' % (
      latest['attempt-false-reject-count'],
      percentage(latest['attempt-false-reject-count'],
                 latest['attempt-count']),
      latest['attempt-count'])

  print '  False rejections include:'
  for r in FLAKY_REASONS.keys() + ['failed-unknown']:
    print_attempt_counts(latest, r, REASONS[r]['message'], indent=2,
                         item_name=REASONS[r]['item'], committed=True,
                         details=args.list_false_rejections)

  print '  Other rejections in committed patches for valid reasons:'
  for r in VALID_REASONS.keys():
    print_attempt_counts(latest, r, REASONS[r]['message'], indent=2,
                         item_name=REASONS[r]['item'], committed=True,
                         details=args.list_false_rejections)

  print_duration('mean', args, latest)
  print_duration('50', args, latest, 'Median')

  print
  print 'Patches which eventually land percentiles:'
  for p in ['10', '25', '50', '75', '90', '95', '99']:
    print '%s: %4.1f hrs, %2d attempts' % (
        p, latest['patchset-committed-durations'][p] / 3600.0,
        latest['patchset-committed-attempts'][p])

  # TODO(sergeyberezin): add total try jobs / by CQ / unknown. Get it from CBE.
  # TODO(sergeyberezin): recompute bot flakiness from CBE. CQ does not
  # have enough info.
  print
  print 'Top flaky builders (which fail and succeed in the same patch):'

  logging.debug('Found %d jobs', len(latest['jobs'].keys()))

  def flakiness(stats, job):
    passes = stats['jobs'][job]['pass-count']
    failures = stats['jobs'][job]['false-reject-count']
    return percentage(failures, passes + failures)

  jobs = sorted(latest['jobs'].iterkeys(), key=lambda j: flakiness(latest, j),
                reverse=True)
  print '%-40s %-15s %-15s %-15s' % (
      'Builder Name', 'Succeeded', 'Flaky Failures', 'Flakiness (%)')
  for job in jobs:
    passes = latest['jobs'][job]['pass-count']
    failures = latest['jobs'][job]['false-reject-count']
    print '%-40s %-15s %-15s %-15s' % (
        job, '%5d' % passes, '%5d' % failures,
        '%6.2f%%' % flakiness(latest, job))


def acquire_stats(args):
  stats = {}
  logging.info('Acquiring stats for project %s for a %s of %s',
               args.project, args.range, args.date)
  end_date = args.date + datetime.timedelta(minutes=INTERVALS[args.range])
  prev_date = args.date - datetime.timedelta(minutes=INTERVALS[args.range])
  init_stats = {'latest': default_stats(), 'previous': default_stats()}
  assert args.date
  init_stats = organize_stats(fetch_stats(args))
  patch_stats = derive_stats(
      args, args.date, init_stats=init_stats['latest'])

  return patch_stats


def process_false_rejections(patch_stats):
  # Sort by end date.
  false_rejections = sorted(
      [s for s in patch_stats.values() if s['false-rejections']],
      key=lambda s: s['end_false_rejection'])
  print '\t'.join(['Patchset', 'Begin', 'End'] + ['%s' % h for h in range(24)])
  prev_day = None
  for patch in false_rejections:
    begin = date_from_timestamp(patch['begin_false_rejection'])
    end = date_from_timestamp(patch['end_false_rejection'])
    day = datetime.datetime(end.year, end.month, end.day)
    if day != prev_day:
      print '\t'.join(['-', '-', '%s' % day] + ['-' for _ in range(24)])
    prev_day = day
    values = [patch_url(patch['patch_id']), str(begin), str(end)]
    for hour in range(24):
      d = day + datetime.timedelta(hours=hour)
      values.append('x' if begin <= d and d < end else ' ')
    print '\t'.join(values)

def main():
  args = parse_args()
  logging.basicConfig(level=args.verbose)
  patch_stats = acquire_stats(args)
  process_false_rejections(patch_stats)
#  print_stats(args, stats)


if __name__ == '__main__':
  sys.exit(main())
