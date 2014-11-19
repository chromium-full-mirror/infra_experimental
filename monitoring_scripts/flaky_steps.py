#!/usr/bin/env python

import argparse
import datetime
import logging
import numpy
import requests_cache
import sys
import urllib


# Expects % (builder, master, date_str, cursor)
CHROME_BUILD_EXTRACT_URL = (
    'https://chrome-build-extract.appspot.com/get_builds?num_builds=50&%s')


def get_args():
  parser = argparse.ArgumentParser()
  parser.add_argument('--master', required=True)
  parser.add_argument(
      '--builders', required=True,
      help='Comma-separated list of builders.')
  parser.add_argument(
      '--from-date',
      required=True,
      help=('Format: YYYY-MM-DD. Process builds from midnight of this day.'))
  parser.add_argument(
      '--to-date',
      required=True,
      help=('Format: YYYY-MM-DD. Process builds upto and excluding this day.'))
  parser.add_argument(
      '--by-builders', action='store_true',
      help='Aggregate by builders instead of steps.')
  parser.add_argument('-v', '--verbose', action='store_true')
  parser.add_argument('-q', '--quiet', action='store_true')
  parser.add_argument('--list-flaky-builds', action='store_true')
  parser.add_argument('--clear', action='store_true',
                      help='Clear requests cache.')
  args = parser.parse_args()
  args.builders = args.builders.split(',')
  return args


def setup_logging(args):
  """Configures the logging module."""
  logging.getLogger().setLevel(logging.DEBUG)

  if args.quiet:
    logging.getLogger().setLevel(logging.WARNING)

  console_logging = logging.StreamHandler()
  console_logging.setFormatter(logging.Formatter(
      '%(asctime)s %(levelname)7s %(message)s'))
  console_logging.setLevel(
      logging.DEBUG if args.verbose else logging.INFO)
  logging.getLogger().addHandler(console_logging)


def parse_properties(properties):
  """Convert list of buildbot properties into a sensible dict."""
  result = {}
  for prop in properties:
    if len(prop) < 2:
      continue
    result[prop[0]] = prop[1]
  return result


def process_build(build):
  """Parse buildbot build into a sensible dict.

  Returns:
    result (dict): patch_id: (issue, patchset)
                   build: build number
                   success: bool
                   failed_steps: list of steps.
  """
  properties = parse_properties(build.get('properties', []))
  patch_id = (properties.get('issue'), properties.get('patchset'))
  if not all(patch_id):
    logging.warning('could not parse patch_id in build: %s',
                    properties.get('buildnumber'))
  result = {
      'patch_id': patch_id,
      'build': build['number'],
      'builder': build['builderName'],
      'success': not build['results'],
      'failed_steps': [s for s in map(process_step, build['steps'])
                       if not s['success'] and not s['name'] == 'steps'],
  }
  return result


def process_step(step):
  """Makes buildbot representation of a step sane."""
  return {
      'name': step['name'],
      'success': not step['results'][0],
      'result_notes': step['results'][1],
      'begin': step.get('times', [0])[0],
      'end': step.get('times', [0, 0])[1],
  }


def find_flaky_builds(builds):
  """Find flaky builds and steps that cause those flakes.

  A flaky build is one that fail on a patch_id for which there is a
  successful run of the same builder.

  Returns result (dict) with the following keys:
    num_total_builds (int): total builds that should have passed
    num_successful_builds (int): how many of the above builds passed
    failed_builds (list): list of failed build objects - these are flakes
    failed_steps (dict): maping of step names to counts, how many times a
                         step caused a flaky build.
  """
  result = {'num_total_builds': 0,
            'num_successful_builds': 0,
            'failed_builds': [],
            'failed_steps': {},
           }
  for patch_id in builds:
    logging.debug('find_flaky_builds: builds[%r] = %r',
                  patch_id, builds[patch_id])
    failed_builds = [b for b in builds[patch_id] if not b['success']]
    num_successful_builds = len(builds[patch_id]) - len(failed_builds)
    if not num_successful_builds:
      continue
    for build in failed_builds:
      for step in build['failed_steps']:
        result['failed_steps'].setdefault(step['name'], 0)
        result['failed_steps'][step['name']] += 1
    result['num_total_builds'] += len(builds[patch_id])
    result['num_successful_builds'] += num_successful_builds
    result['failed_builds'].extend(failed_builds)
  return result


