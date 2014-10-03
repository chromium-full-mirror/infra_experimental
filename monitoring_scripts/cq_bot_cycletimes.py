# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import datetime
import functools
import math
import requests
import sys
import time
from optparse import OptionParser

# By jam@chromium.org.
# Inspired by https://github.com/eseidel/cycletimes/blob/master/bot_cycletimes.py

# TODO(sergeyberezin): can we use numpy.percentile instead?
# from http://code.activestate.com/recipes/511478-finding-the-percentile-of-the-values
def percentile(data, percent):
  if not data:
    return None
  k = (len(data) - 1) * percent
  f = math.floor(k)
  c = math.ceil(k)
  if f == c:
    return data[int(k)]
  d0 = data[int(f)] * (c - k)
  d1 = data[int(c)] * (k - f)
  return d0 + d1
    
median = functools.partial(percentile, percent=0.5)

def printrow(row, widths, indent=0):
  if indent:
    print ' ' * indent,
  for index, cell in enumerate(row):
    print str(cell).rjust(widths[index]),
  print
  
def elapsed(seconds):
  return str(datetime.timedelta(seconds=round(seconds)))
  
def stats_url_for_master(master_name, trybot_name):
  return ('https://chrome-infra-stats.appspot.com/_ah/api/stats/v1/steps/last/%s/%s/overall__build__result__/%d' % (master_name, trybot_name, options.count))

def print_bot_stats(master, builder, stats, widths):
  times = []
  for i in stats['step_records']:
    if i['result'] == '0':
      times.append(i['step_time'])
  times = sorted(times)
  printrow((builder, elapsed(median(times)), elapsed(percentile(times, 0.9)), len(times)), widths, indent=1)

parser = OptionParser()
parser.add_option("-c", "--count", dest="count", type="int", default=1000,
                  help="specify how many trybot runs to look at")
(options, args) = parser.parse_args()

def main(args):
  # data from https://chrome-internal.googlesource.com/infra/infra_internal/+/master/commit_queue/queue_config/chromium.json
  bots = [
  ['tryserver.chromium.win', ['win_chromium_rel_swarming', 'win_chromium_x64_rel_swarming', 'win8_chromium_rel', 'win_chromium_compile_dbg']],
  ['tryserver.chromium.mac', ['mac_chromium_rel_swarming', 'mac_chromium_compile_dbg', 'ios_dbg_simulator', 'ios_rel_device', 'ios_rel_device_ninja']],
  ['tryserver.chromium.linux', ['linux_chromium_rel_swarming', 'linux_chromium_chromeos_rel_swarming', 'linux_chromium_gn_rel', 'chromium_presubmit', 'android_dbg_tests_recipe', 'android_clang_dbg', 'android_aosp', 'android_chromium_gn_compile_rel']],
  ['tryserver.chromium.gpu', ['linux_gpu', 'linux_gpu_triggered_tests', 'mac_gpu', 'mac_gpu_retina_triggered_tests', 'mac_gpu_triggered_tests', 'win_gpu', 'win_gpu_triggered_tests']]
  ]
  
  widths = (40, 10, 10, 15)
  print (time.strftime("%m/%d %I:%M%p"))
  printrow(('master', 'median', '90th', 'success_count'), widths, indent=1)
  for master, builders in bots:
    for builder in builders:
      url = stats_url_for_master(master, builder)
      stats = requests.get(url).json()
      print_bot_stats(master, builder, stats, widths)
 
if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
