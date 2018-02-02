#!/usr/bin/env python

import json
import ast
import argparse
import os


def get_master(builder):
  chromium_path = '/usr/local/google/home/martiniss/chromium/src'
  found = []
  with open(os.path.join(chromium_path, 'tools', 'mb', 'mb_config.pyl')) as f:
    data = ast.literal_eval(f.read())
    for master, values in data['masters'].items():
      if builder in values:
        found.append(master)
        continue
  return found


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('builder')

  args = parser.parse_args()

  found = get_master(args.builder)
  print ','.join(found)

if __name__ == '__main__':
  main()
