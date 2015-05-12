from datetime import datetime
from datetime import timedelta
import requests_cache
import json
import itertools
import seaborn as sns
import numpy
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import time
requests_cache.install_cache('sweet_cache')
import grequests

sns.set(style="darkgrid", palette="Set2")

masters = [
  'tryserver.chromium.linux',
  'tryserver.chromium.mac',
  'tryserver.chromium.win'
]

url_template = 'https://chrome-infra-stats.appspot.com/_ah/api/stats/v1/steps/%s/build__schedule__time__/%s'

current_hour = datetime.utcnow().replace(
  minute=0, second=0, microsecond=0)
end_hour = current_hour - timedelta(hours=8)
step_urls = []
for master in masters:
  for i in reversed(range(7 * 24)):
    hour = end_hour - timedelta(hours=i)
    step_urls.append(url_template % (
      master,
      hour.strftime('%Y-%m-%dT%H:%MZ')))

chunksize = 10
url_chunks = [
    step_urls[x:x+chunksize] for x in xrange(0, len(step_urls), chunksize)]

infra_error = '4'

results = []
for chunk in url_chunks:
  rs = [grequests.get(u) for u in chunk]
  results.extend(
    list(itertools.chain.from_iterable(
      r.json().get('step_records', [])
      for r in grequests.map(rs, size=10))))

def datestring_to_ts(datestring):
  # In case the string doesn't have fractional seconds.
  try:
    return datetime.strptime(
      datestring, '%Y-%m-%dT%H:%M:%S.%f')
  except ValueError:
    return datetime.strptime(
      datestring, '%Y-%m-%dT%H:%M:%S')

cooked_results = list(sorted(({
  'step_start': (datestring_to_ts(r['step_start']) -
    datetime.utcfromtimestamp(0)).total_seconds(),
  'step_time': r['step_time'],
  'infra_failure': r['result'] == infra_error,
  'master': r['master'],
} for r in results), key=lambda x: x['step_start']))

def lock_to_time(ts, span):
  current_ts = (current_hour - datetime.utcfromtimestamp(0)).total_seconds()
  return current_ts - span * (1.0 + int((current_ts - ts) / span))

def calc_failure_rate(data):
  return len([r for r in data if r['infra_failure']]) / float(len(data))

span = 3600
cool_results = []
for k, g in itertools.groupby(
  cooked_results,
  key=lambda x: lock_to_time(x['step_start'], span)):

  g = list(g)
  times = [r['step_time'] for r in g]
  failure_rate = calc_failure_rate(g)
  cool_results.append({
    'center': k + (span / 2),
    'p50': numpy.percentile(times, 50),
    'p75': numpy.percentile(times, 75),
    'p90': numpy.percentile(times, 90),
    'p95': numpy.percentile(times, 95),
    'p99': numpy.percentile(times, 99),
    'infra_failure_rate': failure_rate,
  })

mdytime_formatter = mdates.DateFormatter('%Y-%m-%d %H:%M')
mdy_formatter = mdates.DateFormatter('%Y-%m-%d')
days = mdates.DayLocator()

#ts = [r['step_start'] for r in cooked_results]
#length = [r['step_time'] for r in cooked_results]
#sns.jointplot(numpy.array(ts), numpy.array(length), kind='kde')
fig, (ax1, ax2, ax3) = plt.subplots(nrows=3)
x = [datetime.utcfromtimestamp(r['center']) for r in cool_results]
y = [r['p99'] for r in cool_results]
ax1.scatter(x, y)
ax1.set_title('hourly 99th percentile pending time')
ax1.set_xlabel('date (utc)')
ax1.set_ylabel('seconds')
ax1.set_xlim(left=min(x) - timedelta(hours=6), right=max(x) + timedelta(hours=6))
ax1.fmt_xdata = mdytime_formatter
ax1.xaxis.set_major_locator(days)
ax1.xaxis.set_major_formatter(mdy_formatter)
y = [r['infra_failure_rate'] * 100.0 for r in cool_results]
ax2.scatter(x, y)
ax2.set_title('hourly infrastructure failure rate')
ax2.set_xlabel('date (utc)')
ax2.set_ylabel('failure percentage')
ax2.set_xlim(left=min(x) - timedelta(hours=6), right=max(x) + timedelta(hours=6))
ax2.fmt_xdata = mdytime_formatter
ax2.xaxis.set_major_locator(days)
ax2.xaxis.set_major_formatter(mdy_formatter)
y = [r['step_time'] for r in cooked_results]
print '90:', numpy.percentile(y, 90)
print '99:', numpy.percentile(y, 99)
print 'max:', max(y)
print 'failure_rate:', calc_failure_rate(cooked_results)
#sns.distplot(y, ax=ax3, kde=False)
sns.distplot(y, ax=ax3, hist=False)
#ax3.hist(y)
ax3.axvline(numpy.percentile(y, 90))
ax3.axvline(numpy.percentile(y, 99))
ax3.set_title('overall pending time distribution')
ax3.set_xlabel('seconds (90th and 99th percentile marked)')
ax3.set_xlim(left=0, right=max(y))
plt.tight_layout()
plt.show()

with open('cool_results.json', 'w') as f:
  json.dump(cool_results, f, indent=2)
