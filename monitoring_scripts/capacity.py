#!/usr/bin/env python

import argparse
import datetime
import logging
import math
import numpy
import requests_cache
import urllib


# Expects % (master, builder)
CHROME_MONITOR_URL = (
    'https://chrome-monitor.appspot.com/view_graph/%s%%20'
    'Builder%%20%s%%20Queue/Running?json=1&days=365')

# Expects % (builder, master, date_str, cursor)
CHROME_BUILD_EXTRACT_URL = (
    'https://chrome-build-extract.appspot.com/get_builds?num_builds=50&%s')


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


def get_stats(times, time_period_s):
  result = {
      'mean_cycle_time_s': 0.0,
      'median_cycle_time_s': 0.0,
      'slaves_needed': 0.0,
      'total_runtime': 0.0
  }
  if times:
    result = {
        'mean_cycle_time_s': sum(times) / (len(times) or 1),
        'median_cycle_time_s': numpy.median(times),
        'slaves_needed': sum(times) / time_period_s,
        'total_runtime': sum(times)
    }
  return result


def estimate_wait_time(num_pending, num_bots, run_time_s):
  if not num_bots:
    return 0.0
  return round(num_pending * run_time_s / num_bots)


def estimate_num_bots(run_time_s):
  """Estimate the number of bots required for CQ.

  It uses a very simplistic formula of 40 bots per 1 hour of runtime,
  or runtime_in_seconds / 90.
  """
  logging.debug('estimate_num_bots(%r)', run_time_s)
  return int(math.ceil(run_time_s / 90))


def safe_div(x, y):
  if y:
    return x / y
  else:
    return 0


def get_args():
  parser = argparse.ArgumentParser()
  parser.add_argument('--master', required=True)
  parser.add_argument(
      '--builders', required=True,
      help='Comma-separated list of builders. Estimate capacity for all '
      'the given builders, assuming the builders share the same slave pool.')
  parser.add_argument(
      '--num_slaves', default=0, type=int,
      help=('The number of existing slaves for the pool of builders. '
            'If omitted, attempt to derive it automatically.'))
  parser.add_argument('--from-date', required=True)
  parser.add_argument('--to-date', required=True)
  parser.add_argument('-v', '--verbose', action='store_true')
  parser.add_argument('-q', '--quiet', action='store_true')
  parser.add_argument('--csv', action='store_true', default=True,
                      help='Print in CSV format.')
  parser.add_argument('--text', action='store_false', dest='csv',
                      help='Print in plain text format.')
  parser.add_argument('--print-builders', action='store_true',
                      help='Print estimates for individual builders.')
  parser.add_argument('--print-build-times', action='store_true',
                      help='Print cycle times for individual builds '
                      '(usually a very long list!).')
  parser.add_argument('--print_daily', action='store_true',
                      help='Print pool estimates by day.')
  parser.add_argument('--clear', action='store_true',
                      help='Clear requests cache.')
  return parser.parse_args()


def compute_estimates(aggregates, name='', pending_key='max_pending'):
  return [
      {'key': 'Name', 'value': name, 'format': '%11s'},
      {'key': 'master', 'value': aggregates['master'], 'format': '%11s'},
      {'key': 'builder', 'value': aggregates['builder'], 'format': '%11s'},
      {'key': 'num_builds', 'value': aggregates['num_builds'],
       'format': '%11d'},
      {'key': 'total_runtime', 'value': aggregates['total_runtime'],
       'format': '%11.1f'},
      {'key': 'Median cycle', 'value': aggregates['median_cycle_time_s'],
       'format': '%11.1f'},
      {'key': 'Mean cycle', 'value': aggregates['mean_cycle_time_s'],
       'format': '%11.1f'},
      {'key': 'Max running', 'value': aggregates['max_running'],
       'format': '%11d'},
      {'key': 'Max pending', 'value': aggregates[pending_key],
       'format': '%11d'},
      # Use mean cycle time for estimating wait time. Median time
      # would give unreliable results.
      {'key': 'T_wait', 'value': estimate_wait_time(
          aggregates[pending_key],
          aggregates['max_running'],
          aggregates['mean_cycle_time_s']) / 60.,
       'format': '%11.1f'},
      {'key': '#slaves', 'value': aggregates['num_slaves'], 'format': '%11d'},
      {'key': '#slaves min',
       'value': safe_div(aggregates['total_runtime'],
                         aggregates['time_period_s']),
       # Mostly idle bots need higher precision to estimate minimum
       # capacity, hence .2f instead of .1f.
       'format': '%11.2f'},
      {'key': '#slaves for CQ',
       'value': estimate_num_bots(aggregates['mean_cycle_time_s']),
       'format': '%11d'},
  ]


