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


def events(path, chunk_count=100):
  cursor = None
  with requests.Session() as s:
    res = {'more': True}
    while res.get('more'):
      params = {'count': chunk_count}
      if cursor:
        params['cursor'] = cursor
      query = url_constructor('https', CHROMIUM_CQ_STATUS_HOST, path, params)
      logging.debug('querying %s', query)
      res = s.get(query).json()
      if res.get('cursor'):
        cursor = res['cursor']
      logging.debug('got %d responses', len(res['results']))
      for result in res['results']:
        yield result


def get_action_count(project, action, count):
  return itertools.islice(
    events('query/project=%s/action=%s' % (project, action)), count)

def get_action_issue_patchset(action, issue, patchset):
    return events('query/issue=%s/patchset=%s/action=%s' % (
      issue, patchset, action))

def get_action_i_p_a(action, issue, patchset, attempt):
  events = get_action_issue_patchset(action, issue, patchset)
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

project = 'chromium'
master = 'tryserver.chromium.linux'
builder = 'linux_android_rel_ng'
count = 1000
    
args = [(project, 'verifier_pass', count),
        (project, 'verifier_fail', count)]

dataz = itertools.chain.from_iterable(itertools.starmap(
  get_action_count, args))

issue_patchset_attempts = collections.defaultdict(
    lambda: collections.defaultdict(
      lambda: collections.defaultdict(
        lambda: [])))

for data in dataz:
  issue = data['fields']['issue']
  patchset = data['fields']['patchset']
  attempt = data['fields']['attempt_start_ts']
  issue_patchset_attempts[issue][patchset][attempt].append(data)

run_data = []

for issue, patchsets in issue_patchset_attempts.iteritems():
  for patchset, attempts in patchsets.iteritems():
    for attempt, data in attempts.iteritems():
      action = 'verifier_jobs_update'
      tryjob_updates = list(get_action_i_p_a(action, issue, patchset, attempt))
      run_data.append((issue, patchset, attempt, convert_to_tryjob_endings(tryjob_updates)))

points = []
for issue, patchset, attempt_ts, run in run_data:
  if builder not in run[master]:
    continue

  mx = -1
  second_mx = -1
  for builders in run.itervalues():
    for end in builders.itervalues():
      if end > mx:
        mx = end
      elif end > second_mx:
        second_mx = end

  if second_mx == -1:
    continue

  # append time of day
  if mx == run[master][builder]:
    points.append((issue, patchset, attempt_ts, mx - second_mx))
  else:
    points.append((issue, patchset, attempt_ts, 0))

with open('cool.json', 'w') as f:
  json.dump(points, f)
