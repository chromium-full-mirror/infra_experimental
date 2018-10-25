from get_commit_message import *
from get_bug_ids import *
from monorail_client import *

COMMIT_IDS = ['fa4fdf56608b32896cd7dd733ad623e7474a9f1c']

if __name__ == '__main__':
  monorail_client = MonorailClient()
  for commit_id in COMMIT_IDS:
    # Testing
    msg = get_commit_message(commit_id, repo='infra/experimental')
    bug_ids = get_bug_ids(msg)
    for bug_id in bug_ids:
      print 'updating bug %s with commit %s:' % (bug_id, commit_id)
      print msg
      issue = Issue(bug_id, [])
      issue.set_comment(msg)
      monorail_client.update_issue('chromium', issue, send_email=False)
