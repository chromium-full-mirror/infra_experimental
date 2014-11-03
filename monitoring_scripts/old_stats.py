#!/usr/bin/python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
'''Generate stats of CQ usage.'''

# sudo apt-get install pip; sudo pip install requests request_cache
import argparse
import collections
from datetime import timedelta, datetime
import itertools
import json
import logging
import numpy
import operator
import os
import re
import requests_cache
import sys
import urllib2

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

import projects
import projects_utils
import system_utils


class Unbuffered:
  def __init__(self, stream):
    self.stream = stream
  def write(self, data):
    self.stream.write(data)
    self.stream.flush()
  def __getattr__(self, attr):
    return getattr(self.stream, attr)
sys.stdout = Unbuffered(sys.stdout)


CONFIG = { 'target_base_url_regexps' : [] }

# Threshold to filter out builders, which are started manually and do not have
# sufficient data to produce statistically significant results. Number of
# succeeded builds and flaky failures should be larger than this threshold. The
# reliability of the results is intuitively inversely proportional to this
# number.
FLAKINESS_THRESHOLD = 50


def setup_config(options):
  """Set the list of base URLs.

  Currently it's a hack to grab it from commit queue projects.py.
  """
  options.dry_run = True
  options.fake = True
  options.no_try = True
  options.user = 'commit-bot@chromium.org'
  options.rietveld = 'https://codereview.chromium.org'
  work_dir = os.path.join(ROOT_DIR, 'workdir')
  pending_manager = projects.load_project(work_dir, options)
  project_bases = pending_manager.project_bases
  if pending_manager.project_bases_legacy:
    project_bases = pending_manager.project_bases_legacy
  CONFIG['target_base_url_regexps'] = [re.compile(r) for r in project_bases]
  logging.debug('Setup CONFIG = %r', CONFIG)


requests_cache.install_cache('cq')
session = requests_cache.CachedSession()


def percentage(n, total):
  if total:
    return 100. * n / total
  return 0.


def fetch_recent_issues(limit, args, cursor=None):
  search_url = ('https://codereview.chromium.org/search?format=json&'
                'limit=%d') % limit
  if cursor:
    search_url += '&cursor=%s' % cursor
  if args.modified_after:
    search_url += '&modified_after=%s' % args.modified_after
  if args.modified_before:
    search_url += '&modified_before=%s' % args.modified_before
  if args.owner:
    search_url += '&owner=%s' % urllib2.quote(args.owner)
  response = session.get(search_url)
  return response.json()


def get_target_base_url_regexps():
  return CONFIG['target_base_url_regexps']


def matches_target_base_url(url):
  for regexp in get_target_base_url_regexps():
    match = regexp.match(url)
    if match:
      return True
  return False


def issue_patch_string(issue_id, patch_id):
  return '%s:%s' % (issue_id, patch_id)


def issue_display_url(issue_id):
  return 'https://codereview.chromium.org/%s' % issue_id


def issue_patch_display_url(issue_patch):
  """Convert 'issue_id:patch_id' string into a URL."""
  issue_patch_split = issue_patch.split(':')
  assert len(issue_patch_split) == 2, 'Bad issue_patch: %s' % issue_patch
  issue_id = issue_patch_split[0]
  patch_id = issue_patch_split[1]
  return '%s/#ps%s' % (issue_display_url(issue_id), patch_id)


def issue_url(issue_id):
  return 'https://codereview.chromium.org/api/%s?messages=true' % issue_id


def patchset_url(issue_id, patchset_id):
  return 'https://codereview.chromium.org/api/%s/%s' % (issue_id, patchset_id)


def date_from_iso_str(iso_str):
  # Issues have one of two formats:
  #   2013-10-17 16:43:04.391480
  #   2013-10-17 16:43:04
  try:
    return datetime.strptime(iso_str, '%Y-%m-%d %H:%M:%S.%f')
  except ValueError:
    return datetime.strptime(iso_str, '%Y-%m-%d %H:%M:%S')


def date_in_range(date, from_date, to_date):
  """Check for from_date <= date < to_date.

  If a boundary is None, assume no constraint.
  """
  if from_date and date < from_date:
    return False
  if to_date and date >= to_date:
    return False
  return True


def round_timedelta(delta):
  # We never care about the milliseconds when printing timedeltas:
  return timedelta(seconds=round(delta.total_seconds()))


def fetch_issue(issue_id):
  url = issue_url(issue_id)
  return fetch_url(url)


def fetch_patchset(issue_id, patchset_id):
  return fetch_url(patchset_url(issue_id, patchset_id))


def fetch_url(url):
  try:
    this_json = session.get(url).json()
  except Exception as e:
    logging.error('while fetching %s: %s', url, str(e))
    this_json = None
  # pylint: disable=W0212
  cache_key = session.cache._url_to_key(url)
  _, now = session.cache.get_response_and_time(cache_key)
  return this_json, now


def format_line(values, aligns, widths):
  values = map(str, values)
  args = zip(values, aligns, widths)
  return ' '.join([apply(align, (value, width))
                   for value, align, width in args])


class CQAttempt(object):
  def __init__(self):
    self.result = None
    self.patch_id = None
    self.issue_id = None
    self.author = None
    self.start_time = None
    self.end_time = None
    self.cq_retry = False

  @property
  def issue_patch_string(self):
    return issue_patch_string(self.issue_id, self.patch_id)

  @property
  def duration(self):
    return self.end_time - self.start_time


