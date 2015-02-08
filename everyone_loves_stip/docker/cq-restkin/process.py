# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
from contextlib import closing
from contextlib import contextmanager
from datetime import datetime
from datetime import timedelta
import functools
import hashlib
from itertools import chain
from itertools import groupby
import json
import multiprocessing
import requests
from requests.adapters import HTTPAdapter
import sys


@contextmanager
def MultiPool(processes):
  """Manages a multiprocessing.Pool making sure to close the pool when done.
  This will also call pool.terminate() when an exception is raised (and
  re-raised the exception to the calling procedure can handle it).
  """
  try:
    pool = multiprocessing.Pool(processes=processes)
    yield pool
    pool.close()
  except:
    pool.terminate()
    raise
  finally:
    pool.join()


@functools.total_ordering
class CQApiRecord(object):
  def __init__(self, timestamp=None, tags=None, key=None, fields=None):
    self.timestamp = timestamp
    self._tags = tags
    self._key = key
    self._fields = fields

    self.project = None
    self.issue = None
    self.patchset = None
    self.attempt = None

  def set_identifiers(self, project, issue, patchset, attempt):
    self.project = project
    self.issue = issue
    self.patchset = patchset
    self.attempt = attempt

  def __eq__(self, other):
    return self.timestamp == other.timestamp and self._tags == other._tags

  def __lt__(self, other):
    return self.timestamp < other.timestamp


def builder_id(master, builder):
  return '%s/%s' % (master, builder)


class JobUpdate(object):
  def __init__(self, timestamp, job_dict, rietveld_timestamp):
    self.timestamp = timestamp
    self.job_dict = job_dict
    self.rietveld_timestamp = rietveld_timestamp

  def __eq__(self, other):
    return self.job_dict == other.job_dict

  def __hash__(self):
    return hash(json.dumps(self.job_dict, sort_keys=True))

  def __str__(self):
    return str(self.job_dict)

  def __repr__(self):
    return 'JobUpdate: %s' % repr(self.job_dict)

  def zipkin_data(self):
    # self.rietveld_timestamp, useless?
    return {
        'ss': self.timestamp,
        'cr': self.timestamp,
        'host': self.job_dict['slave'],
        'service_name': builder_id(
            self.job_dict['master'], self.job_dict['builder']),
        }


class VerifierJobsUpdate(CQApiRecord):
  def __init__(self, *args, **kwargs):
    super(VerifierJobsUpdate, self).__init__(*args, **kwargs)

    self.job_updates = set()
    for master in self._fields['jobs'].itervalues():
      for builder in master.itervalues():
        for job in builder['rietveld_results']:
          if job['result'] != -1 and job['buildnumber'] is not None:
            self.job_updates.add(JobUpdate(
                self.timestamp,
                job,
                datetime.strptime(
                    builder['timestamp'], "%Y-%m-%d %H:%M:%S.%f")))


class VerifierStart(CQApiRecord):
  def __init__(self, *args, **kwargs):
    super(VerifierStart, self).__init__(*args, **kwargs)
    self.tryjobs = set()
    for mastername, master_builders in self._fields['tryjobs'].iteritems():
      for builder in master_builders.keys():
        self.tryjobs.add(builder_id(mastername, builder))


class VerifierRetry(CQApiRecord):
  pass


class PatchCommitting(CQApiRecord):
  pass


class PatchCommitted(CQApiRecord):
  pass


class PatchThrottled(CQApiRecord):
  pass


class PatchTreeClosed(CQApiRecord):
  pass


def return_new_jobs(jobs_updates):
  total_jobs = set()
  for update in jobs_updates:
    if isinstance(update, VerifierJobsUpdate):
      diff = update.job_updates - total_jobs
      if diff:
        total_jobs |= diff
        update.job_updates = diff
        yield update
    else:
      yield update


def chunk_attempts(records):
  current_chunk = None
  for record in records:
    if record['fields']['action'] == 'patch_start':
      current_chunk = [record]
    elif record['fields']['action'] == 'patch_stop':
      if current_chunk is not None:
        current_chunk.append(record)
        yield current_chunk
        current_chunk = None
    elif current_chunk is not None:
      current_chunk.append(record)


def translate_retry_to_start(records):
  last_update = None
  for record in records:
    if isinstance(record, VerifierRetry):
      assert last_update is not None
      bad_jobs = {}
      for mastername, master in last_update._fields['jobs'].iteritems():
        for buildername, builder in master.iteritems():
          for job in builder['rietveld_results']:
            if job['result'] != 0:
              bad_jobs.setdefault(mastername, {})[buildername] = {}
      yield VerifierStart(
          timestamp=datetime_to_timestamp(record.timestamp),
          tags=record._tags,
          key=record._key,
          fields={'tryjobs': bad_jobs})
    elif isinstance(record, VerifierJobsUpdate):
      last_update = record
      yield record
    else:
      yield record


