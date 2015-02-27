import argparse
import json
import pingdomlib
import sys
from urlparse import urlparse


def lstrip(string, strip):
  if string.startswith(strip):
    return string[len(strip):]
  return string


def main():
  parser = argparse.ArgumentParser(description='Interact with the pingdom api.')
  parser.add_argument('--cred-file', default='.pingdom_creds.json',
                      help='location of credentials file for pingdom.')
  parser.add_argument('--mastermap-file', default='mastermap.json',
                      help='location of mastermap json')
  parser.add_argument('--master-check-template',
                      default='%(master_dir)s accepting builds',
                      help='template to generate master check names')
  parser.add_argument('--check-url',
                      default='json/accepting_builds',
                      help='url endpoint to hit')
  parser.add_argument('--contains',
                      default='"accepting_builds":true',
                      help='check requires this string to be present')
  args = parser.parse_args()
  with open(args.cred_file) as f:
    creds = json.load(f)
  with open(args.mastermap_file) as f:
    masters = json.load(f)

  masters_to_process = [
      x for x in masters
      if not x['internal']
      and x['host'] != 'localhost']

  api = pingdomlib.Pingdom(
      creds['username'],
      creds['password'],
      creds['apikey'])
  pingdomchecks = dict((x.name, x) for x in api.getChecks())

  for master in masters_to_process:
    url_parts = urlparse(master['buildbot_url'] + args.check_url)
    name = args.master_check_template % {
        'master_dir': lstrip(master['dirname'], 'master.'),
    }

    print name
    if name in pingdomchecks:
      pingdomchecks[name].url = url_parts.path
      pingdomchecks[name].encryption = True
      pingdomchecks[name].host = url_parts.hostname
      pingdomchecks[name].shouldcontain = args.contains
    else:
      api.newCheck(name, url_parts.hostname, resolution=1, encryption=True,
                   url=url_parts.path, shouldcontain=args.contains)


if __name__ == '__main__':
  sys.exit(main())
