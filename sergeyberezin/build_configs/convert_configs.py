#!/usr/bin/env python

import argparse
import ast
import os


def process_waterfalls(waterfalls):
  # collect all compile targets
  targets = set()
  builders = set()
  consoles = set()
  for w in waterfalls:
    consoles.add(w['name'])
    with open(os.path.join('waterfalls', w['name'], 'builders.star'), 'w') as f:
      for name, m in w.get('machines', {}).iteritems():
        builders.add(name)
        for t in m.get('additional_compile_targets', []):
          targets.add(t)
        f.write("""

builder(
  name = {name},
)
""".format(name=name))

  # print '__all_targets = ['
  # for t in sorted(targets):
  #   print "  '%s'," % t
  # print ']\n'

  # print '__all_waterfalls = ['
  # for c in sorted(consoles):
  #   print "mkdir %s" % c
  # print ']\n'

  # print '__all_builders = ['
  # for b in sorted(builders):
  #   print "  '%s'," % b
  # print ']\n'


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('file')
  args = parser.parse_args()

  with open(args.file) as f:
    value = ast.literal_eval(f.read())

  process_waterfalls(value)


if __name__ == '__main__':
  main()
