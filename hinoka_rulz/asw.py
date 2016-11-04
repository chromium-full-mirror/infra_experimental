#!/usr/bin/python

import csv
import urllib2
import os
import base64
import sys
import json
from oauth2client.service_account import ServiceAccountCredentials
import os
import sys
import re

sa_file = os.path.expanduser('~/.service-account-ccompute.json')
scopes = ['https://www.googleapis.com/auth/userinfo.email']
url_tmpl = 'https://1220-c4cc5b1-tainted-hinoka-dot-luci-milo.appspot.com/prpc/%s/%s'
credentials = None
if os.path.exists(sa_file):
  credentials = ServiceAccountCredentials.from_json_keyfile_name(
      sa_file, scopes=scopes)


HEADER = '\033[95m'
OKBLUE = '\033[94m'
OKGREEN = '\033[92m'
WARNING = '\033[93m'
FAIL = '\033[91m'
ENDC = '\033[0m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'


def get(service, endpoint, **kwargs):
  url = url_tmpl % (service, endpoint)
  body = json.dumps(kwargs)
  headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
  }
  if credentials:
    access_token = credentials.get_access_token()
    headers['Authorization'] = 'Bearer %s' % access_token.access_token
  r = urllib2.Request(url, body, headers)
  u = urllib2.urlopen(r, timeout=60)
  u.read(4)  # Remove the jsonp header
  return json.load(u)


android_steps = ['List adb devices', 'device_status', 'provision_devices']
def is_android(builds, device_db):
  for build in builds:
    slave = build['slave']
    if slave in device_db:
      devices = device_db[slave]
      if devices:
        return True
    for step in build['steps']:
      if step['name'] in android_steps:
        return True
  return False


def is_swarming(builds):
  for build in builds:
    for step in build['steps']:
      if re.match(r'\[trigger\] .* on Android', step['name']):
        return True
  return False


def analyze(builds, device_db):
  return {
    'is_android': is_android(builds, device_db),
    'is_swarming': is_swarming(builds),
  }


def get_devices(device_db):
  """Given the output from: go/vbast

  Returns a map of host -> list of devices
  """
  result = {}
  with open(device_db, 'rb') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
      host = row['hostname']
      device = row['metric:device_id']
      if host not in result:
        result[host] = []
      result[host].append(device)
  return result


masters = ['chromium.linux', 'chromium.android']
def main(args):
  devices = {}
  if args:
    devices = get_devices(args[0])
  needs_work = 0
  done = 0
  free_device = 0
  all_buckets = get('milo.Milo', 'GetAllBuckets')
  for bucket in all_buckets['buckets']:
    if bucket['bucket'] not in masters:
      continue
    print '%s: %s' % (bucket['module'], bucket['bucket'])
    for builder in bucket['builders']:
      b_info = get(
          'milo.Buildbot', 'GetBuildbotBuildsJSON', master=bucket['bucket'],
          builder=builder, limit=25)
      builds = [
          json.loads(base64.b64decode(b['data'])) for b in b_info['builds']]
      data = analyze(builds, devices)
      header = ''
      marking = ['']
      if data['is_android']:
        marking.append('[Device]')
        header = FAIL
      if data['is_swarming']:
        marking.append('[Swarming]')
        if header:
          header = WARNING
        else:
          header = OKGREEN
      print '\t%s%s%s%s' % (header, builder, ' '.join(marking), ENDC)
      if header == OKGREEN:
        done += 1
      elif header == WARNING:
        free_device += 1
      elif header == FAIL:
        needs_work += 1

  # Print completion stats.
  print 'Out of %d masters:' % len(masters)
  print 'Completed: %d' % done
  print 'Needs work: %d' % needs_work
  print 'Free Devices: %d' % free_device
  print 'Completion: %d%%' % ( 100 * (done + free_device) / (done + needs_work + free_device) )


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
