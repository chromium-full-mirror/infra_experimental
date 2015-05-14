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

    def fetch_all_results(self, base_url, cgi_args={},
                          max_results=0, page_size=100):
        """Extract 'results' items, fetching later pages as needed"""
        all_data = []
        cursor = '';
        more_data_remains = True
        while more_data_remains:
            url = "%s?count=%s&cursor=%s" % (base_url, page_size, cursor)
            for k in cgi_args: url += "&%s=%s" % (k, cgi_args[k])
            resp = requests.get(url).json()
            all_data.extend(resp['results'])
            more_data_remains = resp['more']
            if (max_results > 0 and len(all_data) >= max_results):
                more_data_remains = False
            cursor = resp['cursor']
            print (" [this_page_n=%d, more=%s, n_so_far=%d, n_max=%d: url=%s]"
                   % (len(resp['results']), more_data_remains,
                      len(all_data), max_results, url))
        return all_data

    def get_all_json_results(self, url, cgi_args={}, key='',
                             max_results=0):
        """If key is empty, no caching is done"""
        if (self.no_cache): key = ''
        if (key != '' and os.path.isfile(self.cachefilename(key))):
            with open(self.cachefilename(key), 'r') as infile:
                return pickle.load(infile)

        data = self.fetch_all_results(url, cgi_args, max_results=max_results)
        if (key != ''):
            with open(self.cachefilename(key), 'w') as outfile:
                pickle.dump(data, outfile)

        return data

# A typical GAE app appears to work like this ...

# 1. An initial URL is constructed (count == results_per_page)
#  https://thing.appspot.com/foo/bar=quux?count=100
# The specification of the URL is app dependent, although (I think ?) the
# CGI args (count,cursor) are standard parts of a GAE results-returning app. 

# 2. When submitted, it returns the first page of results as JSON:
#
# {
#   more: {True|False},
#   cursor: "DEADBEEF",
#   results: [
#     { foo: bar1, ... }
#     { foo: bar2, ... }
#     ...
#   }

# 3. If more=True, then there are more results to fetch. The specified
#  cursor should be used to retrieve the next page, like this:
#  https://thing.appspot.com/foo/bar=quux?count=100&cursor=DEADBEEF

# 4. If the base request does not contain many restrictions, then the app
# may cheerfully page through its entire database; this might not be what
# you expect. So we apply a global max_results value, and bail once we have
# at least that many results.

# So our API should look like this:

# get_gae_results (url = '', cache_key = '', max_results = N)
