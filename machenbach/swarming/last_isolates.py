#!/usr/bin/env python

import json
from multiprocessing.dummy import Pool
import os
import subprocess
import sys

# Example - get the isolates from the last 200 tasks on bot vm92-m4:
# ./last_isolates.py path/to/luci-py/client vm92-m4 200
#
# Prints a json list with the isolates ordered newest->oldest.
assert len(sys.argv) == 4

SWARMING = os.path.join(sys.argv[1], 'swarming.py')
assert os.path.exists(SWARMING)

args = [
  sys.executable,
  SWARMING, 'query',
  '-S', 'https://chromium-swarm.appspot.com',
  '--limit', '%s' % sys.argv[3],
  'bot/%s/tasks' % sys.argv[2],
]

result = subprocess.check_output(args)

task_ids = [
  item['task_id'] for item in json.loads(result)['items']
  # Ignore deduped idempotent tasks (they don't interfere with the cache).
  if not item.get('deduped_from')
]

def get_task_request(task_id):
  args = [
    sys.executable,
    SWARMING, 'query',
    '-S', 'https://chromium-swarm.appspot.com',
    'task/%s/request' % task_id,
  ]
  return json.loads(subprocess.check_output(args))

pool = Pool(48)
requests = pool.map(get_task_request, task_ids)
pool.close()

isolates = []
for request in requests:
  if not request['properties'].get('inputs_ref'):
    continue
  isolates.append(request['properties']['inputs_ref']['isolated'])

print json.dumps(isolates, indent=2)

