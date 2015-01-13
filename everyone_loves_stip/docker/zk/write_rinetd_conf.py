#!/usr/bin/env python
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
from jinja2 import Environment, FileSystemLoader
import os
import sys

SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('output_file', help='write cfg to this file.',
                      default='/etc/rinetd.conf')
  parser.add_argument(
      '--starting-port-envar', help='envar specifying starting port',
      default='KUBERNETES_ZK_REDIR_START_PORT')
  parser.add_argument(
      '--cluster-size-envar', help='envar specifying the cluster size',
      default='KUBERNETES_ZK_CLUSTER_SIZE')
  parser.add_argument(
      '--dry-run', help='don\'t write anything.', action='store_true')
  parser.add_argument(
      '--template-name', help='template to use.', default='rinetd_cfg.template')
  args = parser.parse_args()

  starting_port = int(os.environ[args.starting_port_envar])
  cluster_size = int(os.environ[args.cluster_size_envar])

  leader_ips = []
  election_ips = []
  for i in range(cluster_size):
    leader_ips.append(os.environ['ZOO%d_LEADER_SERVICE_HOST' % i])
    election_ips.append(os.environ['ZOO%d_ELECTION_SERVICE_HOST' % i])

  ctx = {
      'starting_port': starting_port,
      'cluster_size': cluster_size,
      'leader_ips': leader_ips,
      'election_ips': election_ips,
  }

  env = Environment(loader=FileSystemLoader(SCRIPT_DIR))
  rendered_data = env.get_template(args.template_name).render(ctx)

  output_file = os.path.abspath(args.output_file)
  print 'writing to %s:\n%s' % (output_file, rendered_data)
  if args.dry_run:
    print 'dry run, not writing to file.'
  else:
    with open(output_file, 'w') as f:
      f.write(rendered_data)
  return 0


if __name__ == '__main__':
  sys.exit(main())
