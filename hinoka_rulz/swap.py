#!/usr/bin/python

"""Swap an Android builder to swarming.  There are 3 stages:

1. src side: Add swarming configs to the src/testing/buildbot config.
2. recipe side: Enable swarming on the builder and tester.
3. (For single device setup) Add a new GCE bot and convert the existing machine to swarming.
"""

import os
import sys
import argparse
import subprocess
import json
import urllib
import random
import re

TMP_DIR = os.path.expanduser('~/.swapperoo')

word_file = "/usr/share/dict/words"
WORDS = open(word_file).read().splitlines()

def random_word():
  word = random.choice(WORDS)
  return ''.join([i if ord(i) < 128 else '' for i in word])

call = subprocess.call
check_output = subprocess.check_output


class Builder(object):
  def __init__(self, name):
    self.name = name
    self.os = None
    self.type = None
    self.devices = 4

  def __str__(self):
    return '%s (%s/%s)' % (self.name, self.os, self.type)

  def __repr__(self):
    return self.__str__()


def update(repo, target):
  if not os.path.exists(TMP_DIR):
    os.makedirs(TMP_DIR)
  target = os.path.join(TMP_DIR, target)
  if not os.path.exists(target):
    call(['git', 'clone', repo, target])
  call(['git', 'pull'], cwd=target)
  call(['git', 'reset', '--hard', 'origin/master'], cwd=target)
  call(['git', 'new-branch', random_word()], cwd=target)
  return target

def src(master, builders, bug, reviewers):
  p = update('https://chromium.googlesource.com/chromium/src', 'src')

  testfile = os.path.join(p, 'testing', 'buildbot', '%s.json' % master)
  with open(testfile) as f:
    o = json.load(f)
  if not builders:
    print 'No builders specified.  Available: %s' % o.keys()
    return

  for name, builder in o.iteritems():
    if name not in builders:
      continue
    b_info = builders[name]
    for test in builder['gtest_tests']:
      test_name = test['test']
      test['override_isolate_target'] = test_name
      test['swarming'] = {
        'can_use_on_swarming_builders': True,
        'cipd_packages': [{
          'cipd_package': 'infra/tools/luci/logdog/butler/${platform}',
          'location': 'bin',
          'revision': 'git_revision:3ff24775a900b675866fbcacf2a8f98a18b2a16a',
        }],
        'dimension_sets': [
          {
            'android_devices': '%d' % b_info.devices,
            'device_os': b_info.os,
            'device_type': b_info.type,
          }
        ],
        'hard_timeout': 1800,
        'output_links': [
          {
            'link': [
              'https://luci-logdog.appspot.com/v/?s',
              '=android%2Fswarming%2Flogcats%2F',
              '${TASK_ID}%2F%2B%2Funified_logcats'
            ],
            'name': 'shard #${SHARD_INDEX} logcats'
          }
        ]
      }
      for key in ['test_apk', 'apk_under_test']:
        if key in test:
          del test[key]

  with open(testfile, 'w') as f:
    json.dump(o, f, sort_keys=True, separators=(',', ': '), indent=2)

  desc = '%s: Full swarm %s' % (master, ', '.join(builders.keys()))
  desc += '\n\nBUG=%s' % bug
  call(['git', 'commit', '--all', '-m', desc], cwd=p)
  out = check_output([
      'git', 'cl', 'upload', '--bypass-hooks', '--cq-dry-run',
      '-m', desc, '-f', '-r', reviewers], cwd=p)
  issue = re.search(r'Issue created. URL: (.*) \(', out, re.M)
  return issue

def dict_entry(dict_node, key):
  index = None
  for i in range(len(dict_node.keys)):
    key = dict_node.keys[i]
    if key.s == key:
      index = i
      break
  if index is not None:
    return dict_node.values[i]
  return None

def recipe(master, builders, bug, reviewers):
  p = update('https://chromium.googlesource.com/chromium/tools/build', 'build')
  name = '%s.py' % master.replace('.', '_')
  fname = os.path.join(p, 'scripts', 'slave', 'recipe_module', 'chromium_tests', name)
  with open(fname) as f:
    a = ast.parse(f.read())
  spec = None
  for item in a.body:
    if isinstance(item, ast.Assign) and item.targets[0].id == 'SPEC':
      spec = item.value
      break
  builders_node = dict_entry(spec, 'builders')
  for b in builders:
    builder_node = dict_entry(builders_node, b.name)

def new_bot(args):
  raise

def convert_bot(args):
  raise


def get_builders(master, builders):
  """Given a list of builders, find info about the builder (from the master json)."""
  master_json = json.load(urllib.urlopen(
      'https://chrome-build-extract.appspot.com/get_master/%s' % master))
  result = {}
  for name in builders:
    b = Builder(name)
    builder_json = master_json['builders'][name]
    builds = builder_json['cachedBuilds']
    build_json = json.load(urllib.urlopen(
        'https://chrome-build-extract.appspot.com/p/%s/builders/%s/builds/%d?json=true'
        % (master, name, builds[0])))
    for step in build_json['steps']:
      if step['name'] != 'device_status':
        continue
      for log_label, url in step['logs']:
        log_split = log_label.split(' ')
        if len(log_split) == 3:
          b.os = log_split[1]
          b.type = log_split[0]
          break
    result[name] = b
  return result


def main(argv):
  parser = argparse.ArgumentParser()
  parser.add_argument('--src', action='store_true', help='Make the source side change')
  parser.add_argument('--recipe', action='store_true', help='Make the recipe side change')
  parser.add_argument('--new-bot', action='store_true', help='Create a new bot')
  parser.add_argument('--convert-bot', action='store_true', help='Convert existing bot to swarming')

  parser.add_argument('--master', required=True, help='Master to convert.  Only one supported')
  parser.add_argument('builders', nargs='*', help='Builders to convert')

  parser.add_argument('--bug', '-b', help='Bug number', required=True)
  parser.add_argument('--reviewers', '-r', help='Reviewers', required=True)

  args = parser.parse_args(argv)

  builders = get_builders(args.master, args.builders)

  if args.src:
    src(args.master, builders, args.bug, args.reviewers)
  if args.recipe:
    recipe(args.master, builders, args.bug, args.reviewers)
  if args.new_bot:
    new_bot(args)
  if args.convert_bot:
    convert_bot(args)

if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
