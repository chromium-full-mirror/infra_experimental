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
  parser.add_argument('output_file', help='write cfg to this file.')
  parser.add_argument(
      '--envar-prefix', help='envar prefix to import', default='KUBERNETES')
  parser.add_argument(
      '--dry-run', help='don\'t write anything.', action='store_true')
  parser.add_argument(
      '--template-name', help='template to use.', default='kafka_server_config.properties.template')
  args = parser.parse_args()

  ctx = {
      'ZOOKEEPER_SERVICE_HOST': os.environ['ZOOKEEPER_SERVICE_HOST'],
      'ZOOKEEPER_SERVICE_PORT': os.environ['ZOOKEEPER_SERVICE_PORT'],
  }
  for envar, value in os.environ.iteritems():
    if envar.startswith(args.envar_prefix):
      ctx[envar] = value

  env = Environment(loader=FileSystemLoader(SCRIPT_DIR))
  env.globals.update({
      'int': int,
  })
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
