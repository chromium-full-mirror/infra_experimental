import json
import urllib2

TEST_COMMIT_HASH = '2930a5ac88799ddbe9dbc816ebcce49b3afb12f8'

def get_commit_message(commit_hash, host='chromium', repo='chromium/src'):
  """ Given a commit hash, a host, and a repo, returns the commit message for
      that commit within that repo (on googlesource.com)
  """
  url = 'https://%s.googlesource.com/%s/+show/%s?format=json' % (
      host, repo, commit_hash
  )
  response = urllib2.urlopen(url)

  # First 5 chars are )]}'\n
  json_doc = json.loads(response.read()[5:])

  return json_doc['message']

if __name__ == '__main__':
  print get_commit_message(TEST_COMMIT_HASH)
