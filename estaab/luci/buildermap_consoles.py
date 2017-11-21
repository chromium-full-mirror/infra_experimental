#!/usr/bin/python2
#
# Quick and dirty script to generate milo console definitions from
# a buildermap.json.

import collections
import json
import sys


assert len(sys.argv) == 2

builderjson = json.load(open(sys.argv[1]))

master_to_builders = collections.OrderedDict()
for item in builderjson:
  m = item['mastername']
  if 'master.tryserver.chromium' in m and 'internal' not in m:
    master_to_builders.setdefault(m, []).append(item['builder'])

for m, bs in master_to_builders.iteritems():
  m = m[len('master.'):]
  print 'consoles: {'
  print '  id: "%s"' % m
  print '  name: "%s"' % m
  print '  repo_url: "https://chromium.googlesource.com/chromium/src"'
  print '  ref: "refs/heads/master"'
  print '  manifest_name: "REVISION"'
  print ''
  for b in sorted(bs):
    print '  builders: {'
    print '    name: "buildbot/%s/%s"' % (m, b)
    print '  }'
  print '}'
  print ''
