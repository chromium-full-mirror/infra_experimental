#!/usr/bin/env python

import os
import re
import subprocess
import sys
import time

"""Script to archive heads under ignore/foo.

This adds the refs passed to the script as parents to ignore/foo and on
success deletes them.

Assumes push merge access to ignore/foo and force push access to the branches.

Assumes a workdir checkout with all required refs fetched.

archive_branches.py path/to/checkout ref1 [ref2 ...]
"""


assert len(sys.argv) > 1


def git(*args, **kwargs):
  stdin_data = None
  stdin_handle = None
  if kwargs.get('stdin'):
    stdin_data = kwargs.pop('stdin')
    stdin_handle = subprocess.PIPE
  proc = subprocess.Popen(('git',) + args,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          stdin=stdin_handle,
                          **kwargs)
  output, _ = proc.communicate(stdin_data)
  assert proc.returncode == 0, output.strip()
  return output.strip()


def synthesize(refs):
  commits = []
  for ref in refs:
    ref = ref if ref == 'FETCH_HEAD' else 'refs/remotes/origin/' + ref
    commits.append(git('rev-parse', ref))

  name = git('config', 'user.name')
  email = git('config', 'user.email')

  # Hardcoded the tree object of the ignore/foo README file.
  data = ['tree c9c91bce52cd3003b6a9b0b4ae29d46210c40d51']
  for commit in commits:
    data.append('parent %s' % commit)

  timestamp = int(time.time())
  data.append('author %s <%s> %s +0000' % (name, email, timestamp))
  data.append('committer %s <%s> %s +0000' % (name, email, timestamp))
  data.append('')

  # We don't really care about the commit message.
  data.append('Placeholder commit\n')
  data.append('Refs merged:\n' + '\n  '.join(refs) + '\n')

  return git('hash-object', '-t', 'commit', '-w', '--stdin',
             stdin='\n'.join(data))


assert os.path.exists(sys.argv[1])
os.chdir(sys.argv[1])

refs = sys.argv[2:]
assert refs, 'Provide at least one ref'

# Make sure we only archive roll branches.
for ref in refs:
  assert re.match(r'\d*\.\d*\.\d*', ref)

# Print what we're doning.
print 'archive_branches.py ' + ' '.join(sys.argv[1:])

# Merge into ignore/foo.
git('fetch', 'origin', 'refs/heads/ignore/foo')
merge = synthesize(['FETCH_HEAD'] + refs)
git('push', 'origin', '%s:refs/heads/ignore/foo' % merge)

# Delete refs.
del_specs = (
    ['push', 'origin'] +
    [':refs/heads/%s' % ref for ref in refs]
)
git(*del_specs)
