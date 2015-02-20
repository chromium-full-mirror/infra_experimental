# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Representation of a single attempt by the CQ to test an issue:patchset

import re

class CqAttempt:
    frames_ = [] # Consists of an array of 'frames', each a snapshot in time
    prob = 'mac_chromium_compile_dbg_ngXXXX'
    attempt_number = -2

    def __init__(self, frames=[], attempt_number=-1):
        self.attempt_number = attempt_number
        self.frames_ = sorted(frames,
                              key=lambda x: x['fields']['timestamp'])

    def dump(self):
        if (len(self.frames_) == 0): return "[CqAttempt: no data]"
        mystr = "--{ %s:%s:%d }--\n" % (self.frames_[0]['fields']['issue'],
                                        self.frames_[0]['fields']['patchset'],
                                        self.attempt_number)
        for frame in self.frames_:
            f = frame['fields']
            mystr += " %.6f {%-23.23s}" % (f['timestamp'], f['action'])
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
                if self.prob in all_jobs:
                    mystr += "                   ... %s [%s] %s\n" % (
                        prob, all_jobs[self.prob]['timestamp'],
                        all_jobs[self.prob]['job_state'])
            mystr += "\n"

        return mystr

    def __str__(self):
        return self.dump()
