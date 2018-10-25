from get_commit_message import *
from get_bug_ids import *

COMMIT_IDS = ['fa4fdf56608b32896cd7dd733ad623e7474a9f1c']

if __name__ == '__main__':
  for commit_id in COMMIT_IDS:
    msg = get_commit_message(commit_id)
    bug_ids = get_bug_ids(msg)
    for bug_id in bug_ids:
      print 'updating bug %s with commit %s:' % (bug_id, commit_id)
      print msg
