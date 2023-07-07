# Copyright 2023 the V8 project authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Script to ensure the number of tests run on one CL is the same as another.
Used to monitor risky V8 test-framework changes.

Currently doesn't support different trybot runs. They need to be exactly
equal. E.g. all opt-in trybots of one CL need to run on the other.
None of the builds should be repeated.

Usage: Change SWARMING_TOOL (luci-go exe), CL1 and CL2 below.
"""

import json
import re
import subprocess

class SkipStuffException(Exception):
  pass

SWARMING_TOOL = '/home/machenbach/baz/swarming'

CL1 = 'https://chromium-review.googlesource.com/c/4538761/37'
CL2 = 'https://chromium-review.googlesource.com/c/4642630/2'

UNINTERESTING_TASK_PREFIXES = [
  'GCMole',
  'Bytecode-Baseline',
  'JSTests',
  'Num',
  'Static-Initializers',
  'Unittests',
]

TASK_RE = re.compile(r'.*:(\d+):(\d+)')
TAG_RE = re.compile(r'([^:]*):(.*)')
TESTS_RUN_RE = re.compile(r'>>> (\d+) tests ran')

GET_TASKS_COMMAND = f'{SWARMING_TOOL} tasks -S chromium-swarm.appspot.com -limit 500 -tag gerrit:%s'
COLLECT_COMMAND = f'{SWARMING_TOOL} collect -S chromium-swarm.appspot.com -quiet -task-output-stdout console %s'

def load_tasks_json(cl):
  output = subprocess.check_output(
      GET_TASKS_COMMAND % cl, shell=True).decode('utf-8').strip()
  return json.loads(output)

def get_n_tests(task_id):
  output = subprocess.check_output(
      COLLECT_COMMAND % task_id, shell=True).decode('utf-8')
  match = TESTS_RUN_RE.search(output)
  assert match, f'Task {task_id} did not match tests regexp.'
  return int(match.group(1))

def tags_dict(tags):
  result = {}
  for tag in tags:
    match = TAG_RE.match(tag)
    assert match
    result[match.group(1)] = match.group(2)
  return result

def get_task_ids(data):
  tasks = {}

  for task in data:
    try:
      match = TASK_RE.match(task['name'])
      if match:
        shard_num = match.group(1)
        shard_count = match.group(2)
      else:
        shard_num = 0
        shard_count = 1
      tags = tags_dict(task['tags'])
      name = tags['name']
      for prefix in UNINTERESTING_TASK_PREFIXES:
        if name.startswith(prefix):
          raise SkipStuffException()

      spec = tags['spec_name']
      step = tags['stepname']
      uid = f'{spec} {step} {shard_num}'
      assert uid not in tasks, 'Something ran twice... use a fresh patchset?'
      tasks[uid] = task['task_id']
    except SkipStuffException:
      pass

  return tasks

data1 = load_tasks_json(CL1)
tasks1 = get_task_ids(data1)

data2 = load_tasks_json(CL2)
tasks2 = get_task_ids(data2)

assert len(tasks1) <= 499, 'Too many tasks, need higher limit in swarming command'

if len(tasks1) != len(tasks2) or set(tasks1.keys()) != set(tasks2.keys()):
  print(f'One CL ran more tasks than the other, {len(tasks1)} != {len(tasks2)}')
  keys_in1 = set(tasks1.keys()) - set(tasks2.keys())
  keys_in2 = set(tasks2.keys()) - set(tasks1.keys())
  keys_in_both = set(tasks1.keys()) & set(tasks2.keys())
  print(f'Keys in 1 but not in 2: {keys_in1}')
  print(f'Keys in 2 but not in 1: {keys_in2}')
  print(f'Keys in both: {keys_in_both}')
  assert False

expected_total = len(tasks1)
n_tasks = 0
n_tests = 0

for uid, task_id1 in tasks1.items():
  task_id2 = tasks2[uid]
  n_tests1 = get_n_tests(task_id1)
  n_tests2 = get_n_tests(task_id2)
  assert n_tests1 == n_tests2, (
    f'Tasks {task_id1} and {task_id2} ran different tests {n_tests1} != {n_tests2}'
  )
  n_tasks += 1
  n_tests += n_tests1
  if n_tasks % 5 == 0:
    print(f'Done verifying {n_tasks} tasks ({int(n_tasks / expected_total * 100)}%).')

print(f'Verified {n_tasks} tasks running {n_tests} tests in total.')