def decode_job_result(result):
  """Translate the numeric result into a string."""
  result_map = { -1 : 'processing',
                  0 : 'succeeded',
                  1 : 'warnings',
                  2 : 'failed',
                  3 : 'skipped',
                  5 : 'exception',
                  6 : 'pending' }
  return result_map.get(int(result), 'unknown')

class CQAnalyzer(object):
  def __init__(self, args):
    self.args = args
    self.state = None
    self.issue = None
    self.issue_id = None
    self.author = None
    self.patch_id = None
    self.start_time = None
    self.attempts = []
    self.manual_commits = set()
    self.no_try_issues = set()
    self.now = None
    # issue_id -> time since CQ start
    self.in_progress = {}
    # Stats database (dict) with the following keys:
    # 'issues': dict of issue_id -> stats database for the issue_id (see below)
    # 'total':  total number of jobs
    # 'commit-bot': total number of jobs submitted by CQ
    # 'unknown'    : number of jobs by unknown submitter
    # 'redundant'  : sum(succeeded-1) for each builder in the same patchset
    # 'repeated_failures' : sum(failed-1) for each builder in the same patchset
    #
    # Stats database for an individual issue (dict):
    # 'builders' : dict of builder_name -> builder stats (see below)
    # 'total', 'unknown', 'redundant', repeated_failures' - as above
    # 'commit-bot': number of jobs submitted by CQ
    #
    # Builder stats is a following dict:
    # 'results': dict of result_str -> count per CL
    # 'commit-bot', 'unknown' - as above
    self.try_jobs = {}
    self.cq_retry = False

  # pylint: disable=C0301
  start_regexp = re.compile(
      r'CQ is trying da patch.*( |/)(?P<author>.*)/(?P<issue_id>\d+)/'
      r'(?P<patch_id>\d+)$', re.DOTALL)
  # TODO(chrome-infra-cq team): Remove this var when issues with the old
  # commit message have been all crawled.
  old_committed_regexp = re.compile('Change committed as (?P<revision>\d+)')
  # pylint: disable=C0301
  # TODO(chrome-infra-cq team): The below only matches SVN revs and not commit
  # hashes.
  manual_commit_regexp = re.compile(
    'Committed patchset #(?P<patch_id>\d+) \(id:(?P<patchset>\d+)\)  manually '
    'as r?(?P<revision>\d+)')

  def _reset(self):
    self.state = None
    self.author = None
    self.patch_id = None
    self.start_time = None
    self.cq_retry = False

  def _start(self, patch_id, start_time, author=None):
    if self.state == 'START' and self.patch_id == patch_id:
      # print 'Restarted for patchset %s on %s' % (
      #     patch_id, issue_display_url(self.issue_id))
      self._end('RESTART', start_time)
    self.state = 'START'
    self.patch_id = patch_id
    self.author = author
    assert start_time
    self.start_time = start_time

  def _end(self, result, end_time):
    if self.state != 'START':
      logging.error('ERROR: %s for %s without start??' % (
        result, issue_display_url(self.issue_id)))
      self._reset()
      return
    # Only add attemps within specified time frame
    if  not date_in_range(self.start_time,
                         self.args.from_date, self.args.to_date):
      logging.debug('Rejected CQ attempt outside date range: %s',
                    self.start_time)
      self._reset()
      return

    attempt = CQAttempt()
    attempt.result = result
    attempt.patch_id = self.patch_id
    attempt.issue_id = self.issue_id
    attempt.start_time = self.start_time
    attempt.end_time = end_time
    attempt.cq_retry = self.cq_retry
    self.attempts.append(attempt)
    self._reset()

  def _start_and_end(self, patch_id, result, date):
    self._start(patch_id, date)
    self._end(result, date)

  def _end_and_start(self, result, date):
    """When CQ auto retries, end last attempt and start a new one."""
    patch_id = self.patch_id
    author = self.author
    self._end(result, date)
    self._start(patch_id, date, author)

  def _manual_commit(self, patch_id):
    self.manual_commits.add(issue_patch_string(self.issue_id, patch_id))

  def process_message(self, message):
    text = message['text']
    date = date_from_iso_str(message['date'])

    match = self.manual_commit_regexp.match(text)
    if match:
      if self.start_time:
        self._end('MANUAL_COMMIT',
                  date_from_iso_str(self.issue['modified']))
      patch_number = int(match.group('patch_id'))
      # gcl dcommit talks in terms of patch numbers 1-5, we need to map
      # those to patchset ids:
      if len(self.issue['patchsets']) > (patch_number-1):
        patch_id = self.issue['patchsets'][patch_number-1]
      else:
        logging.warning('%s missing patch number %d' % (
            self.issue_id, patch_number))
        logging.warning('Patchsets = %r', self.issue['patchsets'])
        logging.warning('issue, now = fetch_issue(\'%s\')' % self.issue_id)
        patch_id = self.issue['patchsets'][-1]
      self._manual_commit(patch_id)
      return

    if message['sender'] != 'commit-bot@chromium.org':
      return

    match = self.start_regexp.match(text)
    if match:
      self._start(match.group('patch_id'), date, match.group('author'))
      return

    cq_committed_message = 'Committed patchset '
    cq_would_have_committed_message = 'This issue passed the CQ.'
    match = (text.startswith(cq_committed_message) or
             self.old_committed_regexp.match(text) or
             (text.startswith(cq_would_have_committed_message)))
    if match:
      self._end('SUCCESS', date)
      return

    cq_end_messages = {
        'TRY': 'Retried try job',
        'TRY_JOBS_FAILED': 'Try jobs failed on following builders',
        'APPLY': 'Failed to apply patch',
        'APPLY2': 'Failed to apply the patch',
        'BAD_SVN': 'Could not make sense out of svn commit message',
        'COMPILE': 'Sorry for I got bad news for ya',
        'DESCRIPTION_CHANGED': ('Commit queue rejected this change because '
                                'the description'),
        # This is too conservative.
        'REVIEWERS_CHANGED': 'List of reviewers changed.',
        # User caused.
        'PATCH_CHANGED': 'Commit queue failed due to new patchset.',
        # FAILED_TO_TRIGGER is a very serious failure, unclear why it
        # happens!
        'FAILED_TO_TRIGGER': 'Failed to trigger a try job on',
        # BINARY_FILE is just a bug in the CQ.
        'BINARY_FILE': 'Can\'t process patch for file',
        'BINARY_FILE2': 'Failed to request the patch to try',
        # Unclear why UPDATE_STEP happens.  Likely broken bots, shouldn't
        # fail patches!
        'UPDATE_STEP': 'Step "update" is always a major failure.',
        'BERSERK': 'The commit queue went berserk',
        'INTERNAL_ERROR': 'Commit queue had an internal error.',
    }
    for result, message_text in cq_end_messages.items():
      if text.startswith(message_text):
        self._end(result, date)
        return

    cq_fail_to_start_messsages = {
        'FAILED_PATCHSET': 'Failed to get patchset properties',
        'NO_COMMENTS': 'No comments yet.',
        'NO_LGTM': 'No LGTM from a valid reviewer yet.',
    }
    for result, message_text in cq_fail_to_start_messsages.items():
      if text.startswith(message_text):
        self._start_and_end(self.patch_id, result, date)
        return

    cq_retry_message = 'FYI, CQ is re-trying this CL'
    if text.startswith(cq_retry_message):
      self._end_and_start('TRY_JOBS_FAILED', date)
      self.cq_retry = True
      return

    cq_other_messages = {
        # CQ will post another message, do not close the attempt here.
        'UNCHECK': 'The CQ bit was unchecked by commit-bot@chromium.org',
    }
    for result, message_text in cq_other_messages.iteritems():
      if text.startswith(message_text):
        # TODO(sergeyberezin): self._log_message(result, date)
        return

    logging.error('Error %s has unknown message: %s' % (
        issue_display_url(self.issue_id), text))
    self._end('UNKNOWN', date)

  def start_issue(self, issue, now):
    # We may be dealing with cached data, so cache our concept of "now"
    self.now = now
    self.issue = issue
    self.issue_id = issue['issue']

  def end_issue(self, issue):
    issue_id = issue['issue']
    assert issue_id == self.issue_id
    if self.start_time:
      if self.issue['commit']:
        logging.info('%s in progress? %s' % (
            round_timedelta(self.now - self.start_time),
            issue_display_url(self.issue_id)))
        self._end('IN_PROGRESS', self.now)
      else:
        # There are various reasons why the commit box may have
        # been unchecked, including that the issue may be closed now.
        # If those are not from a user, then that's a bug in rietveld
        # and out of scope for this script.  For now we're just ignoring
        # cases where the box was unchecked.  We could log an _end()
        # event, but which time would we use?  last_modified has at
        # best a weak corrolation with the issue close or CQ checkbox.
        self._reset()
    # _reset() shouldn't be needed, but just in case.
    self._reset()
    self.issue_id = None
    self.issue = None

  def process_try_jobs(self, issue):
    """Fetch tryjobs from the latest patchset."""
    if not issue['patchsets']:
      return
    issue_id = issue['issue']

    issues = self.try_jobs.setdefault('issues', {})
    self.try_jobs.setdefault('total', 0)
    self.try_jobs.setdefault('commit-bot', 0)
    self.try_jobs.setdefault('unknown', 0)
    self.try_jobs.setdefault('redundant', 0)
    self.try_jobs.setdefault('repeated_failures', 0)
    self.try_jobs.setdefault('pending', 0)
    # Database of job results indexed by issue_id/patch_id
    by_patchset = self.try_jobs.setdefault('by_patchset', {})
    issues[issue_id] = {
      'builders' : {}, 'total' : 0, 'commit-bot' : 0, 'unknown' : 0,
      'redundant' : 0, 'repeated_failures' : 0 }
    builders = issues[issue_id]['builders']

    for patchset_id in issue['patchsets']:
      logging.debug('process_try_jobs for issue %s: patchset = %r',
                    issue_id, patchset_id)
      patchset, _ = fetch_patchset(issue_id, patchset_id)
      if not patchset or not patchset['try_job_results']:
        logging.debug('No jobs found in issue %s patchset %s',
                      issue_id, patchset_id)
        continue
      if not date_in_range(date_from_iso_str(patchset['modified']),
                           self.args.from_date, self.args.to_date):
        logging.debug('Rejected patchset outside date range: %s',
                      patchset['modified'])
        continue
      patchset_builders = by_patchset.setdefault(
          '%s:%s' % (issue_id, patchset_id), {})
      for tryjob in patchset['try_job_results']:
        builder = builders.setdefault(tryjob['builder'], {})
        result_str = decode_job_result(tryjob['result'])
        builder_results = builder.setdefault('results', {})
        builder_results.setdefault(result_str, 0)
        builder_results[result_str] += 1
        patchset_builder = patchset_builders.setdefault(tryjob['builder'], {})
        patchset_builder.setdefault(result_str, 0)
        patchset_builder.setdefault(result_str + '_jobs', [])
        patchset_builder[result_str] += 1
        patchset_builder[result_str + '_jobs'].append(tryjob.get('url'))
        issues[issue_id]['total'] += 1
        self.try_jobs['total'] += 1
        builder.setdefault('commit-bot', 0)
        builder.setdefault('unknown', 0)
        by_cq = 1 if tryjob['requester'] == 'commit-bot@chromium.org' else 0
        by_unknown = 0 if tryjob['requester'] else 1
        builder['commit-bot'] += by_cq
        issues[issue_id]['commit-bot'] += by_cq
        self.try_jobs['commit-bot'] += by_cq
        builder['unknown'] += by_unknown
        issues[issue_id]['unknown'] += by_unknown
        self.try_jobs['unknown'] += by_unknown
        if result_str == 'pending':
          self.try_jobs['pending'] += 1

      for builder_name, builder in builders.iteritems():
        if builder_name not in patchset_builders:
          continue
        patchset_builder = patchset_builders[builder_name]
        if patchset_builder.get('succeeded', 0):
          patchset_succeeded = patchset_builder['succeeded'] - 1
          issues[issue_id]['redundant'] += patchset_succeeded
          self.try_jobs['redundant'] += patchset_succeeded
        if patchset_builder.get('failed', 0):
          patchset_repeated_failures = patchset_builder['failed'] - 1
          issues[issue_id]['repeated_failures'] += patchset_repeated_failures
          self.try_jobs['repeated_failures'] += patchset_repeated_failures
        if 'succeeded' in patchset_builder and 'failed' in patchset_builder:
          builder.setdefault('flaky_failures', 0)
          builder['flaky_failures'] += patchset_builder['failed']
          builder.setdefault('flaky_jobs', [])
          builder['flaky_jobs'].extend(patchset_builder['failed_jobs'])

    logging.info('process_try_jobs for issue %s: %r',
                 issue_id, self.try_jobs['issues'][issue_id])

  def process_issue(self, issue, now):
    issue_id = issue['issue']

    if re.search('^NOTRY=[tT][rR][uU][eE]$', issue['description'], re.M):
      self.no_try_issues.add(issue_id)

    self.start_issue(issue, now)
    for message in issue['messages']:
      self.process_message(message)
      # print '%(date)s: %(text)s' % message
    self.end_issue(issue)

  def print_attempts_table(self):
    result_getter = operator.attrgetter('result')
    attempts = sorted(self.attempts, key=result_getter)

    col_aligns = (str.rjust, str.ljust, str.rjust, str.rjust)
    col_widths = (5, 20, 16, 16)
    col_headers = ('count', 'result', 'mean duration', 'median duration')
    print
    print ('CQ Attempts by result (there can be more than '
           'one attempt on the same patch)')
    print format_line(col_headers, col_aligns, col_widths)
    print '-' * (sum(col_widths) + len(col_widths) - 1)
    for result, group_itr in itertools.groupby(attempts, result_getter):
      group = list(group_itr)
      durations = map(operator.attrgetter('duration'), group)
      mean = sum(durations, timedelta()) / len(group)
      durations_seconds = map(timedelta.total_seconds, durations)
      median_seconds = numpy.median(durations_seconds)
      median = timedelta(seconds=round(median_seconds))
      values = (len(group), result, round_timedelta(mean), median)
      print format_line(values, col_aligns, col_widths)
    print

  def print_mean_cq_duration(self):
    """Group attempts by "issue:patch" and compute mean patch duration."""
    def compute_patch_duration(attempts):
      start_time = min(map(operator.attrgetter('start_time'), attempts))
      end_time = max(map(operator.attrgetter('end_time'), attempts))
      return end_time - start_time

    patch_attempts = {}
    attempts = sorted(self.attempts,
                      key=operator.attrgetter('issue_patch_string'))
    for issue_patch, group_itr in itertools.groupby(
        attempts, operator.attrgetter('issue_patch_string')):
      patch_attempts[issue_patch] = list(group_itr)
    patch_durations = map(compute_patch_duration, patch_attempts.values())
    if patch_durations:
      patch_mean_duration = round_timedelta(sum(
          patch_durations, timedelta()) / len(patch_durations))
      print 'Mean duration of CQ trying a patch is %s (%d min).' % (
          patch_mean_duration,
          round(patch_mean_duration.total_seconds() / 60.))

      patch_median_duration = timedelta(seconds=round(numpy.median(
          map(timedelta.total_seconds, patch_durations))))
      print 'Median duration of CQ trying a patch is %s (%d min).' % (
          patch_median_duration,
          round(patch_median_duration.total_seconds() / 60.))
    else:
      print 'No entries to compute mean duration of CQ trying a patch.'
    print


