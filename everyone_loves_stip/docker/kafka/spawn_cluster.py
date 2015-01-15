#!/usr/bin/env python
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
from jinja2 import Environment, FileSystemLoader
import json
import os
import sys
import yaml

SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument(
      '--output_file', help='write cfg to this file.',
      default='kubernetes.json')
  parser.add_argument(
      '--template_name', help='which template to use',
      default='kafka_pod.yaml.template')
  parser.add_argument('cluster_size', type=int,
                      help='how many nodes in the cluster')
  args = parser.parse_args()

  ctx = {
    'cluster_size': args.cluster_size
  }

  env = Environment(loader=FileSystemLoader(SCRIPT_DIR))
  rendered_data = yaml.load(env.get_template(args.template_name).render(ctx))

  output_file = os.path.abspath(args.output_file)
  print 'writing to %s' % output_file
  with open(output_file, 'w') as f:
    f.write(json.dumps(rendered_data))

  return 0


if __name__ == '__main__':
  sys.exit(main())
