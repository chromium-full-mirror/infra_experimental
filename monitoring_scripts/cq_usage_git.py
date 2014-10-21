#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Count commits by the commit queue."""

import argparse
import datetime
import json
import logging
import numbers
import sys
import traceback
import requests


REPO_URLS = {
    'chromium': 'https://chromium.googlesource.com/chromium/src',
    'blink': 'https://chromium.googlesource.com/chromium/blink',
}


def fetch_page(session, repo_url, cursor=None, page_size=2000):
  """Fetch one page worth of logs from gitiles."""
  url = repo_url + '/+log/master'
  logging.debug('fetch_page: url = %s', url)
  params = {
      'pretty': 'full',
      'format': 'JSON',
      'n': page_size,
  }
  if cursor:
    params.update({'s': cursor})
  try:
    # Strip off the anti-XSS string from the response.
    lines = [l for l in session.get(url, params=params).iter_lines()
             if l != ")]}'"]
    raw_data = ''.join(lines)
    page = json.loads(raw_data)
  except Exception as e:
    page = {}
    logging.error('Failed to fetch a page: %s', e)
  return page


def date_from_git(date_str):
  """If date_str is not valid or None, return None."""
  if not date_str:
    return None
  date = None
  try:
    date = datetime.datetime.strptime(
        date_str, '%a %b %d %H:%M:%S %Y')
  except Exception:
    pass
  return date


def date_from_string(iso_str):
  formats = ['%Y-%m-%d %H:%M:%S.%f',
             '%Y-%m-%d %H:%M:%S',
             '%Y-%m-%d %H:%M',
             '%Y-%m-%d %H',
             '%Y-%m-%d']
  for fmt in formats:
    try:
      return datetime.datetime.strptime(iso_str, fmt)
    except ValueError:
      pass
  raise ValueError('Unrecognized date/time format: %s' % iso_str)


def fetch_logs(session, repo, from_date, to_date):
  """Fetch all logs from Gitiles for the given date range.

  Gitiles does not natively support time ranges, so we just fetch
  everything until the range is covered. Assume that logs are ordered
  in reverse chronological order.
  """
  cursor = ''
  commit_date = to_date
  data = []
  while(cursor is not None):
    page = fetch_page(session, repo, cursor)
    logs = page.get('log', [])
    cursor = page.get('next')
    for log in logs:
      committer = log.get('committer', {})
      commit_date = date_from_git(committer.get('time'))
      if not commit_date:
        continue
      if commit_date > to_date:
        continue
      if commit_date < from_date:
        break
      data.append({
          'author': log.get('author', {}).get('email'),
          'date': commit_date,
          'commit-bot': bool('commit-bot' in committer.get('email', '')),
          'revision': log.get('commit'),
      })

    if commit_date < from_date:
      break
  return data


def print_aligned(zipped_list):
  if not zipped_list:
    return
  max_len = max(len(i[0]) for i in zipped_list)
  for author, count in zipped_list:
    print('%*s: %d' % (max_len, author, count))


def percentage(data, total):
  num_data = data if isinstance(data, numbers.Number) else len(data)
  num_total = total if isinstance(total, numbers.Number) else len(total)
  percent = 100. * num_data / num_total if num_total else 0
  return num_data, num_total, percent