def collect_stats(args):
  # Rietveld allows up to 1000 results per search query.  I don't know if
  # that's better for the server or not.  We'll use 100 to be safe.
  per_request_search_limit = 100
  if args.count:
    per_request_search_limit = min(int(args.count/2), 100)
  # Currently looking at the last 2000 entries.
  target_count = args.count

  logging.info('Fetching and analyzing most recent issues...')
  analyzer = CQAnalyzer(args)

  total_fetch_count = 0
  issue_count = 0
  cursor = None
  url_counts = collections.Counter()

  while True:
    search_results = fetch_recent_issues(per_request_search_limit, args,
                                         cursor)
    if len(search_results['results']) == 0:
      break
    cursor = search_results['cursor']
    total_fetch_count += per_request_search_limit

    if args.base_url_stats:
      url_counts.update([result['base_url']
                        for result in search_results['results']])

    for result in search_results['results']:
      if not matches_target_base_url(result['base_url']):
        continue
      issue_count += 1
      if args.progress and (issue_count % 100 == 0):
        print issue_count,
        if target_count:
          print target_count
      issue, now = fetch_issue(result['issue'])
      if not issue:
        continue
      analyzer.process_issue(issue, now)
      if args.jobs:
        analyzer.process_try_jobs(issue)
    if target_count and issue_count >= target_count:
      break

  stats = {
    'total_fetch_count' : total_fetch_count,
    'issue_count' : issue_count,
    'url_counts' : url_counts,
    'analyzer' : analyzer }
  return stats