def fetch_load_history(session, points_by_day, master, builder):
  """Populate |points_by_day| with number of running and pending builds by day.
  """
  url = CHROME_MONITOR_URL % (urllib.quote(master),
                              urllib.quote(builder))
  logging.debug('Fetching historical load data for %s/%s at %s', master,
                builder, url)
  try:
    monitor_json = session.get(url).json()
  except Exception as e:
    logging.error('failed to fetch historical load data from %s: %s',
                  url, e)
    return points_by_day

  if 'data' not in monitor_json:
    logging.error('fetched invalid historical load data from %s', url)
    return points_by_day

  # Process the data into a meaningful dict grouped by day
  for point in monitor_json['data']:
    point_json = {}
    idx = 0
    for name in monitor_json['point_names']:
      point_json[name] = point[idx]
      idx += 1
    date = datetime.datetime.fromtimestamp(point_json['time'])
    day = date.strftime('%Y-%m-%d')
    points_by_day.setdefault(day, {})
    # [day] entry may already exist without these fields; initialize
    # separately.
    points_by_day[day].setdefault('max_pending', 0)
    points_by_day[day].setdefault('max_running', 0)
    points_by_day[day].setdefault('points', [])
    points_by_day[day]['points'].append(point_json)
    points_by_day[day]['max_pending'] = max(
        points_by_day[day]['max_pending'], point_json['pending'])
    points_by_day[day]['max_running'] = max(
        points_by_day[day]['max_running'], point_json['running'])
    points_by_day[day]['master'] = master
    points_by_day[day]['builder'] = builder
  return points_by_day


def fetch_builds(session, points_by_day, from_date, to_date, master, builder):
  """Populate |points_by_day| with builds data."""
  cur_date = from_date
  day = cur_date.strftime('%Y-%m-%d')
  points_by_day.setdefault(day, {})
  points_by_day[day]['master'] = master
  points_by_day[day]['builder'] = builder
  while cur_date < to_date:
    day = cur_date.strftime('%Y-%m-%d')
    cur_date += datetime.timedelta(days=1)
    # Sometimes we may get a repeating cursor from a few pages
    # back. AE bug? crbug.com/435241.
    cursors = set()
    try:
      cursor = ''
      parsed = {'builds': []}
      while True:
        params = urllib.urlencode({
            'builder': builder,
            'master': master,
            'day': day,
            'cursor': cursor,
        })
        search_url = CHROME_BUILD_EXTRACT_URL % params
        logging.debug('Fetching build data for %s/%s @ %s at %s',
                      master, builder, day, search_url)
        new_data = session.get(search_url).json()
        parsed['builds'].extend(new_data['builds'])
        if not new_data['cursor']:
          break
        if new_data['cursor'] in cursors:
          logging.error('Repeated cursor %s fetched by %s',
                        new_data['cursor'], search_url)
          break
        cursor = new_data['cursor']
        cursors.add(cursor)
    except Exception as e:
      print 'ERROR: skipping the day, %s' % e
      continue
    points_by_day.setdefault(day, {})
    points_by_day[day]['builds'] = parsed['builds']
    runtimes = [
        build['times'][1] - build['times'][0] for build in parsed['builds']]

    points_by_day[day]['runtimes'] = runtimes
    points_by_day[day].update(get_stats(runtimes, 24 * 3600))
    points_by_day[day]['master'] = master
    points_by_day[day]['builder'] = builder

  return points_by_day


def print_individual_build_runtimes(points_by_day):
  print '\t'.join(['builder', 'build#', 'start time', 'cycle time'])
  for day in sorted(points_by_day.keys()):
    builder = points_by_day[day]['builder']
    for build in points_by_day[day].get('builds', []):
      row = [builder, str(build['number']),
             '%s' % datetime.datetime.fromtimestamp(build['times'][0]),
             '%s' % (build['times'][1] - build['times'][0])]
      print '\t'.join(row)


def merge_points_by_day(builder_points):
  """Merge daily stats of builders into a single pool stream.

  |builder_points| is a dict from builder to its
   points_by_day. Combine all the builders in each day into compatible
   data for the shared slave pool.
   """
  lists_by_day = {}
  # First pass: map days to list of points_by_day
  for points_by_day in builder_points.itervalues():
    for day in points_by_day:
      lists_by_day.setdefault(day, [])
      lists_by_day[day].append(points_by_day[day])

  merged_by_day = {}
  # Second pass: merge daily lists into an aggregated entry
  for day, entries in lists_by_day.iteritems():
    merged = {'max_pending': 0,
              'max_running': 0,
              'builds': [],
              'runtimes': [],
              'master': 'unknown',
              'builder' : set()}
    for entry in entries:
      # TODO(sergeyberezin): merge raw 'points' my ranges of
      # timestamps. This would give a better resolution to the actual
      # load of the slave pool.
      merged['max_pending'] = max(
          merged['max_pending'], entry.get('max_pending', 0))
      merged['max_running'] = max(
          merged['max_running'], entry.get('max_running', 0))
      merged['builds'].extend(entry.get('builds', []))
      merged['runtimes'].extend(entry.get('runtimes', []))
      merged['master'] = entry.get('master', merged['master'])
      if 'builder' in entry:
        merged['builder'].add(entry['builder'])
    merged['num_builds'] = len(merged['builds'])
    merged['builder'] = ','.join(sorted(merged['builder']))
    merged_by_day[day] = merged
  return merged_by_day


