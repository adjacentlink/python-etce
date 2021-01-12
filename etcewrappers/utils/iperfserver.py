#
# Copyright (c) 2015-2018,2020 - Adjacent Link LLC, Bridgewater, New Jersey
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

from etce.wrapper import Wrapper



class IPerfServer(Wrapper):
    """
    Execute iperf as a server. The iperfserver file should contain, at
    most, one line of iperf common and server options. The iperf server
    command will be built as 'iperf -s [file options] [arg values]. Lines
    starting with "#" is ignored as comments. If multiple non-comment
    lines are found, only the last one is used.
    """

    def register(self, registrar):
        registrar.register_infile_name('iperfserver.conf')

        registrar.register_outfile_name('iperfserver.log')

        registrar.register_argument('interval',
                           None,
                           'iperf measurement interval (iperf -i switch ' \
                           'argument)')

        registrar.register_argument('bufferlen',
                           None,
                           'iperf buffer length (iperf -l switch argument)')


    def run(self, ctx):
        if not ctx.args.infile:
            return

        # run as daemon, log to output file and add argument specified via input file
        argstr = '-D -o %s' % ctx.args.outfile

        if ctx.args.interval is not None:
            argstr += ' -i %d ' % ctx.args.interval

        if ctx.args.bufferlen is not None:
            argstr += ' -l %d ' % ctx.args.bufferlen

        fileargstr = ''

        serverarglines = [ line.strip() for line
                           in open(ctx.args.infile).readlines()
                           if len(line.strip()) > 0
                           and line[0] != '#']

        # take the last non-comment line as the iperf input
        if len(serverarglines) > 0:
            fileargstr = serverarglines[-1]

        argstr = '-s %s %s' % (fileargstr, argstr)

        ctx.run('iperf', argstr)


    def stop(self, ctx):
        ctx.stop()
        # iperfserver takes some time to close down
        time.sleep(5)