def compute_derived_stats(stats):
  """Computes stats derived from the raw stats."""

  analyzer = stats['analyzer']
  cq_issues = set([attempt.issue_id for attempt in analyzer.attempts])
  cq_issue_count = len(cq_issues)

  cq_patches = set([attempt.issue_patch_string
                    for attempt in analyzer.attempts])
  cq_patch_count = len(cq_patches)

  cq_no_try_issues = len(cq_issues & analyzer.no_try_issues)
  cq_gave_up_patches = len(cq_patches & analyzer.manual_commits)

  identifier_getter = operator.attrgetter('issue_patch_string')
  attempts = sorted(analyzer.attempts, key=identifier_getter)
  extra_cq_attempts = 0
  cq_retry_attempts = 0
  eventually_success_durations = []
  eventually_success_attempts = []
  eventually_success_by_count = {}
  cq_commit_count = 0

  for _, group_itr in itertools.groupby(attempts, identifier_getter):
    group = list(group_itr)
    if group[0].issue_id in analyzer.no_try_issues:
      continue
    results = map(operator.attrgetter('result'), group)
    successes = [r for r in results if r == 'SUCCESS']
    if successes:
      cq_commit_count += len(successes)
      # 'RESTART' events may not require a user re-click?
      extra_cq_attempts += (len([g for g in group if g.result != 'RESTART'])
                            - 1)
      cq_retry_attempts += len([g for g in group if g.cq_retry])
      durations = map(operator.attrgetter('duration'), group)
      eventually_success_durations.append(
          sum(durations, timedelta()).total_seconds())
      eventually_success_attempts.append(len(group))
      eventually_success_by_count.setdefault(len(group), 0)
      eventually_success_by_count[len(group)] += 1

  flaky_builders = {}
  for _, issue in analyzer.try_jobs.get('issues', {}).iteritems():
    for builder_name, builder in issue['builders'].iteritems():
      flaky_builder = flaky_builders.setdefault(builder_name, {
          'builder_name': builder_name,
          'flaky_failures' : 0,
          'succeeded': 0,
          'flaky_jobs': [],
          'flakiness': 0
      })
      if 'succeeded' in builder['results']:
        flaky_builder['succeeded'] += builder['results']['succeeded']
      if 'flaky_failures' in builder:
        flaky_builder['flaky_failures'] += builder['flaky_failures']
        flaky_builder['flaky_jobs'].extend(builder['flaky_jobs'])

  sorted_flaky_builders = []
  for flaky_builder in flaky_builders.itervalues():
    if not flaky_builder['flaky_failures']:
      continue
    if (flaky_builder['succeeded'] + flaky_builder['flaky_failures'] <
        FLAKINESS_THRESHOLD):
      continue
    flakiness = percentage(
        flaky_builder['flaky_failures'],
        flaky_builder['flaky_failures'] + flaky_builder['succeeded'])
    flakiness = round(10 * flakiness) / 10.
    flaky_builder['flakiness'] = flakiness
    sorted_flaky_builders.append(flaky_builder)

  sorted_flaky_builders = sorted(
      sorted_flaky_builders,
      key=operator.itemgetter('flakiness'), reverse=True)

  failed_patchsets = {}
  sorted_attempts = sorted(
      analyzer.attempts,
      key=operator.attrgetter('issue_patch_string'))
  for issue_patch, group_itr in itertools.groupby(
      sorted_attempts, operator.attrgetter('issue_patch_string')):
    attempts = list(group_itr)
    if filter(lambda a: a.result == 'SUCCESS', attempts):
      continue
    results = set(map(lambda a: a.result, attempts))
    failed_try_jobs = []
    try_jobs = analyzer.try_jobs.get('by_patchset', {}).get(issue_patch, {})
    for builder_name, builder in try_jobs.iteritems():
      if builder.get('succeeded'):
        continue
      failed_try_jobs.append(builder_name)
    failed_patchsets[issue_patch] = {
        'status': list(results),
        'failed_try_jobs': failed_try_jobs
    }

  # List patchsets rejected by each builder
  rejecting_builders = {}
  for issue_patch, value in failed_patchsets.iteritems():
    for builder in value['failed_try_jobs']:
      rejecting_builders.setdefault(builder, [])
      rejecting_builders[builder].append(issue_patch)

  stats['cq_issue_count'] = cq_issue_count
  stats['cq_patch_count'] = cq_patch_count
  stats['cq_no_try_issues'] = cq_no_try_issues
  stats['cq_commit_count'] = cq_commit_count
  stats['cq_gave_up_patches'] = cq_gave_up_patches
  stats['extra_cq_attempts'] = extra_cq_attempts
  stats['cq_retry_attempts'] = cq_retry_attempts
  stats['eventually_success_durations'] = eventually_success_durations
  stats['eventually_success_attempts'] = eventually_success_attempts
  stats['eventually_success_by_count'] = eventually_success_by_count
  stats['sorted_flaky_builders'] = sorted_flaky_builders
  stats['failed_patchsets'] = failed_patchsets
  stats['rejecting_builders'] = rejecting_builders


