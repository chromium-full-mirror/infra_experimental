# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import requests
import os.path
import pickle
from pprint import pprint

class CachingGet:

    def __init__(self, cache_dir="~/.caching-get", no_cache=False):
        self.cache_dir = os.path.expanduser(cache_dir)
        self.no_cache = no_cache
        if (not os.path.isdir(self.cache_dir)):
            os.makedirs(self.cache_dir)

    def cachefilename(self,key):
        return ("%s/%s" % (self.cache_dir, key))

    def fetch_all_results(self, url, no_paging=False):
        """Extract 'results' items, fetching later pages as needed"""
        cursor = '';
        all_data = []
        more_data_remains = True
        i = 0
        if (url.find("patchset") < 0): no_paging=True
        while more_data_remains:
            cursored_url = url
            if (cursor): cursored_url += "&cursor=%s" % cursor
            resp = requests.get(cursored_url).json()
            all_data.extend(resp['results'])
            more_data_remains = resp['more']
            if (no_paging): more_data_remains = False
            i += 1
            cursor = resp['cursor']
            print ("%d n=%d, more=%s, cursor=%s"
                   % (i, len(resp['results']), more_data_remains, cursor))
            #pprint(resp['results'])

        return all_data

    def get_json_results(self, url, key):
        """If key is empty, no caching is done. Follows cursors."""
        if (self.no_cache): key = ''
                #print ("get_json[%s] %s" % (key, url))
        if (key != '' and os.path.isfile(self.cachefilename(key))):
            with open(self.cachefilename(key), 'r') as infile:
                return pickle.load(infile)

        data = self.fetch_all_results(url)
        if (key != ''):
            with open(self.cachefilename(key), 'w') as outfile:
                pickle.dump(data, outfile)

        return data
