# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Crappy wrapper object around the CQ status endpoint

import pprint
import re

from CachingGet import CachingGet
from CqAttempt import CqAttempt

class ChromiumCqStatus:
    base_url = 'https://chromium-cq-status.appspot.com/query'
    caching_get = CachingGet(no_cache=False)
    pp1 = pprint.PrettyPrinter(depth=1, indent=2)
    pp2 = pprint.PrettyPrinter(depth=2, indent=2)
    pp3 = pprint.PrettyPrinter(depth=3, indent=2)

    def frames_into_attempts(self, frames):
        attempts = []
        curr_attempt = []
        for frame in sorted(frames, key=lambda x: x['fields']['timestamp']):
            if (not frame['fields'].has_key('action')):
                # self.pp2.pprint(frame['fields'])
                continue
            action = frame['fields']['action']
            if (action != 'patch_start' and len(curr_attempt)==0): continue
            curr_attempt.append(frame)
            if (action == 'patch_stop'):
                attempts.append(CqAttempt(frames = curr_attempt,
                                          attempt_number = len(attempts)))
                curr_attempt = []
        return attempts

    def get_attempts_list(self, begin=0, end=0, max_results=0):
        """Begin and and are epoch timestamps that frame [start?] times"""
        key = "__list:n=%d:%s-%s" % (max_results, begin, end)
        url = ("%s/project=chromium/action=patch_stop" % (self.base_url))
        cgi_args = {}
        if (begin): cgi_args = {'begin':begin, 'end':end}
        data = self.caching_get.get_all_json_results(url,
                                                     cgi_args=cgi_args,
                                                     key=key,
                                                     max_results=max_results)
        return data

    def get_recent_attempts(self,max_results=100):
        attempts = []
        recents = self.get_attempts_list(max_results=max_results)
        for result in recents:
            attempts.extend(self.get_cq_attempts_for_patchset(
                result['fields']['issue'],
                result['fields']['patchset']))
        return attempts

    def get_cq_attempts_for_patchset(self,issue,patchset):
        """Returns list of CqAttempts made for issue:patchset"""
        url = "%s/issue=%s/patchset=%s" % (self.base_url, issue, patchset)
        key = "%s:%s" % (issue, patchset)
        return self.frames_into_attempts(
            self.caching_get.get_all_json_results(url, key=key))

    def process_attempts(self, callback, state, issue_patchsets):
        for issue_patchset in issue_patchsets:
            for attempt in self.get_cq_attempts_for_patchset(
                    issue_patchset['fields']['issue'],
                    issue_patchset['fields']['patchset']):
                callback(state,attempt)

    def process_recent_attempts(self, callback, state, max_results=10):
        self.process_attempts(callback, state,
                              self.get_attempts_list(max_results=max_results))

    def process_dated_attempts(self, callback, state, begin=0, end=0):
        self.process_attempts(callback, state,
                              self.get_attempts_list(begin=begin,end=end))
