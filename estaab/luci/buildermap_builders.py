#!/usr/bin/python2
#
# Quick and dirty script to print milo builder names from a buildermap.json
# script.

import collections
import json
import sys

assert len(sys.argv) == 2

builderjson = json.load(open(sys.argv[1]))

master_to_builders = collections.OrderedDict()
for item in builderjson:
  m = item['mastername']
  if ('master.chromium' in m or 'tryserver.chromium' in m) and 'internal' not in m:
    master_to_builders.setdefault(m, []).append(item['builder'])

for m, bs in master_to_builders.iteritems():
  m = m[len('master.'):]
  for b in sorted(bs):
    print 'buildbot/%s/%s' % (m, b)
