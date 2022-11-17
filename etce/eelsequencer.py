#
# Copyright (c) 2015-2019,2022 - Adjacent Link LLC, Bridgewater, New Jersey
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in
#   the documentation and/or other materials provided with the
#   distribution.
# * Neither the name of Adjacent Link LLC nor the names of its
#   contributors may be used to endorse or promote products derived
#   from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#

from __future__ import absolute_import, division, print_function
from collections import defaultdict
import datetime
import math
import os.path
import time

import etce.timeutils


class EELSequencerIterator(object):
    def __init__(self, events, starttime):
        self._events = sorted(events.items())
        self._starttime = starttime
        self._index = 0

    def next(self):
        return self.__next__()

    def __next__(self):
        if self._index >= len(self._events):
            raise StopIteration
        else:
            eventtime, eventlist = self._events[self._index]
            self._index += 1
            self._wait(eventtime, self._starttime)
            return eventlist

    def _wait(self, eventtime, starttime):
        if math.isinf(eventtime) and eventtime < 0:
            return

        nowtime = datetime.datetime.now()
        eventabstime = starttime + datetime.timedelta(seconds=eventtime)
        sleeptime = (eventabstime - nowtime).total_seconds()
        if sleeptime <= 0:
            return
        time.sleep(sleeptime)



class EELSequencer(object):
    '''
    EELSequencer parses an EEL file searching for lines with eventtype
    listed in the eventlist. Clients iterating over the sequencer object
    block until the EEL event time listed in the EEL line (relative to
    starttime).

    required starttime format is YYYY-MM-DDTHH:MM:SS

    Each eelfile event line requires format:

    eventtime moduleid eventtype eventarg*

    Blank lines and comment lines, beginning with "#" are permitted.

    Negative eventtimes value are permitted, as is -Inf which will return
    immediately no matter when encountered.

    eventtimes are expected to be non-decreasing.

    Each iteration returns a tuple (moduleid, eventtype, eventargs*)
    extracted from the EEL file for the corresponding matching line.
    '''
    def __init__(self, eelfile, starttime, eventlist):
        self._starttime = etce.timeutils.strtimetodatetime(starttime)

        self._events = self._parsefile(eelfile, eventlist)


    @property
    def init_events(self):
        return self._events.get(float('-inf'), [])


    @property
    def has_dynamic_events(self):
        return any(filter(lambda x: math.isfinite(x), self._events.keys()))


    def __iter__(self):
        return EELSequencerIterator(self._events, self._starttime)


    def _parsefile(self, eelfile, eventlist):
        events = defaultdict(lambda:[])

        # eelfile must be present
        if not os.path.exists(eelfile):
            raise RuntimeError('EEL file "%s" does not exist' % eelfile)

        # process eel lines
        lineno = 0
        for line in open(eelfile, 'r'):
            lineno += 1
            line = line.strip()

            # skip blank lines
            if len(line) == 0:
                continue

            # skip comment lines
            if line[0] == '#':
                continue
            toks = line.split()

            # skip non-blank lines with too few tokens
            if len(toks) > 0 and len(toks) < 3:
                raise RuntimeError('Malformed EEL line %s:%d' %
                                   (eelfile, lineno))

            eventtime = float(toks[0])
            moduleid = toks[1]
            eventtype = toks[2]
            eventargs = tuple(toks[3:])

            # ignore other events
            if not eventtype in eventlist:
                continue

            events[eventtime].append((eventtime, moduleid, eventtype, eventargs))

        return events
