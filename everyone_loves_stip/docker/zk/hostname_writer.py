#!/usr/bin/env python
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import socket
import os
import sys

def main():
  os.mkdir('hostname')
  with open(os.path.join('hostname', 'hostname'), 'w') as f:
    f.write(socket.gethostbyname(socket.gethostname()))

if __name__ == '__main__':
  sys.exit(main())
