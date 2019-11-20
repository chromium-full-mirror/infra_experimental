#!/usr/bin/env vpython
# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Dumps all known LUCI-config project config files to disk.

Useful for for local debugging and inspection of config files globally across
LUCI.

Requires LUCI Auth to work. To run this locally, do:

  $ luci-auth login   # If you haven't logged in ever
  $ cd some/dir       # data will be dumped under $CWD.
  $ luci-auth context ./%(prog)s config_file_name
"""

import argparse
import json
import os
import errno

import httplib2

from infra_libs.luci_auth import LUCICredentials


BASE_URL = 'https://luci-config.appspot.com/_ah/api/config/v1/configs'


def main():
  parser = argparse.ArgumentParser(
      formatter_class=argparse.RawDescriptionHelpFormatter,
      description=__doc__)
  parser.add_argument(
      'config_file_name',
      help='The name of the config file to retrieve.')
  args = parser.parse_args()

  http = LUCICredentials().authorize(httplib2.Http())
  resp, body = http.request(
      '%s/projects/%s' % (BASE_URL, args.config_file_name), 'GET')
  assert resp['status'] == '200', 'Got non-200: %r' % resp

  for config in json.loads(body)['configs']:
    dirname = config['config_set'].replace('/', os.path.sep)
    try:
      os.makedirs(dirname)
    except OSError as ex:
      if ex.errno != errno.EEXIST:
        raise

    cfg_file = os.path.join(dirname, args.config_file_name)
    with open(cfg_file, 'wb') as cfg:
      cfg.write(config['content'].decode('base64'))
    with open(cfg_file+'.meta', 'wb') as meta:
      json.dump({
        'url': config['url'],
        'revision': config['revision'],
        'content_hash': config['content_hash'],
      }, meta)
    print 'Wrote %r' % (cfg_file,)


if __name__ == '__main__':
  main()

# [VPYTHON:BEGIN]
# wheel: {name: "infra/python/wheels/certifi-py2_py3" version: "version:2018.11.29"}
# wheel: {name: "infra/python/wheels/chardet-py2_py3" version: "version:3.0.4"}
# wheel: {name: "infra/python/wheels/google_api_python_client-py2_py3" version: "version:1.6.2"}
# wheel: {name: "infra/python/wheels/httplib2-py2_py3" version: "version:0.12.1"}
# wheel: {name: "infra/python/wheels/idna-py2_py3" version: "version:2.8"}
# wheel: {name: "infra/python/wheels/oauth2client-py2_py3" version: "version:4.1.3"}
# wheel: {name: "infra/python/wheels/protobuf-py2_py3" version: "version:3.6.1"}
# wheel: {name: "infra/python/wheels/pyasn1-py2_py3" version: "version:0.4.5"}
# wheel: {name: "infra/python/wheels/pyasn1_modules-py2_py3" version: "version:0.2.4"}
# wheel: {name: "infra/python/wheels/requests-py2_py3" version: "version:2.21.0"}
# wheel: {name: "infra/python/wheels/rsa-py2_py3" version: "version:4.0"}
# wheel: {name: "infra/python/wheels/six-py2_py3" version: "version:1.10.0"}
# wheel: {name: "infra/python/wheels/uritemplate-py2_py3" version: "version:3.0.0"}
# wheel: {name: "infra/python/wheels/urllib3-py2_py3" version: "version:1.24.1"}
#
# wheel: {name: "infra/python/wheels/infra_libs-py2" version: "version:2.0.0"}
# [VPYTHON:END]
