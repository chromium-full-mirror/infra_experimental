import csv
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

devices = {}
fieldnames = []
timestamps = []

tiny_outage_filter =  5 * 3600

with open('android_device_statuses.csv') as f:
  reader = csv.DictReader(f)
  raw_fieldnames = reader.fieldnames
  # throws out dupes (moved devices)
  for row in reader:
    if row['metric:builder'] == 'linux_android_rel_ng':
      devices[row['metric:device_id']] = row

  for name in raw_fieldnames:
    try:
      intname = int(name)
      timestamps.append(intname)
    except ValueError:
      fieldnames.append(name)

timestamps = sorted(timestamps)


device_connection_events = {}

for device, row in devices.iteritems():
  device_connection_events[device] = []
  raw_status = [(t, row[str(t)]) for t in timestamps if row[str(t)]]
  for l, r in zip(raw_status[:-1], raw_status[1:]):
    if l[1] == 'good' and r[1] != 'good':
      device_connection_events[device].append((r[0], 'down', row['hostname']))
    elif l[1] != 'good' and r[1] == 'good':
      device_connection_events[device].append((r[0], 'up', row['hostname']))

all_good = [device for device, row in devices.iteritems()
    if all(row[str(t)] == 'good' or not row[str(t)] for t in timestamps) and
       any(row[str(t)] == 'good' for t in timestamps)]


sanitized_connection_events = {}
for device, raw_events in device_connection_events.iteritems():
  sanitized_connection_events[device] = []
  stack = []
  for event in raw_events:
    if event[1] == 'down' and not stack:
      continue
    elif event[1] == 'up' and not stack:
      stack.append(event)
    elif event[1] == 'down' and stack:
      stack.append(event)
    elif event[1] == 'up' and stack:
      latest = stack[-1]
      assert latest[1] == 'down'
      if (event[0] - latest[0]) < (tiny_outage_filter * 1000000):
        stack.pop()
        continue
      sanitized_connection_events[device].append(stack[0])
      sanitized_connection_events[device].append(stack[1])
      stack = [event]

offline_spans = {}
online_spans = {}

for device, events in sanitized_connection_events.iteritems():
  if not events:
    continue
  offline_spans[device] = []
  online_spans[device] = []
  for l, r in zip(events[:-1], events[1:]):
    if l[1] == 'down' and r[1] == 'up':
      offline_spans[device].append((l[2], device, l[0], float(r[0] - l[0]) / 1000000.0))
    if l[1] == 'up' and r[1] == 'down':
      online_spans[device].append((l[2], device, l[0], float(r[0] - l[0]) / 1000000.0))


print 'total_devices, all good, eventful devices', len(device_connection_events), len(all_good), len(online_spans)
online_numbers = []
for dev, span in online_spans.iteritems():
  online_numbers.extend((dev, s[3] / 3600, 1) for s in span)

for dev in all_good:
  online_numbers.append((dev, 12 * 168, 1))

#for dev, median, cnt in sorted(online_numbers, key=lambda x: x[1]):
#  print '%s: %s (over %s times)' % (dev, median, cnt)

print '%d data points' % len(online_numbers)
print 'mean of all points %f' % np.mean([x[1] for x in online_numbers])
sns.distplot([x[1] for x in online_numbers], bins=50, kde=False)
plt.show()
