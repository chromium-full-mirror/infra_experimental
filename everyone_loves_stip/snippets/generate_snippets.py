#!/usr/bin/env python

import argparse
from time import gmtime
import numpy
import requests
from spark import spark
import sys


def seconds_to_human(secs):
  raw_minutes = secs / 60

  raw_hours, minutes = divmod(raw_minutes, 60)
  result_str = '%dm' % minutes

  raw_days, hours = divmod(raw_hours, 24)
  if hours or raw_days:
    result_str = '%dh' % hours + result_str

  weeks, days = divmod(raw_days, 7)
  if days or weeks:
    result_str = '%dd' % days + result_str
  if weeks:
    result_str = '%dw' % weeks + result_str

  return result_str


def get_times(user, interval, server):
  return requests.get(
      '%s/user/%s/stats_json/%s' % (server, user, interval)).json()['latencies']


def get_args():
  parser = argparse.ArgumentParser(
      description='Obtain weekly/monthly review stats from Rietveld.')
  parser.add_argument('user',
      help='Email of the user to generate a report for. Ex: stip@chromium.org.')
  parser.add_argument('interval',
      type=int,
      choices=[7, 30],
      help='Time interval to generate a report for.')
  parser.add_argument('--server',
      default='https://codereview.chromium.org',
      help='Rietveld instance to connect to. (default %(default)s).')
  parser.add_argument('--bins',
      default=20,
      type=int,
      help='Number of bins for the histogram. (default %(default)s).')
  parser.add_argument('--annotate', action='store_true',
      help='Annotate the histograms with median and 90th percentile.')
  args = parser.parse_args()
  return args


def find_bin(edges, n):
  return numpy.searchsorted(edges, n) - 1


def print_hist(bins, edges, p50, p90, label='', annotate=False):
  p50bin = find_bin(edges, p50)
  p90bin = find_bin(edges, p90)

  if annotate:
    if p50bin == p90bin:
      print '`' + ' ' * (p50bin - 1) + '*' + '`'
    else:
      print '`' + ' ' * (p50bin) + '5' + ' ' * (p90bin - p50bin - 1) + '9' + '`'
  print '- `' + spark.spark_string(bins) + '`' + label


def gen_hist(times, numbins, pmin, pmax, logarithmic=False):
  if logarithmic:
    bins = 10 ** numpy.linspace(numpy.log10(pmin), numpy.log10(pmax), numbins)
  else:
    bins = numpy.linspace(0, pmax, numbins)
  return numpy.histogram(times, bins=bins)


def main():
  args = get_args()
  times = get_times(args.user, args.interval, args.server)
  reviewed_times = filter(lambda x: x > 0, times)

  print '%s day [review statistics](%s/user/%s/stats/%s):' % (
      args.interval, args.server, args.user, args.interval)
  print

  received = len(times) / float(args.interval)
  print '- Received: %.2f r/day' % received
  reviewed = len(reviewed_times) / float(args.interval)
  print '- Reviewed: %.2f r/day' % reviewed

  if reviewed_times:
    p50 = numpy.percentile(reviewed_times, 50)
    p75 = numpy.percentile(reviewed_times, 75)
    p90 = numpy.percentile(reviewed_times, 90)
    pmin = min(reviewed_times)
    pmax = max(reviewed_times)

    print '- Median review latency: %s' % seconds_to_human(p50)
    print '- 75th: %s 90th: %s Max: %s' % (
        seconds_to_human(p75),
        seconds_to_human(p90),
        seconds_to_human(pmax))

    bins, edges = gen_hist(
        reviewed_times, args.bins, pmin, pmax)
    print_hist(bins, edges, p50, p90, label=' (latency distribution, linear x)',
        annotate=args.annotate)

    log_bins, log_edges = gen_hist(
        reviewed_times, args.bins, pmin, pmax, logarithmic=True)
    print_hist(log_bins, log_edges, p50, p90,
        label=' (latency distribution, log10 x)',
        annotate=args.annotate)



if __name__ == '__main__':
  sys.exit(main())
