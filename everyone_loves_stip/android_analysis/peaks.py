import argparse
import datetime
import itertools
import logging
import json
import numpy
import requests
import sys

import libchromiumcqstatus


def convert_to_ts(dt):
  epoch = datetime.datetime.utcfromtimestamp(0)
  return (dt - epoch).total_seconds()


def get_args():
  parser = argparse.ArgumentParser(
      description='Detects peaks in CL volume.')
  parser.add_argument('start',
      help='How many days to scan.')
  parser.add_argument('--project', default='chromium',
      help='The project to scan.')
  parser.add_argument('--days', default=7 * 4, type=int,
      help='How many days to scan.')
  parser.add_argument('--chunk_count', default=1000, type=int,
      help='How many items to grab per query. Reduce if you start seeing '
           'errors.')
  parser.add_argument('--window', default=60, type=int,
      help='Peak window width.')
  parser.add_argument('-v', '--verbose', action='store_true',
      help='Enable verbose logging.')
  parser.add_argument('--raw_starts', default='raw_starts.json',
      help='Output file.')
  parser.add_argument('--input', action='store_true',
      help='If true, load from a raw_starts file, otherwise write to it.')
  parser.add_argument('--output', default='peaks.json',
      help='Output file.')
  args = parser.parse_args()

  if args.days < 0:
    parser.error('Days must be positive.')

  day_format = '%Y-%m-%d'
  start = datetime.datetime.strptime(args.start, day_format)
  end = start + datetime.timedelta(days=args.days)

  args.start = int(convert_to_ts(start))
  args.end = int(convert_to_ts(end))

  return args


def main():
  args = get_args()

  if args.verbose:
    logging.getLogger().setLevel(logging.DEBUG)
  else:
    logging.getLogger().setLevel(logging.INFO)

  if args.input:
    logging.info('Reading patch_starts from %s', args.raw_starts)
    with open(args.raw_starts) as f:
      patch_starts = json.load(f)
  else:
    logging.info('Getting patch_starts from chromium-cq-status.')
    with requests.Session() as session:
      patch_start_events = libchromiumcqstatus.get_action_time_range(
          args.project, 'patch_start', args.start, args.end, session,
          chunk_count=args.chunk_count)
      patch_starts = [x['fields']['timestamp'] for x in patch_start_events]
    logging.info('Writing patch_starts to %s', args.raw_starts)
    with open(args.raw_starts, 'w') as f:
      json.dump(list(patch_starts), f)

  hour_bins = []
  for hour, group in itertools.groupby(
      patch_starts, lambda x: (
        int(float(x)) / (args.window * 60)) * (args.window * 60)):
    hour_str = datetime.datetime.utcfromtimestamp(hour).isoformat()
    if '.' not in hour_str:
      hour_str += '.0'
    hour_str += 'Z'
    hour_bins.append((hour_str, len(list(group))))

  hour_bins.sort(key=lambda x: x[0])

  with open(args.output, 'w') as f:
    json.dump(hour_bins, f)

  logging.info('Wrote hourly data to %s', args.output)

  highest = max(hour_bins, key=lambda x: x[1])

  print 'Highest detected peak: %s: %d' % (highest[0], highest[1])



if __name__ == '__main__':
  sys.exit(main())
