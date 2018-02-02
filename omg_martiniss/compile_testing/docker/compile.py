#!/usr/bin/env python

import shutil
import subprocess
import os
import sys
import time

def main():
  num_parallel = int(sys.argv[1])
  subprocess.check_call(['/goma/goma/goma_ctl.py', 'ensure_start'])

  targets = ['all']
  #targets = ['browser_tests']
  #targets = ['unittests']
  # Disable goma cache so we have repeatable results. It's much slower using
  # this.
  os.environ['GOMA_STORE_ONLY'] = 'true'

  lines = []
  lines.append('built targets: %s\n' % ','.join(targets))
  lines.append('ninja args: %s\n' % num_parallel)
  before = time.time()
  proc = subprocess.Popen([
    'ninja', '-C', '/home/compile/chromium/src/out/Default', '-j',
    str(num_parallel)] + targets, stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT)

  with open("/home/compile/stdout", "w") as log_file:
    while proc.poll() is None:
       line = proc.stdout.readline()
       if line:
          print line
          log_file.write(line)

  done_compile = time.time()
  lines.append('clean compile time (seconds): %s\n' % (done_compile - before))
  with open('/home/compile/output', 'w') as f:
    f.writelines(lines)

  subprocess.check_call(['/goma/goma/goma_ctl.py', 'report'])
  shutil.move('/tmp/goma-report.tgz', '/home/compile')
  subprocess.check_call(['tar', 'xzf', 'goma-report.tgz'])
  dirname = os.listdir('/home/compile/tmp')[0]
  shutil.move('tmp/%s/ninja_log' % dirname, '/home/compile')

if __name__ == '__main__':
  main()
