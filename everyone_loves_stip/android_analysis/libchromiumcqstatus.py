import collections
import itertools
import json
import logging
import requests
import urllib
import urlparse

CHROMIUM_CQ_STATUS_HOST = 'chromium-cq-status.appspot.com'


def url_constructor(scheme, host, path, params):
  query = urllib.urlencode(params)
  return urlparse.urlunsplit([scheme, host, path, query, None])


def events(path, session, chunk_count=20, extra_params=None):
  """Creates a generator that will get all messages for a query."""
  cursor = None
  res = {'more': True}
  while res.get('more'):
    params = {'count': chunk_count}
    if extra_params:
      params.update(extra_params)
    if cursor:
      params['cursor'] = cursor
    query = url_constructor('https', CHROMIUM_CQ_STATUS_HOST, path, params)
    logging.debug('querying %s', query)
    res = session.get(query).json()
    if res.get('cursor'):
      cursor = res['cursor']
    logging.debug('got %d responses', len(res['results']))
    for result in res['results']:
      yield result


def get_action_time_range(project, action, start_ts, end_ts, session):
  path = 'query/project=%s/action=%s' % (project, action)
  return events(path, session, extra_params={'begin': start_ts, 'end': end_ts})

def get_action_count(project, action, count, session):
  return itertools.islice(
    events('query/project=%s/action=%s' % (project, action), session), count)

def get_action_issue_patchset(action, issue, patchset, session):
    return events('query/issue=%s/patchset=%s/action=%s' % (
      issue, patchset, action), session)

def get_action_i_p_a(action, issue, patchset, attempt, session):
  events = get_action_issue_patchset(action, issue, patchset, session)
  return itertools.ifilter(
      lambda x: x['fields']['attempt_start_ts'] == attempt, events)

def convert_to_tryjob_endings(updates):
  finish_times = collections.defaultdict(
      lambda: collections.defaultdict(
        lambda: {}))
  for update in sorted(updates, key=lambda x: x['timestamp']):
    jobs = update['fields']['jobs']
    for job in itertools.chain(
        jobs.get('JOB_SUCCEEDED', []),
        jobs.get('JOB_FAILED', [])):
      finish_times[job['master']][job['builder']].setdefault(
          job['buildnumber'], update['timestamp'])

  filtered_finish_times = collections.defaultdict(lambda: {})
  for master, builders in finish_times.iteritems():
    for builder, builds in builders.iteritems():
      filtered_finish_times[master][builder] = max(builds.itervalues())
  return filtered_finish_times