def print_flaky_jobs_stats(args, stats):
  """Print stats on flaky builders."""
  if not args.top_flakes:
    return
  if not stats['sorted_flaky_builders']:
    print '\nNo flaky builders were found.\n'
    return

  print '\nTop flaky builders (which fail and succeed in the same patchset):'
  col_aligns = (str.ljust, str.ljust, str.ljust, str.ljust)
  col_widths = (40, 15, 15, 15)
  col_headers = ('Builder Name', 'Succeeded', 'Flaky Failures', 'Flakiness (%)')
  print format_line(col_headers, col_aligns, col_widths)
  print '-' * (sum(col_widths) + len(col_widths) - 1)
  for flaky_builder in stats['sorted_flaky_builders'][:args.top_flakes]:
    columns = (flaky_builder['builder_name'],
               flaky_builder['succeeded'],
               flaky_builder['flaky_failures'],
               flaky_builder['flakiness'])
    print format_line(columns, col_aligns, col_widths)
  print

  if args.list_flaky_jobs:
    print 'Flaky builds:'
    for flaky_builder in stats['sorted_flaky_builders'][:args.top_flakes]:
      for url in flaky_builder['flaky_jobs']:
        print '  ' + url
    print


def print_jobs_stats(args, stats):
  analyzer = stats['analyzer']
  jobs = analyzer.try_jobs['total']
  cq_jobs = analyzer.try_jobs['commit-bot']
  unknown_jobs = analyzer.try_jobs['unknown']
  print ''
  print 'Total try jobs: %d, by CQ: %d (%2.1f%%), unknown: %d (%2.1f%%)' % (
      jobs, cq_jobs, percentage(cq_jobs, jobs),
      unknown_jobs, percentage(unknown_jobs, jobs))

  print_flaky_jobs_stats(args, stats)

  print 'Redundant successful jobs: %d (%.1f%%)' % (
      analyzer.try_jobs['redundant'],
      percentage(analyzer.try_jobs['redundant'], jobs))
  print 'Repeated failed jobs: %d (%2.1f%%)' % (
      analyzer.try_jobs['repeated_failures'],
      percentage(analyzer.try_jobs['repeated_failures'], jobs))
  print 'Pending jobs: %d (%2.1f%%)' % (
      analyzer.try_jobs['pending'],
      percentage(analyzer.try_jobs['pending'], jobs))

  # Figure out builds with the most failing / redundant jobs:
  stats_by_builder = {}
  for _, issue_stats in analyzer.try_jobs['issues'].iteritems():
    for builder_name, builder in issue_stats['builders'].iteritems():
      builder_stats = stats_by_builder.setdefault(
          builder_name, { 'results' : {},
                          'commit-bot' : 0,
                          'unknown' : 0,
                          'redundant' : 0,
                          'repeated_failures' : 0 })

      for result_str, count in builder['results'].iteritems():
        builder_stats['results'].setdefault(result_str, 0)
        builder_stats['results'][result_str] += count

      builder_stats['commit-bot'] += builder['commit-bot']
      builder_stats['unknown'] += builder['unknown']
      builder_results = builder['results']

      if builder_results.get('succeeded', 0):
        builder_stats['redundant'] += builder_results['succeeded'] - 1
      if builder_results.get('failed', 0):
        builder_stats['repeated_failures'] += builder_results['failed'] - 1

  if stats_by_builder and args.top_jobs:
    print '\nBuilders with the highest redundancy / repeated failure rate:'

    def sort_key(builder_name):
      builder = stats_by_builder[builder_name]
      return builder['redundant'] + builder['repeated_failures']

    count = args.top_jobs
    for builder_name in sorted(stats_by_builder, key=sort_key, reverse=True):
      count -= 1
      if count < 0:
        break
      builder_stats = stats_by_builder[builder_name]
      print '%s has %d redundant successful runs and %d repeated failures:' % (
        builder_name, builder_stats['redundant'],
        builder_stats['repeated_failures'])
      print '  %r' % builder_stats

  count = args.top_jobs
  if jobs and count:
    print '\nIssues with the highest number of try jobs:'
    # Print top N CLs with the highest number of jobs
    for issue_id in sorted(
        analyzer.try_jobs['issues'],
        key=lambda i: analyzer.try_jobs['issues'][i]['total'], reverse=True):
      count -= 1
      if count < 0:
        break
      jobs = analyzer.try_jobs['issues'][issue_id]
      print 'Issue %s has %d jobs:' % (issue_id, jobs['total'])
      for builder, results in jobs.iteritems():
        if builder == 'total':
          continue
        print '  %s: %r' % (builder, results)


