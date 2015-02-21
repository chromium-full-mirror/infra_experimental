#!/usr/bin/env python

import argparse
from pprint import pprint
import sys
from collections import defaultdict

from AsciiHistogram import AsciiHistogram
from ChromiumCqStatus import ChromiumCqStatus

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--issue', nargs='?', help='or issue:patchset')
  parser.add_argument('--patchset', nargs='?', help='')
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

  # Process the stream of attempts via a callback
  state = {'counters': defaultdict(int),
           'histograms': defaultdict(AsciiHistogram),
  }
  def callback(state,x):
    c = state['counters']
    h = state['histograms']
    h['all'].add(x.duration())
    c['000_all'] += 1
    if (not x.is_typical):
      h['atypical'].add(x.duration())
      c['100_atypical'] += 1
      c['110_atypical:%s' % x.not_typical_reason] += 1
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
        
  cq_status.process_recent_attempts(callback, state, count=1000)
        
  print "\nHistograms:"
  for name in (['all', 'typical', 'atypical', 'happy', 'unhappy']):
    print "% 20.20s : %s" % (name, state['histograms'][name])

  print "\nCounters:"
  for key in sorted(state['counters']):
    print "  % 6d %s" % (state['counters'][key], key)

if __name__ == '__main__':
  sys.exit(main())