def link_jobs_to_trigger(records):
  triggers = {}
  for record in records:
    if isinstance(record, VerifierStart):
      for trigger in record.tryjobs:
        triggers[trigger] = record.timestamp
    elif isinstance(record, VerifierJobsUpdate):
      for job_update in record.job_updates:
        zk_data = job_update.zipkin_data()
        zk_data['cs'] = triggers[
            builder_id(job_update.job_dict['master'],
                       job_update.job_dict['builder'])]
        zk_data['sr'] = triggers[
            builder_id(job_update.job_dict['master'],
                       job_update.job_dict['builder'])]
        yield zk_data
    else:
      yield record


def process_commit_record_types(records):
  last_patch_record = None
  for record in records:
    if record.__class__ in COMMIT_RECORD_TYPES:
      if last_patch_record is not None:
        service = None
        if isinstance(last_patch_record, PatchCommitting):
          service = 'commit'
        elif isinstance(last_patch_record, PatchThrottled):
          service = 'patch_throttled'
        elif isinstance(last_patch_record, PatchTreeClosed):
          service = 'tree_closed'
        if service:
          yield {
              'cs': last_patch_record.timestamp,
              'sr': last_patch_record.timestamp,
              'ss': record.timestamp,
              'cr': record.timestamp,
              'service_name': service,
          }
      last_patch_record = record
    else:
      yield record

class PatchStart(CQApiRecord):
  pass


class PatchStop(CQApiRecord):
  pass



RECORD_TYPES = {
    'patch_start': PatchStart,
    'patch_stop': PatchStop,
}


COMMIT_RECORD_TYPES = set([
    PatchCommitted,
    PatchCommitting,
    PatchTreeClosed,
    PatchThrottled,
])


def constructor(record):
  return RECORD_TYPES.get(
      record['fields'].get('action'), lambda **kwargs: None)(**record)


def datetime_to_timestamp(dt):
  return (dt - datetime(1970, 1, 1)).total_seconds()


class ZipkinSpan(object):
  def __init__(
      self, name, trace_id, span_id, parent_id, parent_name, annotations):
    self.name = name
    self.trace_id = trace_id
    self.span_id = span_id
    self.parent_id = parent_id
    self.annotations = []

    for annot_name, annot_value in annotations.iteritems():
      if annot_name in ('cs', 'cr'):
        self.annotations.append({
            'key': annot_name,
            'type': 'timestamp',
            'value': int(datetime_to_timestamp(annot_value) * 1000000),
            'name': parent_name,
            'host': {
                'ipv4': '10.10.10.10',
                'port': 1234,
                'service_name': parent_name,
            }
        })
        # timestamps are integers in microseconds
      elif annot_name in ('ss', 'sr'):
        self.annotations.append({
            'key': annot_name,
            'type': 'timestamp',
            'value': int(datetime_to_timestamp(annot_value) * 1000000),
            'name': self.name,
            'host': {
                'ipv4': '10.10.10.10',
                'port': 1234,
                'service_name': self.name,
            }
        })
      elif annot_name in ('patchset', 'issue', 'attempt', 'url', 'cq_url'):
        self.annotations.append({
            'key': annot_name,
            'type': 'string',
            'value': str(annot_value),
        })

  def render(self):
    result = {
        'trace_id': self.trace_id,
        'span_id': self.span_id,
        'name': self.name,
        'annotations': self.annotations,
    }

    if self.parent_id:
      result['parent_span_id'] = self.parent_id

    return result


def gen_unique_hash(issue, patchset, attempt):
  h = hashlib.new('sha1')
  h.update('%s-%s-%s' % (issue, patchset, attempt))
  return h.hexdigest()[0:15]


def hash_dict(d):
  class DateEncoder(json.JSONEncoder):
    # pylint: disable=E0202
    def default(self, obj):
      if isinstance(obj, datetime):
        return obj.isoformat()
      return json.JSONEncoder.default(self, obj)
  h = hashlib.new('sha1')
  h.update(json.dumps(d, cls=DateEncoder, sort_keys=True))
  return h.hexdigest()[0:15]


def construct_spans(records, issue, patchset, attempt):
  records = list(records)
  return [records[0].timestamp, records[-1].timestamp - records[0].timestamp]


def send_to_restkin(url, spans):
  headers = {'content-type': 'application/json'}
  r = requests.post(url, data=json.dumps(spans), headers=headers)
  print r


def get_action(project, action, count, begin, end):
  s = requests.Session()
  s.mount('https://chromium-cq-status.appspot.com',
      HTTPAdapter(max_retries=5))
  cursor = None
  cont = True
  items = []
  while cont:
    query_url = (
        'https://chromium-cq-status.appspot.com/query/project=%s/'
        'action=%s?count=%d&begin=%f&end=%f' % (
          project, action, count, begin, end))
    if cursor:
      query_url += '&cursor=%s' % cursor

    query = requests.get(query_url).json()
    items.extend(query['results'])
    cont = query['more']
    cursor = query['cursor']
    print 'Received %d items (action: %s, more: %s)' % (
        len(query['results']), action, cont)
  return items


