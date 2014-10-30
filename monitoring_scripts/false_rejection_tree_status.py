#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Collect false rejected attemps and correlate with tree status."""

import argparse
import datetime
import json
import logging
from multiprocessing.pool import ThreadPool
import subprocess
import sys
import urllib2


BUILD_URL = ('https://chrome-build-extract.appspot.com/get_builds?'
             'num_builds=50&builder=%s&master=%s&day=%s&cursor=%s')

TRYSERVER_BUILDERS = [
    #'chromium.gpu:GPU Win Builder': 'tryserver.chromium.gpu:win_gpu',
    #'chromium.mac:Mac Builder': 'tryserver.chromium.mac:mac_chromium_rel_swarming',
    #'chromium.linux:Android Arm64 Builder (dbg)': 'tryserver.chromium.linux:android_arm64_dbg_recipe',
    'tryserver.chromium.mac:mac_chromium_compile_dbg'
]


def parse_args():
  parser = argparse.ArgumentParser(description=sys.modules['__main__'].__doc__)
  parser.add_argument(
      '-v', '--verbose', default=False, action='store_true',
      help='Enables debugging log messages.')
  parser.add_argument(
      '--date',
      help='Date of stats YYYY-MM-DD. Default: Now.')
  options = parser.parse_args()
  options.date = options.date or str(datetime.date.today())
  return options

def fetch_build(master, builder, day, rev_dict):
  """Fetch all builds for specified builder.

  Returns a dictionary with revision as key, and list of builds as value.
  """
  cursor = ''
  result = {}
  while True:
    url = BUILD_URL % (urllib2.quote(builder), urllib2.quote(master),
                       day, cursor)
    #print url
    logging.debug('Fetch builds from url %s.', url)
    data = json.load(urllib2.urlopen(url))
    for build in data['builds']:
      rev = _get_revision(build)
      if rev:
        result.setdefault(rev, [])
        rev_dict[rev] = build['times'][0]
        result[rev].append(parse_build(build))
    if data['cursor']:
      cursor = data['cursor']
    else:
      break
  return result

def parse_build(build):
  build_result = {}
  build_result['log_url'] = build['logs'][0]
  build_result['number'] = build['number']
  build_result['whitespace'] = True
  build_result['without_patch'] = False
  build_result['without_patch_succeed'] = True 
  build_result['succeed'] = (build['results'] == 0)
  for step in build['steps']:
    if 'compile' in step['name'] or 'test' in step['name']:
      build_result['whitespace'] = False
    if 'without patch' in step['name']:
      build_result['without_patch'] = True
      if step['results'][0] != 0:
        build_result['without_patch_succeed'] = False
  return build_result

def _get_revision(build):
  GOT_REVISION = 'got_revision'
  for prop in build['properties']:
    if prop[0] == GOT_REVISION:
      return prop[1]
  return None

def print_build_stats(tryserver, rev_list, build_result):
  for rev in rev_list:
    rev_res = []
    if rev in build_result:
      rev_res =  build_result[rev]
    else:
      logging.error('No builds found for revision %s.', rev)
      continue

    rev_res.sort(key=lambda x: int(x['number']))
    first_two = rev_res[:2]
    for res in rev_res:
      total_succeed_cnt = len([x for x in rev_res if x['succeed']])
      total_cnt = len(rev_res)
      wp_succeed_cnt = 0
      wp_total_cnt = 0
      with_patch_succeed_cnt = 0
      with_patch_total_cnt = 0
      wo_patch_succeed_cnt = 0
      wo_patch_total_cnt = 0
      wo_patch_step_succeed_cnt = 0
      wo_patch_step_fail_cnt = 0
      if res['whitespace']:
        wp_total_cnt += 1
        if res['succeed']:
          wp_succeed_cnt += 1
      # Only compile/test with patch
      elif not res['without_patch']:
        with_patch_total_cnt += 1
        if res['succeed']:
          with_patch_succeed_cnt += 1
      else:
        wo_patch_total_cnt += 1
        if res['succeed']:
          wo_patch_succeed_cnt += 1
        if not res['without_patch_succeed']:
          wo_patch_step_fail_cnt += 1
        else:
          wo_patch_step_succeed_cnt += 1
    print ('%s    %d/%d             %d/%d           %d/%d' % 
           (rev[:6], total_succeed_cnt, total_cnt,
            #total_succeed_cnt - wp_succeed_cnt, total_cnt - wp_total_cnt,
            len([x for x in first_two if x['succeed']]),len(first_two),
            wo_patch_step_succeed_cnt, wo_patch_step_succeed_cnt + wo_patch_step_fail_cnt
              ))


def main():
  args = parse_args()
  logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARN)
  day = args.date
  for tryserver in TRYSERVER_BUILDERS:
    rev_dict = {}
    ts_master, ts_builder = tryserver.split(':')
    ts_result = fetch_build(ts_master, ts_builder, day, rev_dict)
    rev_list = list(set(sorted(rev_dict.iterkeys(), key=lambda k: rev_dict[k])))
    print '\t Overall    First-Two    Without-Patch-Step'
    print_build_stats(tryserver, rev_list, ts_result)
  

if __name__ == '__main__':
  sys.exit(main())
