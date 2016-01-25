#!/usr/bin/env python

import json
import sys

"""
Simulate a local disk cache for a list of files of swarming tasks.
Does not do any trimming (i.e. assumes an infinite cache).

Example:
./last_isolates.py path/to/luci-py/client vm92-m4 200 > last_200.json
./flatten_isolates.py path/to/luci-py/client last_200.json > last_200_flat.json
./simulate_caching.py last_200_flat.json
"""

assert len(sys.argv) == 2

with open(sys.argv[1]) as f:
  tasks = json.load(f)

seen = {}
items = {}
hits = 0
small_hits = 0
small_hits_size = 0
large_hits = 0
large_hits_size = 0
total = 0

# Iterate over tasks in reversed order (oldest -> newest).
for task in reversed(tasks):
  for name, hsh, size in task:
    items[hsh] = name, size
    count = seen.setdefault(hsh, 0)
    if count:
      # It's a hit.
      hits += 1
      if size > 1000000:
        large_hits += 1
        large_hits_size += size
      else:
        small_hits += 1
        small_hits_size += size
    else:
      # Added to cache.
      total += size
    seen[hsh] += 1

by_hits = sorted(seen.iteritems(), reverse=True, key=lambda x: x[1])

n_repeated = 0
size_repeated = 0
for i in by_hits:
  if i[1] == 1:
    break
  n_repeated += 1
  size_repeated += items[i[0]][1]

# What's in the cache?
print 'In cache (n):\t\t\t%d' % len(seen)
print 'In cache (size):\t\t%d' % total

# What's in the cache and has been hit at least once?
print 'In cache hit>0 (n):\t\t%d' % n_repeated
print 'In cache hit>0 (size):\t\t%d' % size_repeated

# Total cache hits.
print 'Cache hits:\t\t\t%d' % hits

# Cache hits of files below 1MB.
print 'Cache hits (below 1M):\t\t%d' % small_hits
print 'Cache hits (size below 1M):\t%d' % small_hits_size

# Cache hits of files above 1MB.
print 'Cache hits (above 1M):\t\t%d' % large_hits
print 'Cache hits (size above 1M):\t%d' % large_hits_size

# Optional, see what kind of items are most frequently used.
# for i in by_hits[:100]:
#   print items[i[0]], i[1]

