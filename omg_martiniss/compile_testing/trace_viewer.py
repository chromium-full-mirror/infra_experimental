#!/usr/bin/env python

import argparse
import subprocess
import os

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('instance')
  parser.add_argument('machine_type')
  parser.add_argument('run')
  args = parser.parse_args()

  with open(os.path.join('results', 'results_ninja_log_run-%s-%s-%s' % (
      args.instance, args.machine_type, args.run))) as full_log:
    all_lines = full_log.readlines()

  first_sect_end = 0
  while 'run number' not in all_lines[first_sect_end]:
    first_sect_end += 1

  new_fname = os.path.join('results', 'results_ninja_log_run-%s-%s-%s_0' % (
      args.instance, args.machine_type, args.run))
  print new_fname
  with open(new_fname, 'w') as log_to_write:
    log_to_write.writelines(all_lines[:first_sect_end])

  tmp_loc = os.path.expanduser('~/src/infra/appengine/chromium_build_stats/default/tmpl/trace-viewer.html')
  subprocess.call(['./ninja_log_trace_viewer', '-filename', new_fname, '-port', '12345', '-trace_viewer_tmpl', tmp_loc])

if __name__ == '__main__':
  main()
