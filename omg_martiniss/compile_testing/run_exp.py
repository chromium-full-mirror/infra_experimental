#!/usr/bin/env python

import argparse
import subprocess
import sys
import uuid

PROJECT = 'martiniss-test-compile-time'
# GB
DISK_SIZE = '200'
SOURCE_SNAPSHOT = 'linux-chromium-rel-ng-snap'

def check_call(args):
  print 'running ' + ' '.join(args)
  subprocess.check_call(args)

def create_disks(name, num_runs, zone, builder):
  names = ['%s-%d' % (name, run) for run in range(num_runs)]
  check_call(['gcloud', 'compute', '--project', PROJECT, 'disks',
              'create'] + names + [
                  '--size', DISK_SIZE, '--zone', zone, '--source-snapshot',
                  '%s-snap' % builder.replace('_', '-'), '--type', 'pd-standard'])

def create_disk(name, zone, builder):
  # gcloud compute --project "martiniss-test-compile-time" disks create
  # "instance-4" --size "50" --zone "us-east1-b" --source-snapshot
  # "linux-chromium-rel-ng" --type "pd-standard"
  check_call(['gcloud', 'compute', '--project', PROJECT, 'disks',
              'create', name, '--size', DISK_SIZE, '--zone', zone,
              '--source-snapshot', '%s-snap' % builder.replace('_', '-'), '--type',
              'pd-standard'])

def get_host_script(builder, machine_type, bot_id, num_iter=1,args=None):
  with open('host.sh') as host_file:
    host_file_c = host_file.read()
  return host_file_c % (builder, machine_type, bot_id, num_iter, args or "")

def custom_name(it):
    return 'custom-cpu-%s-mem-%s' % it

def create_instance(name, zone, builder, machine_type, args=None,
                    num_iter=1, make_disk=True):
  type_name = machine_type
  if isinstance(machine_type, tuple):
    type_name = custom_name(machine_type)
  script = get_host_script(builder, type_name, name, num_iter, args)
  if make_disk:
    create_disk(name, zone, builder)

  args = ['gcloud', 'beta', 'compute', '--project', PROJECT, 'instances',
          'create', name, '--zone', zone]
  if isinstance(machine_type, tuple):
    args += ['--custom-cpu', str(machine_type[0]), '--custom-memory', str(machine_type[1])]
  else:
    args += ['--machine-type', machine_type]

  args += ['--subnet', 'default', '--metadata',
          'startup-script=%s' % script,
          '--maintenance-policy', 'MIGRATE', '--service-account',
          '106689601385-compute@developer.gserviceaccount.com', '--scopes',
          'https://www.googleapis.com/auth/cloud-platform',
          '--min-cpu-platform', 'Automatic', '--disk',
          'name=%s,device-name=%s,mode=rw,boot=yes,auto-delete=yes' % (
              name, name)]
  check_call(args)


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('num_runs', default=1, type=int)
  parser.add_argument('--num_iter', default=1, type=int)
  parser.add_argument('target')
  parser.add_argument('--zone', default='us-east1-b')
  parser.add_argument('--instance-type', default='n1-standard-8')
  parser.add_argument('--custom-cpu')
  parser.add_argument('--custom-memory')
  parser.add_argument('--zones')
  parser.add_argument('--instance_types')
  parser.add_argument('--jobs-arr')
  parser.add_argument('--check', '-c', action='store_true')
  parser.add_argument('--increment', '-i')
  parser.add_argument('--builder', default='linux_chromium_rel_ng')
  args = parser.parse_args()

  if args.zones:
    assert len(args.zones) == args.num_runs, (
        'Number of zones must equal number of runs')

  if args.instance_types:
    assert len(args.instance_types) == args.num_runs, (
        'Number of instance types must equal number of runs')

  jobs_arr = None
  if args.jobs_arr:
    if '-' in args.jobs_arr:
      start, end = (int(x.strip()) for x in args.jobs_arr.split('-'))
      # generate the array ourselves
      if args.increment:
        jobs_arr = [x * int(args.increment) + start for x in range(args.num_runs)]
      else:
        jobs_arr = [start + i * (end - start) / (args.num_runs - 1)
                    for i in range(args.num_runs)]
    else:
      jobs_arr = args.jobs_arr.split(',')
    if not len(jobs_arr) == args.num_runs:
      import pdb; pdb.set_trace()
  if jobs_arr:
    print jobs_arr
    if args.check:
      return

  UID = uuid.uuid4().get_hex()[:8]
  make_disk_every_time = True
  if not args.instance_types and not args.zones:
    print 'batch creating disks'
    it = args.instance_type
    if args.custom_cpu or args.custom_memory:
      it = custom_name((args.custom_cpu or 8, args.custom_memory or 30))
    zone = args.zone
    name = 'run-%s-%s' % (UID, it)
    create_disks(name, int(args.num_runs), zone, args.builder)
    make_disk_every_time = False
  else:
    import pdb; pdb.set_trace()

  for i, run in enumerate(range(args.num_runs)):
    it = args.instance_type
    if args.instance_types:
      it = args.instance_types[i]
    it_name = it
    if args.custom_cpu or args.custom_memory:
      it = (args.custom_cpu or 8, args.custom_memory or 30)
      it_name = custom_name(it)

    zone = args.zone
    if args.zones:
      zone = args.zones[i]

    jobs = 50
    if jobs_arr:
      jobs = jobs_arr[i]

    to_pass = ' '.join(['-j', str(jobs), args.target])
    name = 'run-%s-%s-%d' % (UID, it_name, run)
    create_instance(name, zone, args.builder, it, to_pass,
                    num_iter=args.num_iter, make_disk=make_disk_every_time)

if __name__ == '__main__':
  main()
