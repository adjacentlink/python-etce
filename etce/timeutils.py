#
# Copyright (c) 2013-2017 - Adjacent Link LLC, Bridgewater, New Jersey
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

import datetime
import time


def getstrtimenow():
    return datetimetostrtime(datetime.datetime.now(), truncate=False)


def datetimetostrtime(dtime, truncate=True):
    if truncate:
        return "%04d-%02d-%02dT%02d:%02d:%02d" % \
            (dtime.year,
             dtime.month,
             dtime.day,
             dtime.hour,
             dtime.minute,
             int(dtime.second))
    else:
        return "%04d-%02d-%02dT%02d:%02d:%09.6f" % \
            (dtime.year,
             dtime.month,
             dtime.day,
             dtime.hour,
             dtime.minute,
             dtime.second)


def strtimetodatetime(referencetime, truncatesecs=True):
    date,time = referencetime.split('T')
    yr,mn,dy = date.split('-')
    hr,mt,sc = time.split(':')
    seconds = float(sc)
    if truncatesecs:
        seconds=int(seconds)
    return datetime.datetime(year=int(yr),
                             month=int(mn),
                             day=int(dy),
                             hour=int(hr),
                             minute=int(mt),
                             second=seconds)


def field_time_now(client, hosts):
    reftimemap = client.execute('timeutils getstrtimenow', [hosts[0]])
    return reftimemap[hosts[0]].retval['result']


def time_offset(referencetimestr, delayseconds, quantizesecs=None):
    referencetime = strtimetodatetime(referencetimestr)
    delta = datetime.timedelta(seconds=int(delayseconds))
    if quantizesecs is None:
        return datetimetostrtime(referencetime + delta, truncate=False)

    # round secs up to next quantization point
    t1 = referencetime + delta
    day = t1.day
    hour = t1.hour
    minute = t1.minute
    second = int(t1.second) + (quantizesecs - int(t1.second)%quantizesecs)
    # account for time rollover. not accounting for month or year rollover
    if second > 59:
        second -= 60
        minute += 1
        if minute > 59:
            minute -= 60
            hour += 1
            if hour > 23:
                hour -= 24
                day += 1
    return datetimetostrtime(datetime.datetime(year=t1.year,
                                               month=t1.month,
                                               day=t1.day,
                                               hour=hour,
                                               minute=minute,
                                               second=second),
                             truncate=True)


def sleep_until(waketimestr, maxsleepsecs=180.0):
    '''
    Sleeps until waketimestr, but not more than maxsleepsecs.

    waketimestr is a string in format YY-MM-DDTHH:MM:SS. If waketimestr is in
    the past an exception is thrown.

    maxsleepsecs is ignored if set less than or equal to 0. If waketimestr
    exceeds maxsleepsecs into the future, an exception is thrown.
    '''
    nowtime = datetime.datetime.now()
    starttime = strtimetodatetime(waketimestr)

    # how long to wait
    waitduration = starttime - nowtime
    waitsecs = waitduration.seconds + (0.000001 * waitduration.microseconds)
    # straddling a midnight boundary?
    if waitsecs < 0.0:
        errormsg = 'waketimestr "%s" has already passed' % \
                   waketimestr
        raise RuntimeError(errormsg)
    if maxsleepsecs > 0:
        if waitsecs > maxsleepsecs:
            errormsg = 'waketimestr "%s" is too far in the future' % \
                       waketimestr
            raise RuntimeError(errormsg)

    time.sleep(waitsecs)
