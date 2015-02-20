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
    caching_get = CachingGet() #no_cache=True)
    pp1 = pprint.PrettyPrinter(depth=1, indent=2)
    pp2 = pprint.PrettyPrinter(depth=2, indent=2)
    pp3 = pprint.PrettyPrinter(depth=3, indent=2)

    def list_url_and_key_(self, project='chromium', count=100):
        url = ("%s/project=%s/action=patch_stop?count=%d" %
                (self.base_url, project, count))
        key = "__list:%d" % (count)
        return (url, key)

    def item_url_and_key_(self,issue,patchset):
        url = "%s/issue=%s/patchset=%s" % (self.base_url, issue, patchset)
        key = "%s:%s" % (issue, patchset)
        return (url, key)

    def recent_list(self,count=100):
        url, key = self.list_url_and_key_(count=count)
        data = self.caching_get.get_json_results(url, key)
        return data

    def pprint_item(self, item):
        cq_attempt = CqAttempt(item)
        print (cq_attempt)

    def get_cq_attempts_for_issue_patchset(self,issue,patchset):
        """Returns list of CqAttempts made for issue:patchset"""
        url, key = self.item_url_and_key_(issue,patchset)
        all_frames = self.caching_get.get_json_results(url, key)
        attempts = []
        curr_attempt = []
        for frame in sorted(all_frames,
                            key=lambda x: x['fields']['timestamp']):
            action = frame['fields']['action']
            if (action != 'patch_start' and len(curr_attempt)==0): continue
            curr_attempt += frame
            if (action == 'patch_stop'):
                print "asfafasdfs\n\n"
                attempts += CqAttempt(frames = curr_attempt,
                                      attempt_number = len(attempts))
                curr_attempt = []

        return attempts

    def recent_items(self,count=100):
        items = []
        recents = self.recent_list(count=count)
        for result in recents:
            url, key = self.item_url_and_key_(result['fields']['issue'],
                                              result['fields']['patchset'])
            item = self.caching_get.get_json_results(url, key)
            items.append(item)
            self.pprint_item(item)
        return items
