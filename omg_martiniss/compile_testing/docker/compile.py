#!/usr/bin/env python

import argparse
import shutil
import subprocess
import os
import sys
import time

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--builder', default='linux_chromium_rel_ng')
  args, rest = parser.parse_known_args()
  subprocess.check_call(['/goma/goma/goma_ctl.py', 'ensure_start'])

  # Disable goma cache so we have repeatable results. It's much slower using
  # this.
  # os.environ['GOMA_STORE_ONLY'] = 'true'

  rev = subprocess.check_output(['git', 'rev-parse', 'HEAD'])

  lines = []
  goma_cache = os.environ['GOMA_STORE_ONLY'] != 'true'
  lines.append(
      'ninja args: %s| builder %s | revision %s | goma_cache %s' % (
          rest, args.builder, rev, goma_cache))
  before = time.time()
  compile_args = ['ninja', '-C', 'out/Default'] + rest
  proc = subprocess.Popen(
      compile_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

  with open("/home/compile/stdout", "w") as log_file:
    while proc.poll() is None:
       line = proc.stdout.readline()
       if line:
          print line,
          log_file.write(line)

  done_compile = time.time()
  lines.append('clean compile time (seconds): %s\n' % (done_compile - before))
  with open('/home/compile/output', 'w') as f:
    f.writelines(lines)

  subprocess.check_call(['/goma/goma/goma_ctl.py', 'report'])
  shutil.move('/tmp/goma-report.tgz', '/home/compile')
  subprocess.check_call(['tar', 'xzf', '/home/compile/goma-report.tgz'])
  dirname = os.listdir('tmp')[0]
  shutil.move('tmp/%s/ninja_log' % dirname, '/home/compile')

if __name__ == '__main__':
  main()
