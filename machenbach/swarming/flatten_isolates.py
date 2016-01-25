#!/usr/bin/env python

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import uuid

from multiprocessing.dummy import Pool

"""
Example - flattens all files from a list of isolated files:
./flatten_isolates.py path/to/luci-py/client last_200.json

Accepts the output of last_isolates.py as input file.
Prints a json list of lists for each task containing the files of that
task. Does not change the order of tasks. The files for each task
are in random order (and unique per task). Each file is represented
by a tuple (name, hash, size).

Example output:
[
  [ # task
    ("foo/bar", deadbeef, 12345), # file
    ...
  ],
  ...
]
"""

assert len(sys.argv) == 3

ISOLATESERVER = os.path.join(sys.argv[1], 'isolateserver.py')
assert os.path.exists(ISOLATESERVER)

work = tempfile.mkdtemp()

def flatten(hsh):
  # Download the isolated file provided by hsh.
  name = str(uuid.uuid1()) + hsh
  args = [
    sys.executable,
    ISOLATESERVER, 'download',
    '-I', 'https://isolateserver.appspot.com',
    '-f', hsh, name,
    '-t', work,
  ]
  subprocess.check_call(args)

  # Get file's content.
  with open(os.path.join(work, name)) as f:
    content = json.load(f)

  for f, v in content.get('files', {}).iteritems():
    yield f, v['h'], v['s']

  for i in content.get('includes', []):
    for f in flatten(i):
      yield f

def flattened(hsh):
  try:
    return list(flatten(hsh))
  except Exception as e:
    logging.exception('')
    return e

# Open input file containing a list of .isolated files.
with open(sys.argv[2]) as f:
  isolates = json.load(f)

pool = Pool(48)
results = pool.map(flattened, isolates)
pool.close()

tasks = []
for files_per_task in results:
  items = {}
  for name, hsh, size in files_per_task:
    # Dedupe files per task.
    items[hsh] = name, hsh, size
  tasks.append(items.values())

print json.dumps(tasks, indent=2)
shutil.rmtree(work)

