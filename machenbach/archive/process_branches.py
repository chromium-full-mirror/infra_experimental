import json
import re
import subprocess
import sys

# 1) User who executes this should add themselves first to v8-autoroll or give
# themselves force push or delete ref access for refs/heads/*.
#
# 2) Download +refs.txt at:
# https://chromium.googlesource.com/v8/v8/+refs?format=text
#
# 3) Choose which refs to archive. Don't archive the current milestone. E.g.
# if current is 8.4, choose a regexp for archiving older branches, e.g.
# [5-7]\\.\\d+\\.\\d+ and then 8\\.[0-3]\\.\\d+
#
# 4) For each regexp call:
# python process_branches.py path/to/v8 path/to/+refs.txt regexp

assert len(sys.argv) > 3

v8_dir = sys.argv[1]
refs_file = sys.argv[2]

RE = re.compile('^refs/heads/(%s)$' % sys.argv[3])

with open(refs_file) as f:
  data = f.read()

work_refs = []
for line in data.splitlines():
  hsh, ref = line.split(' ')
  match = RE.match(ref)
  if match:
    work_refs.append(match.group(1))


def process(refs):
  if not refs:
    return
  head = refs[:10]

  cmd = 'python archive_branches.py %s %s' % (v8_dir, ' '.join(head))
  print(cmd)
  subprocess.check_call(cmd, shell=True)
  process(refs[10:])


process(sorted(work_refs))