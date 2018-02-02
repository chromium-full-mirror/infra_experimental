#!/usr/bin/env python

import argparse
import subprocess
import sys

from docker import find_master

PROJECT = "martiniss-test-compile-time"
URL = "gcr.io/%s/%s"

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('-j', default='50')
  parser.add_argument('--builder', default='linux_chromium_rel_ng')

  args = parser.parse_args()
  master = find_master.get_master(args.builder)[0]

  proc = subprocess.Popen(
      ['docker', 'build', '--build-arg', 'MASTER=%s' % master, '--build-arg',
       'BUILDER=%s' % args.builder, 'docker', '-q'],
      stdout=subprocess.PIPE)
  proc.wait()
  digest = proc.stdout.read().strip()
  print digest
  url = URL % (PROJECT, args.builder)

  subprocess.check_call(['docker', 'tag', digest, url])
  subprocess.check_call(['gcloud', 'docker', '--', 'push', url])


if __name__ == '__main__':
  main()
