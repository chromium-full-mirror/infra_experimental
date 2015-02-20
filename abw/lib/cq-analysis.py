#!/usr/bin/env python

from ChromiumCqStatus import ChromiumCqStatus
import argparse
from pprint import pprint
import sys

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--issue', nargs='?', help='or issue:patchset')
  parser.add_argument('--patchset', nargs='?', help='')
  args = parser.parse_args()

  if args.issue and args.issue.find(':')>0:
    args.issue, args.patchset = args.issue.split(':')

  cq_status = ChromiumCqStatus()

  if args.issue:
    items = cq_status.get_cq_attempts_for_issue_patchset(args.issue, args.patchset)
    for item in items: print (item)
  else:
    items = cq_status.recent_items(count=10)

if __name__ == '__main__':
  sys.exit(main())
