#!/usr/bin/env python

import argparse
import ast
import hashlib
import sqlite3
import subprocess
import os

FILE_DIR = os.path.dirname(__file__)

TYPE_TO_TUP = {
    'n1-standard-8': (8, 30),
    'n1-standard-4': (4, 15),
    'n1-highmem-8': (8, 52),
    'n1-highcpu-8': (8, 7.2),
    'n1-standard-64': (64, 240),
    'custom-cpu-8-mem-17': (8, 17),
    'custom-cpu-8-mem-20': (8, 20),
}

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--dir', default='results')
  parser.add_argument('-n', '--no-fetch', action='store_true')

  args = parser.parse_args()
  if not args.no_fetch:
    subprocess.check_call(['gsutil', '-m', 'cp', 'gs://martiniss-compile-time-data/linux_chromium_rel_ng/results_run*', 'results'])
    subprocess.check_call(['gsutil', '-m', 'cp', 'gs://martiniss-compile-time-data/android_n5x_swarming_rel/results_run*', 'results'])

  files = os.listdir(os.path.join(FILE_DIR, args.dir))
  to_print = [f for f in files if 'results_run' in f]
  conn = sqlite3.connect(os.path.join(FILE_DIR, 'data.db'))
  s = 'INSERT INTO data VALUES (%s)' % ','.join(['?' for _ in range(11)])
  for fname in to_print:
    with open(os.path.join(args.dir, fname)) as f:
      contents = f.readlines()
    for begin in range(len(contents)/4):
      try:
        first_line = contents[begin*4+0]
        ninja_arr = ast.literal_eval(first_line.split('|')[0].split(':')[1].strip())
        builder = 'linux_chromium_rel_ng'
        if '|' in first_line: # we have a builder type
          builder = first_line.split('|')[1].strip()
          if builder.startswith('builder '):
            builder = builder.split(' ')[1]

        time = float(contents[begin*4+1].split(':')[1].strip())
        machine = contents[begin*4+2].split(':')[1].strip()
        inst_num = contents[begin*4+3].split(' ')[-1].strip()
        target = ninja_arr[-1]
        full_inst = fname.split('-')[1]
        run = fname.split('-')[-1]
      except ValueError:
        print 'bad file', fname
        continue

      if len(ninja_arr) == 1:
        continue

      data = [
          int(ninja_arr[1]),
          builder,
          target] + list(TYPE_TO_TUP[machine]) + [
          200, # Not read from file right now
          full_inst,
          int(run),
          int(inst_num),
          time,
      ]
      data.insert(
          0, hashlib.sha1(
              ','.join([str(x) for x in data[:-2] + [data[-1]]])).hexdigest())
      try:
        conn.execute(s, data)
      except sqlite3.IntegrityError:
        pass

  conn.commit()


if __name__ == '__main__':
  main()
