#!/usr/bin/env python

"""This script runs 1 minute worth of load tests.

It is meant to be run from a cron job every minute.
"""

import json
import httplib2
import logging
import multiprocessing
import os
import random
import sys
import urllib2
import threading
import time

import googleapiclient.http
from oauth2client.client import GoogleCredentials

ENDPOINT_TO_TEST = 'https://chrome-infra-mon-proxy.appspot.com/monacq'
AUTHORIZE = True
METHOD = 'POST'
CREDENTIALS = '.loadtest_credentials.json'
SCOPES = 'https://www.googleapis.com/auth/userinfo.email'
QPS_URL = 'https://chrome-infra-loadtest.appspot.com/loadtest/'
PAYLOAD_SIZE = 6000 # In bytes.
PAYLOAD_TIMEOUT = 10 # In seconds.


class LoadTest(object):
  def __init__(self):
    self.qps = 0
    self.payload = ''
    self.credentials = GoogleCredentials.from_stream(CREDENTIALS)
    self.credentials = self.credentials.create_scoped(SCOPES)
    self.http = httplib2.Http()
    self.authorize()

  def authorize(self):
    if AUTHORIZE:
      self.http = self.credentials.authorize(self.http)

  def refresh_token(self):
    if AUTHORIZE and self.credentials.access_token_expired:
      print 'Refreshing oauth2 token'
      self.authorize()

  def update_qps(self):
    response = urllib2.urlopen(QPS_URL, timeout=15)
    data = json.loads(response.read())
    self.qps = data.get('qps', 0)
    payload_size = data.get('payload_size', PAYLOAD_SIZE)
    self.payload = ''.join(
        chr(random.randint(0, 255)) for i in xrange(payload_size))
    self.refresh_token()

  def send_one_request(self):
    url = ENDPOINT_TO_TEST
    headers = {
        'content-length': str(len(self.payload)),
        'content-type': 'application/x-protobuf',
    }
    def callback(_response, _content):
      pass
    if METHOD == 'POST':
      request = googleapiclient.http.HttpRequest(
          self.http, callback, url, method=METHOD,
          body=self.payload,
          headers=headers)
    else:
      request = googleapiclient.http.HttpRequest(
          self.http, callback, url, method=METHOD, headers={})
    request.execute()

  def send_n_requests(self, n):
    """Spawn ``n`` parallel processes each sending a single request."""
    procs = [
        multiprocessing.Process(
            # pylint: disable=unnecessary-lambda
            target=lambda: self.send_one_request(),
            args=[],
            name='run %d' % n,
        ) for n in xrange(n)]
    for p in procs:
      p.daemon = True
      p.start()
    for p in procs:
      p.join(timeout=PAYLOAD_TIMEOUT)
    # Clear runaway processes.
    for p in procs:
      if p.is_alive():
        p.terminate()


def main():
  # Run 1 minute worth of load test.
  lt = LoadTest()
  lt.update_qps()
  if not lt.qps:
    return 0
  for _ in xrange(60):
    time_start = time.time()
    # Send lt.qps number of requests every second, asynchronously.
    proc = threading.Thread(
        target=lambda: lt.send_n_requests(lt.qps),
        args=[],
        name='queue %d' % time_start)
    proc.start()
    time.sleep(1.0)


if __name__ == '__main__':
  sys.exit(main())
