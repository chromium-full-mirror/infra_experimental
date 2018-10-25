import re

BUG_ID_RE = re.compile(
    r'^(Bug:|BUG=)\s*(?P<bugs>[0-9,]+)',
    re.MULTILINE
)

TEST_COMMIT_MESSAGE="""
Implement a bunch of micro-optimisations in package_index.

Together, these changes speed up runs on Windows by XX% and Linux by XX%.

Bug: 873956,12345
Change-Id: I8c99177dfe5f3c463aba3ea5a7372ad50fdf8371
"""

def get_bug_ids(commit_message):
  """Extracts bug IDs from a commit message string."""
  match = BUG_ID_RE.search(commit_message)
  if match is None:
    return []
  groupdict = match.groupdict()
  bugs = groupdict['bugs']
  return map(int,bugs.split(','))

if __name__ == '__main__':
  print get_bug_ids(TEST_COMMIT_MESSAGE)
