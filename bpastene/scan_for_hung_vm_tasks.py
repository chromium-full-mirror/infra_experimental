import argparse
import datetime
import os
import json
import subprocess
import sys
import tempfile

import smtplib
from email.mime.text import MIMEText


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('path_to_swarming_dot_py')
  parser.add_argument('--dry-run', help='Won\'t send an email.', action='store_true')
  args = parser.parse_args()

  assert os.path.exists(args.path_to_swarming_dot_py), 'Can\'t find swarming.py'
  swarming_args = [
    args.path_to_swarming_dot_py,
    'query',
    '-S',
    'chromium-swarm.appspot.com',
    'tasks/list?state=RUNNING&tags=pool:Chrome-CrOS-VM',
  ]
  out = subprocess.check_output(swarming_args)
  d = json.loads(out)
  now = datetime.datetime.strptime(d['now'], '%Y-%m-%dT%H:%M:%S.%f')
  if not d.get('items', []):
    print 'no currently running tasks'
    return 0
  else:
    print 'total currently running tasks:'
    print len(d['items'])
    print

  borked_tasks = []
  for task in d['items']:
    name = None
    for tag in task['tags']:
      if tag.startswith('name:'):
        name = tag.split(':')[1]
    duration = now - datetime.datetime.strptime(task['started_ts'], '%Y-%m-%dT%H:%M:%S.%f')
    duration_s = duration.seconds
    if name == 'cros_vm_sanity_test' and duration_s >= 300:
      borked_tasks.append((name, duration_s, task['task_id']))
    elif name == 'telemetry_perf_unittests' and duration_s >= 300:
      borked_tasks.append((name, duration_s, task['task_id']))

  if borked_tasks and args.dry_run:
    print 'found %d hung tasks, skipping email' % len(borked_tasks) 
  elif borked_tasks and not args.dry_run:
    print 'found %d hung tasks, sending email...' % len(borked_tasks)
    msg = '<html><body>'
    msg += 'The following tasks are possibly hung:<br/><br/>'
    for name, duration, task_id in borked_tasks:
      task_link = '<a href="https://chromium-swarm.appspot.com/task?id=%s">%s</a>' % (task_id, task_id)
      msg += '%s: %s running for %.2fm<br/>' % (task_link, name, duration/60.0)
    msg += '</body></html>'

    tmp_file = tempfile.NamedTemporaryFile(delete=False)
    tmp_file.write(msg)
    tmp_file.close()
    print 'wrote html to %s' % tmp_file.name

    with open(os.devnull, 'w') as null:
      email_args = [
        'sendgmr',
        '--subject=Potentially hung CrOS VM Tests',
        '--html_file=%s' % tmp_file.name,
        '--body_file=/dev/null',
        '--to=unlucky-engineers',
      ]
      subprocess.check_call(email_args, stdin=null)

    os.unlink(tmp_file.name)
  else:
    print 'no borked tasks found, exitting'


if __name__ == '__main__':
  sys.exit(main())