def compute_aggregates(points_by_day, from_date, to_date, args):
  max_pending_list = []
  max_running_list = []
  master = 'unknown'
  builder = 'unknown'
  runtimes = []
  for day in sorted(points_by_day.keys()):
    date = datetime.datetime.strptime(day, '%Y-%m-%d')
    if from_date <= date and date < to_date:
      entry = points_by_day[day]
      max_pending_list.append(entry.get('max_pending', 0))
      max_running_list.append(entry.get('max_running', 0))
      # Assumption: master and builder are the same in every entry.
      master = entry.get('master', master)
      builder = entry.get('builder', builder)
      runtimes.extend(entry.get('runtimes', []))
  # To keep numpy sane.
  runtimes = runtimes or [0.0]
  max_pending_list = max_pending_list or [0]
  max_running_list = max_running_list or [0]
  return {'master' : master,
          'builder': builder,
          'num_slaves': args.num_slaves,
          'median_pending': numpy.median(max_pending_list),
          'max_pending': max(max_pending_list),
          'median_running': numpy.median(max_running_list),
          'max_running': max(max_running_list),
          'median_cycle_time_s': numpy.median(runtimes),
          'mean_cycle_time_s': numpy.mean(runtimes),
          'total_runtime': sum(runtimes),
          'num_builds': sum([len(x.get('builds', []))
                             for x in points_by_day.itervalues()]),
          'runtimes': runtimes,
          'time_period_s': (to_date - from_date).total_seconds(),
          'longest_build_time': max(list(
              max(x.get('runtimes', [0]) or [0])
              for x in points_by_day.itervalues()) or [0]),
          }


def pretty_print_estimates_header(estimates):
  print(' | '.join([x['key'] for x in estimates]))


def pretty_print_estimates(estimates):
  values = tuple(x['value'] for x in estimates)
  print(' | '.join([x['format'] for x in estimates]) % values)


def pretty_print_daily_estimates(points_by_day):
  for day in sorted(points_by_day):
    if 'estimates' in points_by_day[day]:
      pretty_print_estimates(points_by_day[day]['estimates'])


def print_csv_header(estimates):
  print('\t'.join([x['key'] for x in estimates]))


def print_csv(estimates):
  values = tuple(x['value'] for x in estimates)
  print('\t'.join([x['format'] for x in estimates]) % values)


def print_estimates_header(args, estimates):
  if args.csv:
    print_csv_header(estimates)
  else:
    pretty_print_estimates_header(estimates)


def print_estimates(args, estimates):
  if args.csv:
    print_csv(estimates)
  else:
    pretty_print_estimates(estimates)


def main():
  args = get_args()
  setup_logging(args)

  requests_cache.install_cache('capacity')
  session = requests_cache.CachedSession()

  if args.clear:
    logging.info('Clearing cache...')
    session.cache.clear()

  from_date = datetime.datetime.strptime(args.from_date, '%Y-%m-%d')
  to_date = datetime.datetime.strptime(args.to_date, '%Y-%m-%d')
  builders = args.builders.split(',')

  points_by_day = {}
  aggregates_by_builder = {}
  estimates_by_builder = {}
  pool_mean_runtime_s = 0
  for builder in builders:
    points_by_day[builder] = fetch_load_history(
        session, {}, args.master, builder)
    fetch_builds(session, points_by_day[builder],
                 from_date, to_date, args.master, builder)
    aggregates_by_builder[builder] = compute_aggregates(
        points_by_day[builder], from_date, to_date, args)
    pool_mean_runtime_s += aggregates_by_builder[builder]['mean_cycle_time_s']
    logging.debug('aggregates: %r', aggregates_by_builder[builder])
    estimates_by_builder[builder] = compute_estimates(
        aggregates_by_builder[builder], name='builder total')

  # Merged pool stats
  merged_by_day = merge_points_by_day(points_by_day)
  merged_aggregates = compute_aggregates(
      merged_by_day, from_date, to_date, args)
  # For correct estimates, add up mean cycle times of all builders in the pool.
  merged_aggregates['mean_cycle_time_s'] = pool_mean_runtime_s
  merged_estimates = compute_estimates(merged_aggregates, name='pool')
  if args.print_daily:
    merged_daily_estimates = {}
    for day in merged_by_day:
      start_date = datetime.datetime.strptime(day, '%Y-%m-%d')
      end_date = start_date + datetime.timedelta(days=1)
      aggregates = compute_aggregates({day: merged_by_day[day]},
                                      start_date, end_date, args)
      aggregates['mean_cycle_time_s'] = pool_mean_runtime_s
      merged_daily_estimates[day] = compute_estimates(aggregates, name=day)

  print_estimates_header(args, merged_estimates)
  if args.print_builders:
    for builder in builders:
      print_estimates(args, estimates_by_builder[builder])

  if args.print_daily:
    for day in sorted(merged_daily_estimates):
      date = datetime.datetime.strptime(day, '%Y-%m-%d')
      if from_date <= date and date < to_date:
        print_estimates(args, merged_daily_estimates[day])

  print_estimates(args, merged_estimates)

  if args.print_build_times:
    for builder in points_by_day:
      print_individual_build_runtimes(points_by_day[builder])


if __name__ == '__main__':
  main()
