#!/usr/bin/env python
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""Generate a random branch name based on a wordlist.

This file generates a random branch name based on wordlists. Using a pattern and
wordlist is intended to create random but memorable names to automate `git
new-branch` usage. Any locale can be requested, but if it is not present in the
datafile it will fall back to en_US
(https://en.wikipedia.org/wiki/Americanization).
"""

import argparse
import json
import locale
import os
import random
import sys

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
WORDLIST = os.path.join(DATA_DIR, 'branch_wordlist.json')

FALLBACK_LOCALE = 'en_US'


def generate_branch(requested_locale=FALLBACK_LOCALE):
  with open(WORDLIST) as f:
    wordlist = json.load(f)

  # Each locale has a list of lists. A word is randomly picked from each list,
  # making a branch name.

  wl = wordlist.get(requested_locale, wordlist[FALLBACK_LOCALE])
  sequence = [random.choice(words) for words in wl]
  return '-'.join(sequence)


def main():
  parser = argparse.ArgumentParser(
      description='Generates a random branch name.',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument(
      '--locale', default=locale.getdefaultlocale()[0],
      help='The locale used to generate names. Falls back to %s if not in data '
           'file.' % FALLBACK_LOCALE)

  args = parser.parse_args()
  branch_name = generate_branch(requested_locale=args.locale)
  print branch_name


if __name__ == '__main__':
  sys.exit(main())
