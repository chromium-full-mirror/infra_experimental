#!/usr/bin/env python
# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os

from scandir import walk as OS_WALK
from google.protobuf import text_format as textpb

from project_config_pb2 import BuildbucketCfg
from multiline_proto import parse_multiline


def main():
  for base, _, fnames in OS_WALK(os.curdir):
    for fname in fnames:
      if fname != 'cr-buildbucket.cfg':
        continue

      path = os.path.join(base, fname)
      with open(path, 'rb') as cfg_file:
        pb = textpb.Parse(parse_multiline(cfg_file.read()), BuildbucketCfg())

      bad = {}
      want_tag = 'vpython:native-python-wrapper'
      for bucket in pb.buckets:
        tags = bucket.swarming.builder_defaults.swarming_tags
        if want_tag not in tags:
          bad[bucket.name] = tags

      if bad:
        print path
        for bucket, tags in sorted(bad.items()):
          print '  bucket %r missing tag %s: %s' % (bucket, want_tag, tags)


if __name__ == '__main__':
  main()

# [VPYTHON:BEGIN]
# wheel: {name: "infra/python/wheels/protobuf-py2_py3" version: "version:3.6.1"}
# wheel: {name: "infra/python/wheels/scandir/${vpython_platform}" version: "version:1.9.0"}
# [VPYTHON:END]
