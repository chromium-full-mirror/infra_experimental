#!/usr/bin/env python
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
'''Generate current load stats for the given buildbot master.'''

import argparse
import json
import os
import sys
import urllib2


class ListAction(argparse.Action):
  def __call__(self, parser, namespace, values, option_string=None):
    if values == 'all':
      setattr(namespace, self.dest, [])
    else:
      setattr(namespace, self.dest, values.split(','))


def get_options():
  parser = argparse.ArgumentParser(
      description=sys.modules['__main__'].__doc__)
  parser.add_argument('--url',
                      default='',
                      help=('URL of the buildbot master to inspect. '
                            'E.g. http://build.chromium.org/p/chromium.linux'))
  parser.add_argument('--master',
                      default='',
                      help=('buildbot master to inspect. E.g. chromium.linux'))
  parser.add_argument('--builders',
                      default=[],
                      action=ListAction,
                      dest='builders',
                      help=(
      'Comma-separated list of builders. '
      'E.g. --builders "win_chromium_rel,linux_chromium_rel" '
      'Default is "all". Use "cq" to list only builders used by CQ.'))
  parser.add_argument('--all', default=True,
                      action='store_true',
                      help=(
      'List all builders, even inactive ones (default).'))
  parser.add_argument(
      '--active', default=False,
      action='store_false',
      dest='all',
      help=('List  only active builders '
            '(those that have running or pending jobs)'))
  return parser.parse_args()


def format_builder(builder):
  return '%4d slaves, %4d running and %4d pending in %s' % (
      len(builder[1]['slaves']),
      len(builder[1]['currentBuilds']),
      builder[1]['pendingBuilds'],
      builder[0])


def is_builder_relevant(name, builder, options):
  """Check if this builder is relevant for stats."""
  return ((not options.builders or name in options.builders) and
          (options.all or
           (builder['currentBuilds'] or builder['pendingBuilds'])))


def split_by_slave_pools(builders):
  # Split builders into disjoint equivalence classes by shared slave
  # pools.  A builder belongs to an equivalence class if its slave pool
  # has common slaves with those in the equivalence class.
  slavesets = []
  for builder_name, builder_data in builders.iteritems():
    new_slaveset = {
        'slaves'  : set(builder_data['slaves']),
        'builders': [(builder_name, builder_data)],
        'running' : len(builder_data['currentBuilds']),
        'pending' : builder_data['pendingBuilds']}

    # Merge with all intersecting slavesets
    new_slavesets = []
    for slaveset in slavesets:
      if slaveset['slaves'] & new_slaveset['slaves']:
        new_slaveset['slaves'] |= slaveset['slaves']
        new_slaveset['builders'].extend(slaveset['builders'])
        new_slaveset['running'] += slaveset['running']
        new_slaveset['pending'] += slaveset['pending']
      else:
        new_slavesets.append(slaveset)

    new_slavesets.append(new_slaveset)
    slavesets = new_slavesets
  return slavesets

def main():
  options = get_options()
  all_builders = {}
  if options.url:
    url = options.url.rstrip('/')
  elif options.master:
    url = 'http://build.chromium.org/p/' + options.master
  else:
    print 'ERROR: One of --url or --master options is required.'
    sys.exit(1)

  print 'Loading %s' % url + '/json/builders'
  all_builders = json.loads(urllib2.urlopen(url + '/json/builders').read())
  print 'Loading %s' % url + '/json/slaves'
  all_slaves = json.loads(urllib2.urlopen(url + '/json/slaves').read())
  builders = {k: v for k, v in all_builders.iteritems()
              if is_builder_relevant(k, v, options)}

  slavesets = split_by_slave_pools(builders)
  # Add offline slaves information.
  for slaveset in slavesets:
    slaveset.setdefault('slaves_connected', 0)
    for slave_name in slaveset['slaves']:
      if all_slaves[slave_name]['connected']:
        slaveset['slaves_connected'] += 1

  top_pending = sorted(
      slavesets, key=lambda x: (x['pending'], x['running']), reverse=True)

  total_pending = sum(s['pending'] for s in slavesets)
  total_running = sum(s['running'] for s in slavesets)
  total_connected = sum(s['slaves_connected'] for s in slavesets)
  total_slaves = sum(len(s['slaves']) for s in slavesets)

  print
  print 'Found total %3d running and %3d pending builds,' % (
      total_running, total_pending)
  print '  %d connected, %d offline, total %d slaves.' % (
      total_connected, total_slaves - total_connected, total_slaves)
  print
  print '%2d sets of %sbuilders grouped by common slave pools:' % (
      len(top_pending), '' if options.all else 'active ')
  for slaveset in top_pending:
    builders = sorted(
        slaveset['builders'],
        key=lambda x: (x[1]['pendingBuilds'], len(x[1]['currentBuilds'])),
        reverse=True)
    print ('%4d slaves (%d connected, %d offline), '
           '%4d running and %4d pending jobs:\n    %s' % (
        len(slaveset['slaves']),
        slaveset['slaves_connected'],
        len(slaveset['slaves']) - slaveset['slaves_connected'],
        slaveset['running'],
        slaveset['pending'],
        '\n    '.join(map(format_builder, builders))))


if __name__ == '__main__':
  main()