def fetch_flaky_builds(session, master, builder, from_date, to_date):
  # Map (issue, patchset) -> list of builds
  builds = {}
  dates = []
  cur_date = from_date
  while cur_date < to_date:
    date_str = cur_date.strftime('%Y-%m-%d')
    dates.append(date_str)
    cur_date += datetime.timedelta(days=1)
    try:
      cursor = ''
      data = {'builds': []}
      logging.debug('Fetching data for %s', date_str)
      while True:
        params = urllib.urlencode({
            'builder': builder,
            'master': master,
            'day': date_str,
            'cursor': cursor,
        })
        search_url = CHROME_BUILD_EXTRACT_URL % params
        response = session.get(search_url)
        new_data = response.json()
        cursor = new_data['cursor']
        data['builds'].extend(new_data['builds'])
        logging.debug('Read %d builds', len(data['builds']))
        if not cursor:
          break
    except IOError as e:
      logging.error('skipping the day %s: %s', date_str, e)
      continue

    for build in data['builds']:
      b = process_build(build)
      builds.setdefault(b['patch_id'], [])
      builds[b['patch_id']].append(b)

  return find_flaky_builds(builds)


def percentage(x, y):
  if not y:
    return 0.0
  else:
    return 100.0 * x / y


def patch_url(patch_id):
  return 'https://chromium-cq-status.appspot.com/patch-status/%s/%s' % patch_id


def build_url(master, builder, build_num):
  url = 'http://build.chromium.org/p/%s/builders/%s/builds/%d'
  return url % (master, builder, build_num)


def format_step(step):
  return '%s (%.2fs)' % (step['name'], step['end'] - step['begin'])


def print_builds(master, builder, builds):
  """Print builds in CSV format."""
  fmt = '%20s\t%20s\t%s'
  print fmt % ('Issue/patchset', 'build', 'steps')
  for build in builds:
    print fmt % (patch_url(build['patch_id']),
                 build_url(master, builder, build['build']),
                 ', '.join(map(format_step, build['failed_steps'])))


def print_flaky_stats(builder, flaky_builds):
  steps = sorted(flaky_builds['failed_steps'].iteritems(),
                 key=lambda x: x[1], reverse=True)
  print '%s: %d (%6.2f%%) flaky failures out of %d total' % (
      builder, len(flaky_builds['failed_builds']),
      percentage(len(flaky_builds['failed_builds']),
                 flaky_builds['num_total_builds']),
      flaky_builds['num_total_builds'])
  for step in steps:
    print '%d flakes in step %s' % (step[1], step[0])



def main():
  args = get_args()
  setup_logging(args)

  requests_cache.install_cache('steps')
  session = requests_cache.CachedSession()

  if args.clear:
    logging.info('Clearing cache...')
    session.cache.clear()

  from_date = datetime.datetime.strptime(args.from_date, '%Y-%m-%d')
  to_date = datetime.datetime.strptime(args.to_date, '%Y-%m-%d')

  flaky_builds = {}
  flaky_steps = {}
  for builder in args.builders:
    flaky_builds[builder] = fetch_flaky_builds(
        session, args.master, builder, from_date, to_date)
    for step, num_flakes in flaky_builds[builder]['failed_steps'].iteritems():
      flaky_steps[step] = flaky_steps.get(step, 0) + num_flakes

  for builder, flakes in flaky_builds.iteritems():
    print_flaky_stats(builder, flakes)
    if args.list_flaky_builds:
      print_builds(args.master, builder, flakes['failed_builds'])


if __name__ == '__main__':
  main()
