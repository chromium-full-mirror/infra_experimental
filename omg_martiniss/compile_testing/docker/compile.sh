#!/usr/bin/env python

import subprocess

def main():
  subprocess.check_call(['/goma/goma/goma_ctl.py', 'start'])
  subprocess.check_call(['ninja', '-C', '/home/compile/chromium/src/out/Default', 'unittests'])

if __name__ == '__main__':
  main()

#/goma/goma/goma_ctl.py start
#ninja -C 
