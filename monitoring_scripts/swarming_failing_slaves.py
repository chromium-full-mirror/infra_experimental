#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Collect stats about failing bots on swarming.

Assumes swarming.py is in your shell PATH. To get your copy:
  git clone https://code.google.com/p/swarming/
"""

import argparse
import json
import logging
from multiprocessing.pool import ThreadPool
import subprocess
import sys


SWARMING_URL = 'https://chromium-swarm.appspot.com'
SWARMING_CMD = 'swarming.py'
AUTH_CMD = 'auth.py'


def get_args():
  parser = argparse.ArgumentParser(__doc__)
  parser.add_argument(
    "--task-count", default=10, type=int,
    help=('Number of tasks per bot to retrieve. '
          'Failure rate is averaged over this number.'))
  parser.add_argument(
    "--top", default=20, type=int,
    help=('Number of top failing bots to print'))
  parser.add_argument(
      '-v', '--verbose', default=False, action='store_true',
      help='Enables debugging log messages.')
  return parser.parse_args()


def auth():
  """Authenticate to swarming server."""
  cmd = [AUTH_CMD, 'login', '--service', SWARMING_URL]
  logging.debug('auth(): executing %s', ', '.join(cmd))
  return_code = subprocess.call(cmd)
  return return_code == 0


def swarming_query(*args):
  cmd = [SWARMING_CMD, 'query']
  cmd += [str(arg) for arg in args]
  cmd += ['-S', SWARMING_URL]
  logging.debug('swarming_query(%s)', ', '.join(cmd))
  attempt = 0
  for attempt in range(2):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    output = p.stdout.read()
    return_code = p.wait()
    if not return_code:
      break
    auth()
  if return_code:
    return {'error': '%r return with code %d' % (cmd, return_code),
            'output': output}
  try:
    result = json.loads(output)
  except Exception as e:
    return {'error': 'Cannot decode JSON: %s' % e,
            'output': output}
  return result


def bot_stats(tasks):
  num_tasks = len(tasks)
  stats = {
      'tasks': tasks,
      'tasks_count': num_tasks,
      'failure_count': len([t for t in tasks if t.get('failure')]),
      'internal_failure_count': len(
          [t for t in tasks if t.get('internal_failure')]),
      'failure_rate': 0.0,
      'internal_failure_rate': 0.0,
  }
  if num_tasks:
    stats['failure_rate'] = 1.0 * stats['failure_count'] / num_tasks
    stats['internal_failure_rate'] = (
        1.0 * stats['internal_failure_count'] / num_tasks)
  return stats


def process_bot(args, bot):
  if 'id' not in bot:
    logging.error('Bot without ID: %r: ', bot)
    return None, None
  bot_id = bot['id']
  tasks_json = swarming_query(
      'bot/%s/tasks' % bot_id, '--limit', args.task_count)
  if 'error' in tasks_json:
    logging.error('Failed to fetch tasks for %s: %s', bot_id, tasks_json)
    return None, None
  tasks = tasks_json.get('items', [])
  return bot_id, bot_stats(tasks)


def collect_stats(args):
  bots_json = swarming_query('bots', '--limit', '10000')
  if 'error' in bots_json:
    return bots_json
  bots = bots_json.get('items', [])
  stats = {
      'bots_count': len(bots),
      'bots': {},
  }
  logging.info('Found %d bots; collecting tasks.', stats['bots_count'])
  pool = ThreadPool(100)
  count = 0

  def func(bot):
    return process_bot(args, bot)

  try:
    for bot_id, bot_results in pool.imap_unordered(func, bots):
      count += 1
      stats['bots'][bot_id] = bot_results
      logging.info('%4d of %4d (%2.0f%%) of bots processed',
                   count, stats['bots_count'],
                   count * 100 / stats['bots_count'])
  except KeyboardInterrupt as e:
    pass
  return stats


def print_stats(args, stats):
  if 'error' in stats:
    logging.error('ERROR: %s', stats['error'])
    if 'output' in stats:
      logging.debug('ERROR: swarming.py raw output:\n%s', stats['output'])
    return
  top_failures = sorted(
      stats['bots'].iterkeys(),
      reverse=True,
      key = lambda k: stats['bots'][k]['failure_rate'])
  top_internal_failures = sorted(
      stats['bots'].iterkeys(),
      reverse=True,
      key = lambda k: stats['bots'][k]['internal_failure_rate'])
  print
  print 'Top %d failing bots:' % args.top
  for bot_id in top_failures[:args.top]:
    bot_stats = stats['bots'][bot_id]
    print('  %s failed %d (%3.1f%%), internal failures %d (%3.1f%%) '
          'of %d tasks' % (
        bot_id, bot_stats['failure_count'],
        100.0 * bot_stats['failure_rate'],
        bot_stats['internal_failure_count'],
        100.0 * bot_stats['internal_failure_rate'],
        bot_stats['tasks_count']))
  print
  print 'Top %d internally failing bots:' % args.top
  for bot_id in top_internal_failures[:args.top]:
    bot_stats = stats['bots'][bot_id]
    print('  %s failed %d (%3.1f%%), internal failures %d (%3.1f%%) '
          'of %d tasks' % (
        bot_id, bot_stats['failure_count'],
        100.0 * bot_stats['failure_rate'],
        bot_stats['internal_failure_count'],
        100.0 * bot_stats['internal_failure_rate'],
        bot_stats['tasks_count']))


def main():
  args = get_args()
  logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARN)
  stats = collect_stats(args)
  print_stats(args, stats)


if __name__ == '__main__':
  sys.exit(main())
