#
# Copyright (c) 2014-2018 - Adjacent Link LLC, Bridgewater, New Jersey
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
import time
import random

from etce.wrapper import Wrapper


class SleepWait(Wrapper):
    """
    Sleep and wait for a fixed or randomly selected period.
    """

    def register(self, registrar):
        registrar.register_argument(
            'sleepseconds',
            10.0,
            'The number of seconds to sleep/wait')

        registrar.register_argument(
            'range',
            0.0,
            'A range, centered at "sleepseconds" from which ' \
            'a sleep time is selected. For example for ' \
            'sleepseconds=10.0 and range=10.0, a sleep time ' \
            'time is uniformly selected from the range ' \
            '[5.0,15.0]')


    def run(self, ctx):
        sleepsecsmiddle = ctx.args.sleepseconds

        sleeprange = ctx.args.range

        sleepsecs = random.uniform(sleepsecsmiddle - (sleeprange/2.0),
                                   sleepsecsmiddle + (sleeprange/2.0))

        print('sleepwait sleepsecs=%0.1f' % sleepsecs)

        time.sleep(sleepsecs)


    def stop(self, ctx):
        pass
