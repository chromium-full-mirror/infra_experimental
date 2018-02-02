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

def create_disks(name, num_runs, zone):
  names = ['%s-%d' % (name, run) for run in range(num_runs)]
  check_call(['gcloud', 'compute', '--project', PROJECT, 'disks',
              'create'] + names + [
                  '--size', DISK_SIZE, '--zone', zone, '--source-snapshot',
                  SOURCE_SNAPSHOT, '--type', 'pd-standard'])

def create_disk(name, zone):
  # gcloud compute --project "martiniss-test-compile-time" disks create
  # "instance-4" --size "50" --zone "us-east1-b" --source-snapshot
  # "linux-chromium-rel-ng" --type "pd-standard"
  check_call(['gcloud', 'compute', '--project', PROJECT, 'disks',
              'create', name, '--size', DISK_SIZE, '--zone', zone,
              '--source-snapshot', SOURCE_SNAPSHOT, '--type',
              'pd-standard'])

def get_host_script(builder, bot_id):
  with open('host.sh') as host_file:
    host_file_c = host_file.read()
  return host_file_c % (builder, bot_id)

def create_instance(name, zone, builder, machine_type, make_disk=True):
  get_host_script(builder, name)
  if make_disk:
    create_disk(name, zone)

  args = ['gcloud', 'beta', 'compute', '--project', PROJECT, 'instances',
          'create', name, '--zone', zone, '--machine-type', machine_type,
          '--subnet', 'default', '--metadata',
          'startup-script=%s' % get_host_script(builder, name),
          '--maintenance-policy', 'MIGRATE', '--service-account',
          '106689601385-compute@developer.gserviceaccount.com', '--scopes',
          'https://www.googleapis.com/auth/cloud-platform',
          '--min-cpu-platform', 'Automatic', '--disk',
          'name=%s,device-name=%s,mode=rw,boot=yes,auto-delete=yes' % (
              name, name)]
  check_call(args)


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('num_runs', default=1)
  parser.add_argument('--zone', default='us-east1-b')
  parser.add_argument('--instance-type', default='n1-standard-8')
  parser.add_argument('--zones')
  parser.add_argument('--instance_types')
  args = parser.parse_args()

  if args.zones:
    assert len(args.zones) == args.num_runs, (
        'Number of zones must equal number of runs')

  if args.instance_types:
    assert len(args.instance_types) == args.num_runs, (
        'Number of instance types must equal number of runs')

  UID = uuid.uuid4().get_hex()[:8]
  make_disk_every_time = True
  if not args.instance_types and not args.zones:
    print 'batch creating disks'
    it = args.instance_type
    zone = args.zone
    name = 'run-%s-%s' % (UID, it)
    create_disks(name, int(args.num_runs), zone)
    make_disk_every_time = False
  else:
    import pdb; pdb.set_trace()

  for i, run in enumerate(range(int(args.num_runs))):
    it = args.instance_type
    if args.instance_types:
      it = args.instance_types[i]

    zone = args.zone
    if args.zones:
      zone = args.zones[i]

    name = 'run-%s-%s-%d' % (UID, it, run)
    create_instance(name, zone, 'linux_chromium_rel_ng', it,
                    make_disk=make_disk_every_time)

if __name__ == '__main__':
  main()