def get_builder_runtime(builder, default_runtime=36000):
  runtimes = {
    'chromium_presubmit': 132.6,
    'blink_presubmit': 158.7,
    'ios_rel_device_ninja': 343.3,
    'android_chromium_gn_compile_rel': 357.1,
    'linux_chromium_gn_rel': 412.4,
    'ios_rel_device': 497.1,
    'android_clang_dbg': 1059.3,
    'linux_chromium_clang_dbg': 1123.8,
    'mac_chromium_compile_dbg': 1220.2,
    'linux_chromium_chromeos_clang_dbg': 1225.5,
    'ios_dbg_simulator': 1272.9,
    'android_dbg': 1287.9,
    'win8_aura': 1926.1,
    'win_chromium_compile_dbg': 2047.6,
    'win8_chromium_rel': 2214.3,
    'linux_chromium_rel_swarming': 2306.1,
    'android_aosp': 2782.8,
    'linux_chromium_rel': 3671,
    'mac_chromium_rel_swarming': 3847.6,
    'linux_chromium_chromeos_rel': 4035,
    'win_chromium_x64_rel': 6412.3,
    'win_chromium_rel_swarming': 6471.7,
    'mac_chromium_rel': 7022.4,
    'win_chromium_rel': 8261.9,
    'mac_gpu': 955.2,
    'linux_gpu': 1235.7,
    'win_gpu': 1835.1,
    # Triggered bots include the triggering bot runtime.
    'android_dbg_triggered_tests': 3200.8 + 1287.9,
    'mac_gpu_triggered_tests': 790.2 + 955.2,
    'mac_gpu_retina_triggered_tests': 613.9 + 955.2,
    'linux_gpu_triggered_tests': 718.2 + 1235.7,
    'win_gpu_triggered_tests': 1279.1 + 1835.1,
  }
  return runtimes.get(builder, default_runtime)


