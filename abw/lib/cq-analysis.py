#!/usr/bin/env python

from ChromiumCqStatus import ChromiumCqStatus
import argparse
from pprint import pprint
import sys

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('issue', type=int, nargs='?', help='rietveld issue')
  parser.add_argument(
      'patchset', type=int, nargs='?', help='patchset', default=1)
  args = parser.parse_args()

  cq_status = ChromiumCqStatus()
  # data = cq_status.recent_list(count=3)
  items = cq_status.recent_items(count=1)
  #pprint(items[0])

if __name__ == '__main__':
  sys.exit(main())