def days_past(current_date, days):
  return ((current_date - timedelta(days=days)) -
      datetime.utcfromtimestamp(0)).total_seconds()


def get_events(spec):
  events = []
  events.extend(get_action(
      spec[3], 'patch_start', spec[2], spec[0], spec[1]))
  events.extend(get_action(
      spec[3], 'patch_stop', spec[2], spec[0], spec[1]))
  if spec[4]:
    events.extend(get_action(
      spec[3], spec[4], spec[2], spec[0], spec[1]))
  return events


def process_patchset(item):
  issue = item['fields']['issue']
  patchset = item['fields']['patchset']
  print 'processing patchset: %s/%s' % (issue, patchset)
  start = datetime.utcnow()
  url_template = ('https://chromium-cq-status.appspot.com/'
                  'query/issue=%d/patchset=%d')

  url = url_template % (issue, patchset)

  items = requests.get(url).json()

  sorted_records = sorted(filter(bool, map(constructor, items['results'])))
  spans = []
  for attempt, record_set in enumerate((chunk_attempts(sorted_records))):
    spans.append(construct_spans(
        process_commit_record_types(
          record_set),
        issue,
        patchset,
        attempt))
  done = datetime.utcnow()
  print '%s/%s took %.2fs' % (
    issue,
    patchset,
    (done - start).total_seconds())
  return spans


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('issue', type=int, nargs='?', help='rietveld issue')
  parser.add_argument(
      'patchset', type=int, nargs='?', help='patchset', default=1)
  parser.add_argument('--count',
                      default=1000,
                      type=int,
                      help='number of patch_stop events to process at a time')
  parser.add_argument('--days',
                      default=30,
                      type=int,
                      help='number of days to go back for data')
  parser.add_argument('--processes',
                      default=8,
                      type=int,
                      help='number of threads to issue queries')
  parser.add_argument('--project',
                      default='chromium',
                      help='project to get data for')
  parser.add_argument('--action',
                      help='which action to time')
  parser.add_argument('--inverse',
                      action='store_true',
                      help='time this action to stop, instead of this to start')
  parser.add_argument('--output',
                      default='real_results.json',
                      help='where to output')
  args = parser.parse_args()

  spans = []
  if args.issue:
    spans.append(process_patchset(args.issue, args.patchset, args.restkin_url))
  else:
    querynow = datetime.utcnow()
    print 'UTC time is %s' % querynow.isoformat()

    events = []
    event_specs = [[
      int(days_past(querynow, i+1)),
      int(days_past(querynow, i)),
      args.count,
      args.project,
      args.action] for i in range(args.days)]
    with MultiPool(args.processes) as pool:
      events.extend(chain.from_iterable(
        pool.map_async(get_events, event_specs).get(9999999)))

    all_events = sorted(events, key=lambda x: x['fields']['issue'])

    attempts = []
    for _, group in groupby(all_events, lambda x: x['fields']['issue']):
      def patchset_keyfunc(item):
        patchset_tag = next(x for x in item['tags'] if x.startswith('patchset'))
        return int(patchset_tag.split('=')[1])
      patchset_sorted = sorted(group, key=patchset_keyfunc)
      for _, group in groupby(patchset_sorted, patchset_keyfunc):
        sorted_patchset = sorted(group, key=lambda x: x['timestamp'])
        for chunk in chunk_attempts(sorted_patchset):
          chunk = list(chunk)
          termination_action = 'patch_stop'
          if args.action:
            termination_action = args.action

          try:
            action = next(
                x for x in chunk if x['fields']['action'] == termination_action)
          except StopIteration:
            continue

          action_time = action['timestamp'] - chunk[0]['timestamp']

          if args.inverse:
            total_time = chunk[-1]['timestamp'] - chunk[0]['timestamp']
            action_time = total_time - action_time

          attempts.append([chunk[0]['timestamp'], action_time])
    spans.append(sorted(attempts, key=lambda x: x[0]))
    earliest = datetime.utcfromtimestamp(spans[0][0][0])
    days_progress = (querynow - earliest).total_seconds() / (24.0 * 3600.0)
    runtime = (datetime.utcnow() - querynow).total_seconds()
    print (
        'Retrieved %d issues, earliest is %s (%.2f days). %.2fs elapsed, '
        '%.2fd/min' % (
          len(attempts),
          earliest.isoformat(),
          days_progress,
          runtime,
          60.0 * days_progress / runtime,
        )
    )

  with open(args.output, 'w') as f:
    json.dump(spans, f, indent=2)
  print 'wrote %d records' % len(spans[0])
  return 0


if __name__ == '__main__':
  sys.exit(main())
