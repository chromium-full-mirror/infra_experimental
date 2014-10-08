#!/usr/bin/env python

import json
import urllib2

if __name__ == '__main__':
  counter = 1
  for failure in json.load(urllib2.urlopen('http://chromium-cq-status.appspot.com/query/action=verifier_fail/verifier=simple%20try%20job'))['results']:
    passes = json.load(urllib2.urlopen('http://chromium-cq-status.appspot.com/query/action=verifier_pass/verifier=simple%%20try%%20job/issue=%d/patchset=%d' % (failure['fields']['issue'], failure['fields']['patchset'])))
    if passes['results']:
      print '#%d: https://chromium-cq-status.appspot.com/patch-status/%d/%d' % (counter, failure['fields']['issue'], failure['fields']['patchset'])
      counter += 1

      for abort in json.load(urllib2.urlopen('http://chromium-cq-status.appspot.com/query/verification=abort/issue=%d/patchset=%d' % (failure['fields']['issue'], failure['fields']['patchset'])))['results']:
        msg = abort['fields']['payload']['output']
        if msg != 'CQ bit was unchecked on CL. Ignoring.':
          print '\t%s' % abort['fields']['payload']['output']
