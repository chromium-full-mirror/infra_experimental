#!/usr/bin/env python

import argparse
import collections
import itertools
import json
import logging
import requests
import sys

import libchromiumcqstatus


def get_args():
  parser = argparse.ArgumentParser(
      description='Get information on per-CL builder timing information.')
  parser.add_argument('--project', default='chromium',
      help='The project to scan.')
  parser.add_argument('-v', '--verbose', action='store_true',
      help='Enable verbose logging.')
  parser.add_argument('--count', default=10, type=int,
      help='How many pass/fail issues to load.')
  parser.add_argument('--output', default='all_builders.json',
      help='Output file.')
  args = parser.parse_args()
  return args


def main():
  args = get_args()
  master = 'tryserver.chromium.linux'
  builder = 'linux_android_rel_ng'

  if args.verbose:
    logging.getLogger().setLevel(logging.DEBUG)
  else:
    logging.getLogger().setLevel(logging.INFO)
      
  with requests.Session() as session:
    action_args = [
        (args.project, 'verifier_pass', args.count, session),
        (args.project, 'verifier_fail', args.count, session)]

    dataz = itertools.chain.from_iterable(itertools.starmap(
      libchromiumcqstatus.get_action_count, action_args))

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
          tryjob_updates = list(
              libchromiumcqstatus.get_action_i_p_a(
                action, issue, patchset, attempt, session))
          run_data.append((issue, patchset, attempt,
            libchromiumcqstatus.convert_to_tryjob_endings(
            tryjob_updates)))

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

  with open(args.output, 'w') as f:
    json.dump(points, f)

if __name__ == '__main__':
  sys.exit(main())
