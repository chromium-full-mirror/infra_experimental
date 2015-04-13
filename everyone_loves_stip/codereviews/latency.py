import argparse
import collections
import dateutil
import datetime
import getpass
import itertools
import json
import matplotlib.pyplot as plt
import numpy
import requests
import grequests
import itertools
import simplejson
import os
import seaborn as sns
import sys

# Shamelessly stolen from http://goo.gl/JJmg4m.
def get_issue_latency(issue, reviewer):
  from_owner = [
    msg for msg in issue['messages'] if msg['sender'] == issue['owner_email']
  ]
  if not from_owner:
    # Probably requested by email.
    return None
  first_msg_from_owner = None
  latency = None
  received = False
  for index, msg in enumerate(issue['messages']):
    if not first_msg_from_owner and msg['sender'] == issue['owner_email']:
      first_msg_from_owner = msg
    if index and not received and msg['sender'] == reviewer:
      return None
    received |= reviewer in msg['recipients']
    if first_msg_from_owner and msg['sender'] == reviewer:
      delta = dateutil.parser.parse(msg['date']) - dateutil.parser.parse(first_msg_from_owner['date'])
      latency = delta.seconds + delta.days * 24 * 3600
      break
  return latency


TimeChunk = collections.namedtuple('TimeChunk',
    ['created_after', 'created_before'])


ApiRequest = collections.namedtuple('ApiRequest',
    ['server', 'user', 'timechunk', 'cursor'])


def year_month_generator(startyear, startmonth, endyear, endmonth):
  assert startyear <= endyear
  if startyear == endyear:
    assert startmonth < endmonth
  assert startmonth > 0 and startmonth < 13
  assert endmonth > 0 and endmonth < 13

  year = startyear
  month = startmonth
  while year < endyear or month <= endmonth:
    yield (year, month)
    month += 1
    if month >= 13:
      year += 1
      month = 1


def pairwise(iterable):
  a, b = itertools.tee(iterable)
  next(b, None)
  return itertools.izip(a, b)


def create_month_chunks(created_after_or_during_year):
  now = datetime.datetime.utcnow()
  if created_after_or_during_year is None:
    yield TimeChunk(created_after=None, created_before=None)
  def datestring(year, month):
    return '%d-%02d-01' % (year, month)
  for after, before in pairwise(
      year_month_generator(
          created_after_or_during_year, 1, now.year, now.month)):
    yield TimeChunk(
        created_after=datestring(after[0], after[1]),
        created_before=datestring(before[0], before[1]))
  yield TimeChunk(
      created_after=datestring(now.year, now.month),
      created_before=None)


def seed_request_queue(server, users, created_after_or_during_year=None):
  request_queue = []
  created_after_or_during_year = created_after_or_during_year or 2008
  for user in users:
    for chunk in create_month_chunks(created_after_or_during_year):
      request_queue.append(ApiRequest(
        server=server,
        user=user,
        timechunk=chunk,
        cursor=None,
      ))
  return request_queue


def convert_request_to_url(req):
  url = '%s/search?format=json&reviewer=%s&with_messages=True' % (
      req.server,
      req.user)
  if req.timechunk.created_before:
    url += '&created_before=%s' % req.timechunk.created_before
  if req.timechunk.created_after:
    url += '&created_after=%s' % req.timechunk.created_after
  if req.cursor:
    url += '&cursor=%s' % req.cursor
  return url


def get_latencies(server, usernames, start_year=2008):
  latencies = []
  request_queue = seed_request_queue(server, usernames, start_year)
  wave_num = 0
  while request_queue:
    print 'request wave %d, %d requests in flight' % (
        wave_num, len(request_queue))
    urls = [convert_request_to_url(r) for r in request_queue]
    rs = [grequests.get(url) for url in urls]
    results = grequests.map(rs)
    old_request_queue = request_queue
    request_queue = []
    for req, res in zip(old_request_queue, results):
      res_json = res.json()
      for issue in res_json['results']:
        latency = get_issue_latency(issue, req.user)
        if latency:
          latencies.append((dateutil.parser.parse(issue['created']), latency))

      if res_json['results']:
        request_queue.append(
            ApiRequest(
              server=req.server,
              user=req.user,
              timechunk=req.timechunk,
              cursor=res_json['cursor']))
    wave_num += 1
  print 'done making requests'
  return sorted(latencies, key=lambda x: x[0])



def dt_to_ts(dt):
  return (dt - datetime.datetime.utcfromtimestamp(0)).total_seconds()


# http://stackoverflow.com/a/6822773/3984761
def sliding_window(seq, n=2):
  it = iter(seq)
  result = tuple(itertools.islice(it, n))
  if len(result) == n:
    yield result    
  for elem in it:
    result = result[1:] + (elem,)
    yield result

