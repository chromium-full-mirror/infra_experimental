#!/usr/bin/env python
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
from jinja2 import Environment, FileSystemLoader
import os
import sys



def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('output_file', help='write cfg to this file.')
  parser.add_argument(
      '--envar-prefix', help='envar prefix to import', default='KUBERNETES')
  parser.add_argument(
      '--data-dir-envar', help='envar specifying data dir',
      default='KUBERNETES_ZK_DATA_DIR')
  parser.add_argument(
      '--idx-envar', help='envar identifying this pod',
      default='KUBERNETES_POD_IDX')
  parser.add_argument(
      '--dry-run', help='don\'t write anything.', action='store_true')
  parser.add_argument(
      '--template-name', help='template to use.', default='zoo_cfg.template')
  args = parser.parse_args()

  ctx = {}
  for envar, value in os.environ.iteritems():
    if envar.startswith(args.envar_prefix):
      ctx[envar] = value

  env = Environment(loader=FileSystemLoader('.'))
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

  id_file = os.path.abspath(os.path.join(
      os.environ[args.data_dir_envar], 'myid'))
  myid = int(os.environ[args.idx_envar])
  print 'writing %d to %s' % (myid, id_file)
  if args.dry_run:
    print 'dry run, not writing to file.'
  else:
    with open(id_file, 'w') as f:
      f.write('%d\n' % myid)

  return 0


if __name__ == '__main__':
  sys.exit(main())