def print_data(log_data, options):
  # Calculate stats.
  cq_commits = [v for v in log_data if v['commit-bot']]
  users = {}
  for i in cq_commits:
    users.setdefault(i['author'], 0)
    users[i['author']] += 1

  if not options.stats_only:
    max_author_len = max(len(i['author']) for i in log_data)
    for entry in log_data:
      by_cq = ' '
      by_bot = ' '
      if entry['commit-bot']:
        by_cq = 'c'
      if entry['author'] in options.bots:
        by_bot = 'b'
      print('%s  %s%s  %s  %*s' % (
        (entry['revision']).rjust(40),
        by_cq, by_bot,
        entry['date'].strftime('%Y-%m-%d %H:%M UTC'),
        max_author_len,
        entry['author']))
    print('')

  committers = {}
  manual_committers = {}
  bot_committers = {}
  bot_manual_committers = {}
  for i in log_data:
    committers.setdefault(i['author'], 0)
    committers[i['author']] += 1
    if not i['commit-bot']:
      manual_committers.setdefault(i['author'], 0)
      manual_committers[i['author']] += 1
    if i['author'] in options.bots:
      bot_committers.setdefault(i['author'], 0)
      bot_committers[i['author']] += 1
    if i['author'] in options.bots and not i['commit-bot']:
      bot_manual_committers.setdefault(i['author'], 0)
      bot_manual_committers[i['author']] += 1

  manual_commits = sum(x for x in manual_committers.itervalues())
  bot_commits = sum(x for x in bot_committers.itervalues())
  bot_manual_commits = sum(x for x in bot_manual_committers.itervalues())
  manual_only_committers = {
      a: c for a, c in committers.iteritems()
      if c == manual_committers.get(a, 0)}
  print('CQ users:      %6d out of %6d total committers %6.2f%%' %
        percentage(users, committers))
  fmt_str = '  Committed    %6d out of %6d commits          %6.2f%%'
  data = percentage(cq_commits, log_data)
  if bot_manual_commits:
    fmt_str += ' (%6.2f%% by humans)'
    data += percentage(cq_commits, len(log_data) - bot_manual_commits)[2:3]
  print fmt_str % data

  if not options.stats_only and options.top and manual_only_committers:
    print
    print 'Top %d manual only committers:' % options.top
    top_manual_only = sorted(
        manual_only_committers.iteritems(),
        key=lambda x: x[1], reverse=True)[:options.top]
    print_aligned(top_manual_only)

  if not options.stats_only and options.top and users:
    top_users = sorted(
        users.iteritems(), key=lambda x: x[1], reverse=True)[:options.top]
    print
    print 'Top %d CQ users:' % options.top
    print_aligned(top_users)

  print
  print('Bots:                %6d out of %6d total committers %6.2f%%' %
        percentage(bot_committers, committers))
  print('  Committed by CQ    %6d out of %6d commits          %6.2f%%' %
        percentage(bot_commits, log_data))
  print('  Committed directly %6d out of %6d commits          %6.2f%%' %
        percentage(bot_manual_commits, log_data))
  print
  print('Manual committers: %6d out of all %6d users   %6.2f%%' %
        percentage(manual_committers, committers))
  print('  Committed        %6d out of     %6d commits %6.2f%%' %
        percentage(manual_commits, log_data))
  if not options.stats_only and options.top and manual_committers:
    top_manual_committers = sorted(
        manual_committers.iteritems(), key=lambda x: x[1],
        reverse=True)[:options.top]
    print 'Top %d manual committers:' % len(top_manual_committers)
    print_aligned(top_manual_committers)

  non_committers = sorted(
        ( (u, c) for u, c in users.iteritems()
          if not u.endswith('@chromium.org')),
        key=lambda x: x[1], reverse=True)
  if non_committers:
    print
    n_c_commits = sum(x[1] for x in non_committers)
    print('Non-chromium.org CQ users: %6d out of %6d total users   %6.2f%%' %
          percentage(non_committers, committers))
    print('  Committed                %6d out of %6d total commits %6.2f%%' %
          percentage(n_c_commits, log_data))
    if not options.stats_only and options.top and non_committers:
      print 'Top %d non-chromium.org CQ users:' % (
          min(options.top, len(non_committers)))
      print_aligned(non_committers[:options.top])

    if options.domains:
      print
      print('Top domains')
      domains = {}
      for user, count in non_committers:
        domain = user.split('@', 1)[1]
        domains.setdefault(domain, 0)
        domains[domain] += count
      domains_stats = sorted(
          ((k, v) for k, v in domains.iteritems()),
          key=lambda x: x[1], reverse=True)
      print_aligned(domains_stats)
      if not options.stats_only:
        print_aligned(non_committers)


def get_args():
  parser = argparse.ArgumentParser(
      description=sys.modules['__main__'].__doc__)
  parser.add_argument('-v', '--verbose', action='store_true')
  parser.add_argument(
      '-r', '--repo', default='',
      help='Directly set the Gitiles URL. Overrides --project.')
  parser.add_argument(
      '--project',
      choices=['chromium', 'blink'],
      default='chromium',
      help='Sets the default --repo argument to the project\'s URL.')
  parser.add_argument(
      '--from-date',
      required=True,
      help='Count starting from this date. Format: YYYY-MM-DD[ HH[:MM[:SS]]],')
  parser.add_argument(
      '--to-date',
      required=True,
      help='Count starting from this date. Format: YYYY-MM-DD[ HH[:MM[:SS]]],')
  parser.add_argument('--domains', action='store_true', default=False,
                      help='Print top non-committers\' domains.')
  parser.add_argument('-o', '--stats_only', dest='stats_only',
                      action='store_true', default=True,
                      help='Only print summary stats.')
  parser.add_argument('-l', '--list_commits', dest='stats_only',
                      action='store_false', default=True,
                      help='List revisions and committers.')
  parser.add_argument('--top', default=20, type=int,
                      help='How many entries to print for "top N" reports.')
  parser.add_argument('--bot', type=str, dest='bots',
                      action='append',
                      default=['blink-deps-roller@chromium.org',
                               'chrome-admin@google.com',
                               'chrome-release@google.com',
                               'chromeos-commit-bot@chromium.org',
                               'skia-deps-roller@chromium.org',
                              ],
                      help=('Add an author to be treated as a bot. '
                            'Repeat to add several bots.'))
  options = parser.parse_args()
  if not options.repo:
    options.repo = REPO_URLS[options.project]

  logging.basicConfig(
      level=(logging.DEBUG if options.verbose else logging.ERROR))

  options.from_datetime = date_from_string(options.from_date)
  options.to_datetime = date_from_string(options.to_date)
  return options


def main():
  options = get_args()
  session = requests.Session()

  try:
    log_data = fetch_logs(
        session, options.repo, options.from_datetime, options.to_datetime)
    print_data(log_data, options)
  except Exception:
    print 'ERROR: Uncaught exception:' + '\n'.join([
        'exception type: %r' % sys.exc_info()[0],
        'exception value: %r' % sys.exc_info()[1],
        traceback.format_exc()])
    raise
  return 0


if __name__ == '__main__':
  sys.exit(main())