def better_window(sorted_arr, idx, timedelta):
  yield idx
  small_idx = idx - 1
  while small_idx >= 0 and sorted_arr[
      small_idx] > (sorted_arr[idx] - timedelta):
    yield small_idx
    small_idx -= 1

  large_idx = idx + 1
  while large_idx < len(sorted_arr) and sorted_arr[
      large_idx] < (sorted_arr[idx] + timedelta):
    yield large_idx
    large_idx += 1


def windowed(x, y, timedelta, window_thresh):
  for i in range(len(x)):
    indices = better_window(x, i, timedelta)
    res = [y[idx] for idx in sorted(indices)]
    if len(res) >= window_thresh:
      yield res
    else:
      yield None

def filter_latencies(latencies, hourly_limit):
  for x, y in zip(*latencies):
    if y < hourly_limit:
      yield x, y


def filtered_percentile(x, y, window_days, window_thresh, percentile):
  new_x = []
  new_y = []
  windowed_data = windowed(
      x, y, datetime.timedelta(days=window_days/2.0), window_thresh)
  for xx, yy in zip(x, windowed_data):
    if yy:
      new_x.append(xx)
      new_y.append(numpy.percentile(yy, percentile))
  return (new_x, new_y)


def get_args():
  parser = argparse.ArgumentParser()
  parser.add_argument('usernames', nargs='?',
      help='comma-separated list of usernames. default %(default)s',
      default='%s@chromium.org' % getpass.getuser())
  parser.add_argument('--thresh',
      type=int,
      help='number of points required to plot a window. default %(default)d',
      default=10)
  parser.add_argument('--palette',
      default='husl',
      help='plot the data with a palette from http://goo.gl/fndl7O. '
           'default %(default)s.')
  parser.add_argument('--server',
      default='https://codereview.chromium.org',
      help='rietveld instance to connect to')
  parser.add_argument('--plot-raw', action='store_true',
      help='also plot raw datapoints')
  parser.add_argument('--cutoff-hours',
      default=24 * 30, type=int,
      help='ignore latencies higher than this many hours. default %(default)s.')
  parser.add_argument(
      '--plotlist',
      default='7,50,30,50,90,50',
      help='flattened comma-separated list of (days-in-window, percentile) to'
           ' plot. default %(default)s.')
  parser.add_argument(
      '--cache-file',
      help='use a json file as a cache to limit hitting rietveld. '
           'note: this cache is never invalidated, delete it if you change '
           'usernames, start year, or if you want fresh data.')
  parser.add_argument(
      '--start-year',
      default=2008, type=int,
      help='the year to start scanning. default %(default)s.')

  args = parser.parse_args()
  args.usernames = args.usernames.split(',')
  args.plotlist = [int(x) for x in args.plotlist.split(',')]
  if len(args.plotlist) % 2 != 0:
    parser.error(
        'plotlist must have an even number of elements (you listed %d)' %
        len(args.plotlist))
  return args


def main():
  args = get_args()
  sns.set()
  sns.set_palette(args.palette)
  latencies = None
  if args.cache_file and os.path.exists(args.cache_file):
    with open(args.cache_file) as f:
      raw_latencies = json.load(f)
      latencies = [
          [datetime.datetime.utcfromtimestamp(x) for x in raw_latencies[0]],
          raw_latencies[1]]
      print 'loaded data from %s' % args.cache_file
  if latencies is None:
    print 'loaded data from %s' % args.server
    start = datetime.datetime.utcnow()
    latencies = zip(
        *get_latencies(args.server, args.usernames, args.start_year))
    end = datetime.datetime.utcnow()
    print 'took %fs' % (end - start).total_seconds()
    if args.cache_file:
      raw_latencies = [[dt_to_ts(x) for x in latencies[0]], latencies[1]]
      with open(args.cache_file, 'w') as f:
        json.dump(raw_latencies, f, indent=2)
      print 'wrote data to %s' % args.cache_file

  # Convert to hours.
  latencies[1] = [x / 3600.0 for x in latencies[1]]

  latencies = zip(*filter_latencies(latencies, args.cutoff_hours))

  def group(lst, n):
    for i in range(0, len(lst), n):
      val = lst[i:i+n]
      if len(val) == n:
        yield tuple(val)
  for window, percentile in group(args.plotlist, 2):
    plt.plot(
        *filtered_percentile(latencies[0], latencies[1], window, args.thresh,
          percentile),
        label='%d-day rolling %d-percentile' % (window, percentile))
  axes = plt.gca()
  if args.plot_raw:
    color = next(axes._get_lines.color_cycle)
    plt.scatter(latencies[0], latencies[1], 5, label='raw latencies', c=color,
  lw=0)
  plt.ylabel('hours from issue creation to first response')
  start, stop = axes.get_ylim()
  ticks = numpy.arange(0, stop + 24, 24)
  axes.set_yticks(ticks)
  plt.legend(loc='upper right', frameon=True)

  plt.show()
  return 0


if __name__ == '__main__':
  sys.exit(main())
