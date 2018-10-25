import json
import urllib2

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