def print_attempts_rate(stats):
  analyzer = stats['analyzer']

  def get_hour(attempt):
    return attempt.start_time.strftime('%Y-%m-%d:%H')

  sorted_attempts = sorted(analyzer.attempts, key=get_hour)
  hourly = [(h, len(list(g))) for h, g in itertools.groupby(
      sorted_attempts, get_hour)]
  hourly = sorted(hourly, key=lambda x: x[0])

  print 'Timestamp, Number of CQ attempts'
  for hour, num_attempts in hourly:
    print '%s,%d' % (hour, num_attempts)


def print_stats(args, stats):

  analyzer = stats['analyzer']

  # This prints an CSV format for ingesting into spreadsheet for
  # graphing.  Keep it the only output to be printed, if requested.
  if args.list_attempts_rate:
    print_attempts_rate(stats)
    return

  if args.base_url_stats:
    print
    for url, count in stats.url_counts.most_common():
      matches_target = matches_target_base_url(url)
      print '%s %s %s' % (matches_target, count, url)

  print
  print 'Found %s issues (in the %s most recent issues).' % (
      stats['issue_count'], stats['total_fetch_count'])
  print ('%4d issues (%2.1f%%, %d patchsets) were tried the CQ, '
         'resulting in') % (
      stats['cq_issue_count'],
      percentage(stats['cq_issue_count'], stats['issue_count']),
      stats['cq_patch_count'])
  print ('%4d CQ attempts, %d (%2.1f%%) of which are auto-retries.') % (
      len(analyzer.attempts), stats['cq_retry_attempts'],
      percentage(stats['cq_retry_attempts'], len(analyzer.attempts)))
  print '%4d patches (%2.1f%% of tried patchsets) were committed by CQ,' % (
      stats['cq_commit_count'],
      percentage(stats['cq_commit_count'], stats['cq_patch_count']))
  print('%4d patches (%2.1f%% of tried patchsets) '
        'were committed manually (gave up).') % (
      stats['cq_gave_up_patches'],
      percentage(stats['cq_gave_up_patches'], stats['cq_patch_count']))
  print '%4d issues (%2.1f%% of tried issues) were marked NOTRY.' % (
      stats['cq_no_try_issues'],
      percentage(stats['cq_no_try_issues'], stats['cq_issue_count']))

  print
  analyzer.print_mean_cq_duration()

  print ('%d CQ starts (%2.1f%% of %d CQ attempts) were due to a '
         'previous false-negative') % (
      stats['extra_cq_attempts'],
      percentage(stats['extra_cq_attempts'], len(analyzer.attempts)),
      len(analyzer.attempts))
  manual_attempts = (stats['extra_cq_attempts'] -
                     stats['cq_retry_attempts'])
  print ('  (CQ landed a patch it previously rejected), %d of which '
         '(%2.1f%% of %d CQ attempts) were manual retry:') % (
      manual_attempts,
      percentage(manual_attempts, len(analyzer.attempts)),
      len(analyzer.attempts))

  success_count = stats['eventually_success_by_count']
  if success_count:
    sorted_keys = sorted(success_count)
    for k in sorted_keys:
      print '%4d patchsets (%2.1f%%) committed in %2d CQ attempts' % (
          success_count[k],
          percentage(success_count[k], stats['cq_commit_count']), k)

    if stats['eventually_success_durations']:
      print
      print 'Patches which eventually land percentiles:'
      for i in [10, 25, 50, 75, 90, 95, 99]:
        eventually_success_durations_p = round(numpy.percentile(
            stats['eventually_success_durations'], i)/(60*60), 3)
        eventually_success_attempts_p = numpy.percentile(
            stats['eventually_success_attempts'], i)
        print '  %2d: %4.1f hrs, %2d attempts' % (
            i, eventually_success_durations_p,
            round(eventually_success_attempts_p))

  analyzer.print_attempts_table()

  if args.jobs:
    print_jobs_stats(args, stats)

  if args.top_rejecting_jobs or args.rejecting_jobs:
    jobs = stats['rejecting_builders'].items()
    top_jobs = []
    if args.rejecting_jobs:
      for job_name in args.rejecting_jobs:
        value = stats['rejecting_builders'].get(job_name)
        if value:
          top_jobs.append((job_name, value))
      num_jobs = len(top_jobs)
    else:
