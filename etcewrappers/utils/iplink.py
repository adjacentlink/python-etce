#
# Copyright (c) 2014-2018,2020 - Adjacent Link LLC, Bridgewater, New Jersey
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
import shlex
import subprocess
import time

import etce.utils
from etce.wrapper import Wrapper


class IpLink(Wrapper):
    """
    Set interface txqueuelen and mtu. Optionally, periodically
    query interface stats.

    The input file must contain 1 or more lines with the format:

    interface,[txqueuelen],[mtu]

      interface:  the network interface to monitor/control. (required)
      txqueuelen: set the txqueuelen size of the interface. (optional)
      mtu:        set the mtu size of the interface. (optional)

    Optional values should be left empty. Examples:

      eth0,,              # monitor eth0
      eth0,,32768         # monitor eth0 and set its mtu to 32768
      emane0,30000,       # monitor emane0 and set its txqueuelen to 30000
      emane0,30000,32768  # monitor emane0 and set txqueuelen and mtu

    """

    def register(self, registrar):
        registrar.register_argument('testtimesecs',
                                    0,
                                    'Total time to conduct stat queries. "0" ' \
                                    'disables queries.')

        registrar.register_argument('periodsecs',
                                    0,
                                    'Number of seconds between stat queries. "0" ' \
                                    'disables queries. Ignored if testtimesecs ' \
                                    'is "0".')

        registrar.register_infile_name('iplink.script')

        registrar.register_outfile_name('iplink.log')


    def run(self, ctx):
        if not ctx.args.infile:
            return

        interfaces = []
        for line in open(ctx.args.infile):
            interface, txqueuelen, mtu = line.strip().split(',')

            interfaces.append(interface)

            if len(txqueuelen.strip()) > 0:
                txqueuelen = int(txqueuelen)
                if txqueuelen > 0:
                    queuelencommand = 'ip link set %s txqueuelen %d' \
                                      % (interface, txqueuelen)
                    print(queuelencommand)
                    subprocess.call(shlex.split(queuelencommand),
                                    stdin=subprocess.DEVNULL)

            if len(mtu.strip()) > 0:
                mtu = int(mtu)
                if mtu > 0:
                    mtucommand = 'ip link set %s mtu %d' % (interface, mtu)
                    print(mtucommand)
                    subprocess.call(shlex.split(mtucommand),
                                    stdin=subprocess.DEVNULL)


        testtimesecs = ctx.args.testtimesecs

        periodsecs = ctx.args.periodsecs

        if testtimesecs < 0:
            print('testtimesecs is < 0. Quitting.')
            return

        if periodsecs < 0:
            print('periodsecs is < 0. Quitting.')
            return

        if etce.utils.daemonize() > 0:
            return

        testtime = 0
        stdoutfd = open(ctx.args.outfile, 'w')
        retval = 0

        # keep running until we get a non-zero return value (expecting
        # the monitored interface to go away) or our runtime has
        # exceeded the specified total test time
        while retval == 0 and testtime < testtimesecs:
            for interface in interfaces:
                command = 'ip link show %s' % interface
                retval = subprocess.call(shlex.split(command),
                                         stdin=subprocess.DEVNULL,
                                         stdout=stdoutfd)
            time.sleep(periodsecs)
            testtime += periodsecs

        # exit completely instead of returning to next etce step
        sys.exit(0)


    def stop(self, ctx):
        # this wrapper quits when time runs out.
        pass
