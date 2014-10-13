#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import sys
import urllib

"""Compares a waterfall and a corresponding tryserver builds.

Missing steps on the tryserver are reported.
"""

def main():
  if len(sys.argv) != 3:
    print 'Wrong number of arguments.'
    print 'Usage: python compare_builds.py [waterfall_url] [tryserver_url]'
    return

  def correct_url(url):
    if '/json/builders/' not in url:
      url = url.replace('/builders/', '/json/builders/')
    return url

  wf_url = correct_url(sys.argv[1])
  ts_url = correct_url(sys.argv[2])

  wf_json = json.load(urllib.urlopen(wf_url))
  ts_json = json.load(urllib.urlopen(ts_url))

  def cleanup(step_name):
    step_name = str(step_name)
    if step_name.startswith('[trigger] '):
      step_name = step_name[10:]
    if step_name.endswith(' (with patch)'):
      step_name = step_name[:-13]
    # Note: "(without patch)" is omitted on purpose. Even in case if they were
    # not identical to "(with patch)" steps, they do not validate the change
    # and thus do not guarantee that a test will pass on waterfall.
    return step_name

  wf_steps = [cleanup(step_name['name']) for step_name in wf_json['steps']]
  ts_steps = [cleanup(step_name['name']) for step_name in ts_json['steps']]

  print 'Missing steps on tryserver: %r' % list(set(wf_steps) - set(ts_steps))


if __name__ == '__main__':
  sys.exit(main())
