#!/usr/bin/env python

import argparse
import base64
import json
import os
import sys
import urllib2
import zlib


def get_builders(filename):
  with open(filename) as f:
    return f.read().strip().splitlines()

def o(name):
  name = name.lower()
  os = 'linux'
  if 'mac' in name:
    os = 'mac'
  elif 'win' in name:
    os = 'win'
  return os


def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument('--project', help='Name of the project.', required=True)
  public = parser.add_mutually_exclusive_group(required=True)
  public.add_argument('--public', action='store_true')
  public.add_argument('--non-public', action='store_true')
  parser.add_argument('--builder-file', required=True)
  args = parser.parse_args()
  assert args.public != args.non_public  # There can only be one.
  return args


def main():
  args = parse_args()

  with open('cr-buildbucket') as f:
    bb_template = f.read()
  with open('luci-scheduler') as f:
    sch_template = f.read()
  with open('luci-logdog') as f:
    logdog_template = f.read()
  with open('luci-milo') as f:
    milo_template = f.read()
  with open('project') as f:
    project_template = f.read()

  builders = get_builders(args.builder_file)
  if args.public:
    readers = 'all'
    swarming_host = 'chromium-swarm'
    recipe_bundle = 'infra/recipe_bundles/chromium.googlesource.com/chromium/tools/build'
    logdog_writers = 'luci-logdog-chromium-writers'
    logdog_bucket = 'chromium-luci-logdog'
  else:
    readers = 'project-%s-readers' % args.project
    swarming_host = 'chrome-swarming'
    recipe_bundle = 'infra_internal/recipe_bundles/chrome-internal.googlesource.com/chrome/tools/build_limited/scripts/slave'
    logdog_writers = 'luci-logdog-%s-writers' % args.project
    logdog_bucket = 'logdog-%s-archive' % args.project

  os.mkdir(args.project)

  with open(os.path.join(args.project, 'cr-buildbucket.cfg'), 'w') as f:
    cib = ''
    trb = ''
    for name in sorted(builders):
      osname = o(name)
      cib += """
    builders {
      name: "%s"
      mixins: "%s"
    }""" % (name, osname)
      trb += """
    builders {
      name: "%s"
      mixins: "%s"
    }""" % (name, osname)
    f.write(bb_template % {
      'project': args.project,
      'readers': readers,
      'swarming_host': swarming_host,
      'recipe_bundle': recipe_bundle,
      'ci_builders': cib,
      'try_builders': trb,
    })

  with open(os.path.join(args.project, 'luci-scheduler.cfg'), 'w') as f:
    triggers = ''
    jobs = ''
    for name in sorted(builders):
      triggers += '  triggers: "%s"\n' % name
      jobs += """
job {
  id: "%s"
  acl_sets: "default"
  buildbucket {
    server: "cr-buildbucket.appspot.com"
    bucket: "luci.%s.ci"
    builder: "%s"
  }
}
""" % (name, args.project, name)
    f.write(sch_template % {
      'project': args.project,
      'readers': readers,
      'triggers': triggers,
      'jobs': jobs
    })

  with open(os.path.join(args.project, 'luci-milo.cfg'), 'w') as f:
    cib = ''
    trb = ''
    for name in sorted(builders):
      cib += """
  builders {
    name: "buildbucket/luci.%s.ci/%s"
    category: "%s"
    short_name: "%s"
  }""" % (args.project, name, name, name[:3])
      trb += """
  builders {
    name: "buildbucket/luci.%s.ci/%s"
  }""" % (args.project, name)
    f.write(milo_template % {
      'project': args.project,
      'ci_builders': cib,
      'try_builders': trb,
    })

  with open(os.path.join(args.project, 'project.cfg'), 'w') as f:
    f.write(project_template % {
      'project': args.project,
      'readers': readers,
    })

  with open(os.path.join(args.project, 'luci-logdog.cfg'), 'w') as f:
    f.write(logdog_template % {
      'readers': readers,
      'writers': logdog_writers,
      'bucket': logdog_bucket,
    })

if __name__ == '__main__':
  sys.exit(main())
