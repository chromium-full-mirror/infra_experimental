#!/usr/bin/env python
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
from jinja2 import Environment, FileSystemLoader
import httplib
import os
import socket
import sys
import time
import urllib2

SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))


def exponential_backoff(url, initial_seconds, max_tries):
  print 'contacting %s for ip' % url
  sys.stdout.flush()
  tries = 0
  last_e = None
  while tries < max_tries:
    try:
      return urllib2.urlopen(url).read()
    except (urllib2.URLError, socket.error, httplib.BadStatusLine) as e:
      last_e = str(e)
      sleep_secs = (2 ** tries) * initial_seconds
      print 'error, sleeping %s secs' % sleep_secs
      sys.stdout.flush()
      time.sleep(sleep_secs)
      tries += 1
  raise ValueError('couldn\'t load %s: %s' % (url, last_e))


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
      '--cluster-size-envar', help='envar specifying how big the cluster is',
      default='KUBERNETES_ZK_CLUSTER_SIZE')
  parser.add_argument(
      '--dry-run', help='don\'t write anything.', action='store_true')
  parser.add_argument(
      '--template-name', help='template to use.', default='zoo_cfg.template')
  args = parser.parse_args()

  ctx = {
      'ips': {},
  }
  for envar, value in os.environ.iteritems():
    if envar.startswith(args.envar_prefix):
      ctx[envar] = value

  for i in range(int(os.environ[args.cluster_size_envar])):
    print 'tryin server %d' % i
    ctx['ips']['zoo%d' % i] = exponential_backoff(
        'http://' + os.environ['ZOO%d_SERVICE_HOST' % i] + ':9999/hostname',
        1,
        8
    )

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
