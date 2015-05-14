#!/usr/bin/env python

# TODO: jq

import argparse
from pprint import pprint
import sys
from collections import defaultdict
import datetime

from AsciiHistogram import AsciiHistogram
from ChromiumCqStatus import ChromiumCqStatus

def dt2epoch(dt):
    return (dt - datetime.datetime.utcfromtimestamp(0)).total_seconds()

def datestring2epochs(datestring):
    dt = datetime.datetime.strptime(datestring, "%Y-%m-%d")
    t_start = dt2epoch(dt)
    t_end = dt2epoch(dt + datetime.timedelta(days=1))
    return t_start, t_end

# Process the stream of attempts via a callback
state = {'counters': defaultdict(int),
         'histograms': defaultdict(AsciiHistogram),
         'dates': defaultdict(int),
       }
def callback(state,x):
  state['dates'][x.start_datetime().strftime("%Y-%m-%d")] += 1
  c = state['counters']
  h = state['histograms']
  h['all'].add(x.duration())
  c['000_all'] += 1
  # print x
  if (not x.is_typical):
    h['atypical'].add(x.duration())
    c['100_atypical'] += 1
    c['110_atypical:%s' % x.not_typical_reason] += 1
    # print x.dump()
  else:
    h['typical'].add(x.duration())
    c['200_typical'] += 1
    if (x.is_happy):
      h['happy'].add(x.duration())
      c['210_happy'] += 1
    else:
      h['unhappy'].add(x.duration())
      c['220_unhappy'] += 1
      c['221_unhappy:%s' % x.not_happy_reason] += 1
      if (not x.is_happy): print x


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--issue', nargs='?', help='or issue:patchset')
  parser.add_argument('--patchset', nargs='?', help='')
  parser.add_argument('--startdate', nargs='?', help='YYYY-MM-DD')
  args = parser.parse_args()

  if args.issue and args.issue.find(':')>0:
    args.issue, args.patchset, args.attempt_number = args.issue.split(':')

  cq_status = ChromiumCqStatus()

  attempts = []
  if args.issue:
    attempts = cq_status.get_cq_attempts_for_patchset(args.issue, args.patchset)
    for attempt in attempts:
      print attempt.dump()
    return

  if args.startdate:
    t_begin, t_end = datestring2epochs(args.startdate)
    cq_status.process_dated_attempts(callback, state, begin=t_begin, end=t_end)
  else:
    cq_status.process_recent_attempts(callback, state, max_results=3)

  print "\nDates:"
  for date in sorted(state['dates']):
    print "% 20.20s : %s" % (date, state['dates'][date])

  print "\nHistograms:"
  for name in (['all', 'typical', 'atypical', 'happy', 'unhappy']):
    print "% 20.20s : %s" % (name, state['histograms'][name])

  print "\nCounters:"
  for keyval in sorted(state['counters'].iteritems(),
                       key=lambda(k,v): ("%08d_%08d" % (int(k.split("_")[0]),
                                                        sys.maxint-v)) ):
    print "  % 6d %s" % (state['counters'][keyval[0]], keyval[0])

if __name__ == '__main__':
  sys.exit(main())