#    top_jobs = sorted(jobs, key=lambda j: len(j[1]), reverse=True)
      top_jobs = sorted(jobs, key=lambda j: get_builder_runtime(j[0]))
      num_jobs = min(len(top_jobs), args.top_rejecting_jobs)
    num_failed_patchsets = len(stats['failed_patchsets'])
    covered_patches = set()
    for job in top_jobs[:num_jobs]:
      covered_patches.update(job[1])
    num_rejected_patchsets = len(covered_patches)
    covered_patches = set()
    print
    print 'Top %d bots that rejected %d CLs (%2.1f%% of %d failed CLs):' % (
        num_jobs, num_rejected_patchsets,
        percentage(num_rejected_patchsets, num_failed_patchsets),
        num_failed_patchsets)
    for job in top_jobs[:num_jobs]:
      diff = set(job[1]) - covered_patches
      covered_patches.update(job[1])
      print('%6d (%3d @ %2.1f%% new, %6d @ %2.1f%% total) %s, '
            'runtime: %5d sec' % (
          len(job[1]), len(diff),
          percentage(len(diff), num_rejected_patchsets),
          len(covered_patches),
          percentage(len(covered_patches), num_rejected_patchsets),
          job[0], get_builder_runtime(job[0], default_runtime=-1)))
      if args.list_rejected:
        for patch in diff:
          print '     ' + issue_patch_display_url(patch)

    uncovered_patches = set(stats['failed_patchsets']) - covered_patches
    if args.list_rejected and uncovered_patches:
      print
      print '  Patchsets rejected for other reasons: %d of %d (%2.1f%%)' % (
        len(uncovered_patches), num_failed_patchsets,
        percentage(len(uncovered_patches), num_failed_patchsets))
      for patch in uncovered_patches:
        print '    ' + issue_patch_display_url(patch)

  elif args.list_rejected:
    failed = []
    for issue_patch, results in stats['failed_patchsets'].iteritems():
      url = issue_patch_display_url(issue_patch)
      failed.append('%s: status: %s, failed jobs: %s' % (
          url, ', '.join(results['status']),
          ', '.join(results['failed_try_jobs'])))
    print
    print 'Failed CLs (%d):' % len(failed)
    print '  ' + '\n  '.join(failed)


def export_stats_as_json(args, stats):
  """Exports stats in a json format to a file."""

  stats_json = {
      'attempts': [attempt.__dict__ for attempt in stats['analyzer'].attempts]
  }

  if args.jobs:
    stats_json['try_jobs'] = stats['analyzer'].try_jobs

  date_handler = lambda obj: (obj.isoformat() if isinstance(obj, datetime)
                              else None)
  json.dump(stats_json, open(args.json, 'w'), default=date_handler)


def parse_options():
  parser = argparse.ArgumentParser()
  parser.add_argument('--base-url-stats', action='store_true',
                      help='print base_url matching stats')
  project_choices = projects_utils.GetSupportedProjects()
  parser.add_argument(
      '--project',
      choices=project_choices,
      required=True,
      help='Collect stats about this project.')
  parser.add_argument('--verbose', action='store_true')
  parser.add_argument('--quiet', action='store_true')
  parser.add_argument('--jobs', action='store_true',
                      dest='jobs',
                      default=True,
                      help='collect stats on try jobs')
  parser.add_argument('--no-jobs', action='store_false',
                      dest='jobs',
                      default=True,
                      help='Do not collect stats on try jobs')
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
  parser.add_argument('--clear', action='store_true',
                      help='clear the cache before starting')
  parser.add_argument('--count', type=int, default=None,
                      help='number of issues to fetch')
  parser.add_argument('--modified-after', default=None,
                      dest='modified_after',
                      help=('search for issues modified after '
                            'this date YYYY-MM-DD'))
  parser.add_argument('--modified-before', default=None,
                      dest='modified_before',
                      help=('search for issues modified before '
                            'this date YYYY-MM-DD'))
  parser.add_argument('--progress', help='Show progress', action='store_true')
  parser.add_argument('--json', default=None,
                      help='Exports JSON stats into a file')
  parser.add_argument('--owner', default=None,
                      help=('search for issues of specified owner'))
  parser.add_argument('--list-attempts-rate',
                      dest='list_attempts_rate',
                      action='store_true',
                      help='List number of CQ attempts by hour in CSV.')
  args = parser.parse_args()
  if args.rejecting_jobs:
    args.rejecting_jobs = args.rejecting_jobs.split(',')

  # Make sure the dates are given in the correct format.
  def to_datetime(date_str, opt_name):
    result = None
    if date_str:
      try:
        result = datetime.strptime(date_str, '%Y-%m-%d')
      except ValueError:
        print ('ERROR: Incorrect date format in %s %s. '
               'Please use YYYY-MM-DD.' % (opt_name, date_str))
        result = 'ERROR'
    return result

  args.from_date = to_datetime(args.modified_after, '--modified-after')
  args.to_date = to_datetime(args.modified_before, '--modified-before')
  if 'ERROR' in [args.from_date, args.to_date]:
    args = None

  return args


def main():
  args = parse_options()
  if not args:
    sys.exit(1)
  system_utils.setup_logging('commit_queue_stats', args)
  setup_config(args)

  if args.clear:
    logging.info('Clearing cache...')
    session.cache.clear()

  print 'Collecting stats on project %s' % args.project
  stats = collect_stats(args)
  compute_derived_stats(stats)
  print_stats(args, stats)

  if args.json:
    export_stats_as_json(args, stats)

if __name__ == '__main__':
  sys.exit(main())
