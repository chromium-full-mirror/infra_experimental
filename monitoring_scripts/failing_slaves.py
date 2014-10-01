#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Collect stats about failing slaves."""

import argparse
import json
import logging
from multiprocessing.pool import ThreadPool
import sys
import urllib2


CHROME_BUILD_EXTRACT_BASE_URL = 'http://chrome-build-extract.appspot.com'

# Expects % (master, slave)
SLAVE_URL = 'http://build.chromium.org/p/%s/buildslaves/%s'


def get_options():
  parser = argparse.ArgumentParser(__doc__)
  parser.add_argument("--count", default=20, type=int,
                      help='Number of builds per slave to retrieve.')
  parser.add_argument("--top", default=20, type=int,
                      help='Number of top failing slaves to print.')
  parser.add_argument('-v', '--verbose', default=False, action='store_true',
                      help='Enables debugging log messages.')
  parser.add_argument('--masters',
                      help='Comma-separated list of masters to scan for '
                           'builds. If not specified, the list is retrieved '
                           'from server.')
  parser.add_argument('--builders',
                      help='Comma-separated list of builders to scan for '
                           'builds. If not specified, list of builders is '
                           'retrieved from server.')
  return parser.parse_args()


def process_slave(count):
  def func(slave_name):
    builds = []
    cursor = None
    num_builds = min(20, count)
    page = 0
    while len(builds) < count:
      slave_url = '%s/get_builds?slave=%s&num_builds=%d&json=1' % (
          CHROME_BUILD_EXTRACT_BASE_URL, slave_name, num_builds)
      if cursor:
        slave_url += '&cursor=%s' % cursor
      page += 1
      logging.debug('Fetching page %d of builds for %s: %s',
                    page, slave_name, slave_url)
      build_data = json.loads(urllib2.urlopen(slave_url).read())
      cursor = build_data['cursor']
      builds.extend(build_data['builds'])
    return (slave_name, builds)
  return func


def fetch_json(url):
  try:
    return json.loads(urllib2.urlopen(url).read())
  except Exception as e:
    logging.error('Failed to fetch JSON from %s: %s', url, e)
    return {'error': '404'}


def main():
  options = get_options()
  logging.basicConfig(level=logging.DEBUG if options.verbose else logging.WARN)

  if options.masters:
    master_names = options.masters.split(',')
  else:
    masters_url = '%s/get_masters?json=1' % CHROME_BUILD_EXTRACT_BASE_URL
    master_names = fetch_json(masters_url).get('masters',[])
  if not master_names:
    print 'No masters found, exiting.'
    return 1

  slaves = []
  for master_name in master_names:
    if options.builders:
      builder_names = options.builders.split(',')
    else:
      builders_url = '%s/get_builders/%s?json=1' % (
        CHROME_BUILD_EXTRACT_BASE_URL, master_name)
      builder_names = fetch_json(builders_url).get('builders', [])

    if not builder_names:
      print 'No builders found, exiting.'
      return 1

    master_data_url = '%s/get_master/%s' % (
        CHROME_BUILD_EXTRACT_BASE_URL, master_name)
    master_data = fetch_json(master_data_url).get('builders')
    if not master_data:
      logging.error('Failed to fetch builders data from master %s, '
                    'skipping the master.', master_name)
      continue

    slave_set = set()
    for builder_name in builder_names:
      builder = master_data.get(builder_name, {})
      slave_set.update(builder.get('slaves', []))

    logging.info('Found %d slaves:\n[%s]', len(slave_set),
                 ', '.join(slave_set))

    pool = ThreadPool(100)
    for slave_name, builds in pool.imap_unordered(process_slave(options.count),
                                          slave_set):
      total = len(builds)
      logging.debug('Got %d builds for slave %s', total, slave_name)

      failures = len([b for b in builds if b['results'] == 2])
      exceptions = len([b for b in builds if b['results'] == 4])
      successes = len([b for b in builds if b['results'] == 0])

      bad_runs = failures + exceptions
      if total == 0:
        failure_rate = 0.0
        success_rate = 0.0
      else:
        failure_rate = float(bad_runs) / total
        success_rate = float(successes) / total
      slaves.append({
          'slave': slave_name,
          'master': master_name,
          'builds': builds,
          'failures': failures,
          'exceptions': exceptions,
          'successes': successes,
          'failure_rate': failure_rate,
          'success_rate': success_rate,
      })

  slaves_sorted = sorted(slaves, key=lambda s: s.get('success_rate', 0))

  print 'Top %d slaves with lowest success rates:' % options.top
  print 'Success % | failed | exceptions | succeeded | total | URL'
  for slave in slaves_sorted[:options.top]:
    print ('%8.2f%% | %6d | %10d | %9d | %5d | %s') % (
        slave['success_rate'] * 100.0,
        slave['failures'],
        slave['exceptions'],
        slave['successes'],
        len(slave['builds']),
        SLAVE_URL % (slave['master'], slave['slave']))


if __name__ == '__main__':
  sys.exit(main())
