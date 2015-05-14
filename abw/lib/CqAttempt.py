# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Representation of a single attempt by the CQ to test an issue:patchset

import re
import pprint
from collections import defaultdict
from datetime import datetime
from datetime import timedelta

class CqAttempt:
    frames_ = [] # Consists of an array of 'frames', each a snapshot in time
    attempt_number = -2
    pp1 = pprint.PrettyPrinter(depth=1, indent=2)
    pp2 = pprint.PrettyPrinter(depth=2, indent=2)
    pp3 = pprint.PrettyPrinter(depth=3, indent=2)

    is_typical = True
    not_typical_reason = ''
    is_happy = False
    not_happy_reason = ''

    def __init__(self, frames=[], attempt_number=-1):
        self.attempt_number = attempt_number
        self.frames_ = sorted(frames, # Should already be sorted, but hey
                              key=lambda x: x['fields']['timestamp'])
        self.extract_times_()
        (istypical, reason) = self.decide_is_typical_()
        if (istypical == False):
            self.is_typical = False
            self.not_typical_reason = reason
        self.is_happy, self.not_happy_reason = self.decide_is_happy_()

    def id(self):
        if (len(self.frames_) == 0): return "?:?:?"
        id = "%s:%s:%d" % (self.frames_[0]['fields']['issue'],
                           self.frames_[0]['fields']['patchset'],
                           self.attempt_number)
        return id

    def duration(self,start='patch_start', end='patch_stop'):
        """Integer seconds between two actions. (first instance of each)"""
        return (self.action_times[end][0] -
                self.action_times[start][0]).total_seconds()

    def start_datetime(self):
        return self.action_times['patch_start'][0]

    def parsetimefloat(self, cq_time_float):
        # These are epochs with fractional micros (do the micros survive ?)
        return datetime.utcfromtimestamp(cq_time_float)

    def parsetimestr(self, cq_time_string):
        # Strings happen to be in utc, parser appears to assume UTC, all is well
        if (cq_time_string.find(".") < 0): cq_time_string += ".0"
        return datetime.strptime(cq_time_string, "%Y-%m-%d %H:%M:%S.%f")

    def extract_times_(self):
        """Extract a bunch of key timestamps, job start/end in particular"""
        a = self.action_times = defaultdict(list)
        j = self.job_times = defaultdict(dict)

        for frame in self.frames_:
            f = frame['fields']
            a[f['action']].append(self.parsetimefloat(f['timestamp']))
            if (not f.has_key('jobs')): continue
            for group in f['jobs']:
                for job in f['jobs'][group]:
                    # What if 'job' is a string, not a dict ?
                    # if (not job.has_key('timestamp')): continue
                    tstamp = self.parsetimestr(job['timestamp'])
                    if (group == 'JOB_RUNNING'):
                        j[job['builder']]['start'] = tstamp
                    elif (group == 'JOB_SUCCEEDED'):
                        j[job['builder']]['end'] = tstamp

        if (not self.action_times.has_key('verifier_start')):
            return

        start_t = self.action_times['verifier_start'][0]
        for job in j:
            if (not j[job].has_key('start') or not j[job].has_key('end')):
                j[job]['duration'] = 0
                j[job]['start_offset'] = 0
                self.not_typical_reason = 'cached_jobs'
                continue
            j[job]['duration'] = (j[job]['end'] - j[job]['start']).total_seconds()
            j[job]['start_offset'] = (j[job]['start'] - start_t).total_seconds()
            if (start_t > j[job]['start']):
                self.not_typical_reason = 'job_time-travel'

    def jobnames_by_duration(self):
        return reversed(sorted(self.job_times,
                               key=lambda x: self.job_times[x]['duration']))

    def decide_is_typical_(self):
        # We must have a frame for each of these actions
        for action in ('patch_start', 'verifier_start', 'verifier_pass',
                       'patch_ready_to_commit', 'patch_committed'):
            if (not self.action_times.has_key(action)):
                return (False, "no_%s" % (action))
        # May not have multiple instances of these actions
        for action in ('verifier_start', 'verifier_pass', 'patch_committed'):
            if (len(self.action_times[action])>1):
                return (False, "multiple_%s" % (action))
        # We must not have frames with any of these actions
        for action in ('verifier_skipped', 'verifier_fail',
                       'verifier_retry', 'patch_tree_closed'):
            if (self.action_times.has_key(action)):
                return (False, "%s" % (action))
        # I guess we're typical !
        return (True, '')

    def decide_is_happy_(self):
        if (not self.is_typical): return (False, 'not typical')
        names = list(self.jobnames_by_duration())

        # If the slowest job is kinda slow (>15min), look for outliers
        if (self.job_times[names[0]]['duration'] > 900):
            if (self.job_times[names[0]]['duration'] >
                self.job_times[names[1]]['duration'] * 1.3):
                return (False, "solo_pole:%s" % (names[0]))
            elif(self.job_times[names[1]]['duration'] >
                 self.job_times[names[2]]['duration'] * 1.3):
                n1,n2 = sorted([names[0], names[1]])
                return (False, "dual_pole:%s,%s" % (n1, n2))

        # Jobs that took too long to start (pending)
        for jobname in names:
            if (self.job_times[jobname]['start_offset'] > 180):
                return (False, "slow_job_start:%s" % jobname)

        # Jobs that were queued up to start (or commit)
        if(self.duration('patch_start','verifier_start') > 90):
            return (False, "slow_start")
        elif(self.duration('verifier_pass','patch_committed') > 90):
            return (False, "slow_commit")

        # I guess we're happy !
        return (True, '')

    def dump_times(self):
        mystr = '';
        for job in self.jobnames_by_duration():
            mystr += "{%32.32s} : +% 3d,  % 5d\n" % (
                job,
                self.job_times[job]['start_offset'],
                self.job_times[job]['duration'])
        return mystr
        
    def dump(self):
        if (len(self.frames_) == 0): return "[CqAttempt: no data]"
        mystr = "--{ %s }--\n" % (self.__str__())
        start_t = self.action_times['patch_start'][0]

        for frame in self.frames_:
            f = frame['fields']
            tstamp = self.parsetimefloat(f['timestamp'])
            t_offset = (tstamp - start_t).total_seconds()
            mystr += " %s +% 5ds {%-23.23s}" % (tstamp, t_offset, f['action'])
            if 'jobs' in f:
                counts = {}
                all_jobs = {}
                for group in f['jobs']:
                    counts[group] = len(f['jobs'][group])
                    for job in f['jobs'][group]:
                        all_jobs[job['builder']] = job
                for key in counts:
                    newkey = re.compile('JOB_').sub('', key).lower()
                    mystr += " %s:%d" % (newkey, counts[key])
            mystr += "\n"

        mystr += self.dump_times()
        return mystr

    def __str__(self):
        typical = "typical=%s" % self.is_typical
        happy = ''
        if (not self.is_typical):
            typical += "(%s)" % self.not_typical_reason
        else:
            happy = ", happy=%s" % self.is_happy
            if (not self.is_happy):
                happy += "(%s)" % self.not_happy_reason

        oneline = "%-19.19s % 6ds, %s%s" % (
            self.id(), self.duration(), typical, happy)

        return oneline

        #return self.dump()
