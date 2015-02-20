# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Crappy wrapper object around the CQ status endpoint

from CachingGet import CachingGet
import pprint

class ChromiumCqStatus:
    base_url = 'https://chromium-cq-status.appspot.com/query'
    caching_get = CachingGet(no_cache=True)
    pprinter = pprint.PrettyPrinter(depth=3, indent=2)

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
        print ("--{ %s:%s }--" % (item[0]['fields']['issue'],
                                  item[0]['fields']['patchset']))

        for frame in sorted(item, key=lambda x: x['fields']['timestamp']):
            print " %.6f {%-23.23s}" % (frame['fields']['timestamp'],
                                      frame['fields']['action'])

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
