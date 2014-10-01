#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Collect stats about failing slaves."""

import argparse
import json
import logging
from multiprocessing.pool import ThreadPool
import operator
import requests_cache
import sys
import urllib2


CHROME_BUILD_EXTRACT_BASE_URL = "http://chrome-build-extract.appspot.com"


def get_options():
  parser = argparse.ArgumentParser(__doc__)
  parser.add_argument("--count", default=20, type=int,
                      help='Number of builds per slave to retrieve.')
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
  parser.add_argument('--clear', action='store_true',
                      help='Clear the cache before starting.')
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

def main():
  options = get_options()
  logging.basicConfig(level=logging.DEBUG if options.verbose else logging.WARN)

  requests_cache.install_cache('cq')
  session = requests_cache.CachedSession()
  if options.clear:
    logging.info('Clearing cache...')
    session.cache.clear()

  slaves = {}
  if options.masters:
    master_names = options.masters.split(',')
  else:
    masters_url = '%s/get_masters?json=1' % CHROME_BUILD_EXTRACT_BASE_URL
    master_names = session.get(masters_url).json()['masters']

  for master_name in master_names:
    if options.builders:
      builder_names = options.builders.split(',')
    else:
      builders_url = '%s/get_builders/%s?json=1' % (
        CHROME_BUILD_EXTRACT_BASE_URL, master_name)
      builder_names = session.get(builders_url).json()['builders']

    master_data_url = '%s/get_master/%s' % (
        CHROME_BUILD_EXTRACT_BASE_URL, master_name)
    master_data = session.get(master_data_url).json()['builders']

    slave_set = set()
    for builder_name in builder_names:
      builder = master_data.get(builder_name, {})
      slave_set.update(builder.get('slaves', []))

    logging.info('Found %d slaves:\n[%s]', len(slave_set),
                 ', '.join(slave_set))

    pool = ThreadPool(100)
    for slave_name, builds in pool.imap_unordered(process_slave(options.count),
                                          slave_set):
      logging.debug('Got %d builds for slave %s', len(builds), slave_name)
      failures = len([b for b in builds if b['results'] == 2])
      exceptions = len([b for b in builds if b['results'] == 4])
      successes = len([b for b in builds if b['results'] == 0])

      bad_runs = failures + exceptions
      unsuccessful = len(builds) - successes
      if successes == 0:
        failure_rate = 1.0
        success_rate = 0.0
      else:
        failure_rate = bad_runs / float(successes + bad_runs)
        success_rate = successes / len(builds)
      slaves[slave_name] = {
          'slave': slave_name,
          'builds': builds,
          'failures': failures,
          'exceptions': exceptions,
          'successes': successes,
          'failure_rate': failure_rate,
          'success_rate': success_rate,
      }

  # TODO(sergeyberezin): remove it, replace by sorting by success_rate
  # on keys.
  slave_failure_rates = []
  for slave_name, data in slaves.iteritems():
    slave_failure_rates.append((slave_name,
                                data['failures'],
                                data['successes'],
                                data['failure_rate']))

  

  slave_failure_rates = sorted(slave_failure_rates, key=operator.itemgetter(3),
                               reverse=True)

  print '20 slaves with highest failure rates:'
  for slave_name, failures, successes, failure_rate in slave_failure_rates[:20]:
    print '%s - %.2f%% (%d failures, %d successes)' % (
        slave_name, failure_rate * 100, failures, successes)


if __name__ == '__main__':
  sys.exit(main())
