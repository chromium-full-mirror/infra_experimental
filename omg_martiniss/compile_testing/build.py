#!/usr/bin/env python

import argparse
import subprocess
import sys

from docker import find_master

PROJECT = "martiniss-test-compile-time"
URL = "gcr.io/%s/%s"

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--builder', default='linux_chromium_rel_ng')
  parser.add_argument('--tag', default=None)

  args = parser.parse_args()
  master = find_master.get_master(args.builder)[0]

  proc = subprocess.Popen(
      ['docker', 'build', '--build-arg', 'MASTER=%s' % master, '--build-arg',
       'BUILDER=%s' % args.builder, '-q', 'docker'],
      stdout=subprocess.PIPE)
  proc.wait()
  if proc.returncode:
    for l in proc.stdout.readlines():
      print l.strip()
    sys.exit(proc.returncode)
  digest = proc.stdout.read().strip()
  print digest
  url = URL % (PROJECT, args.builder)
  if args.tag is not None:
    url = '%s:%s' % (url, args.tag)

  subprocess.check_call(['docker', 'tag', digest, url])
  subprocess.check_call(['gcloud', 'docker', '--', 'push', url])


if __name__ == '__main__':
  main()
