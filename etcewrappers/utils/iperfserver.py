#
# Copyright (c) 2015-2018 - Adjacent Link LLC, Bridgewater, New Jersey
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

import shlex
import subprocess
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
        registrar.register_infile_name('iperfserver')

        registrar.register_outfile_name('iperfserver.log')

        registrar.register_argument('interval',
                           None,
                           'iperf measurement interval (iperf -i switch ' \
                           'argument)')

        registrar.register_argument('bufferlen',
                           None,
                           'iperf buffer length (iperf -l switch argument)')

        registrar.register_argument('daemonize',
                           'true',
                           'run as daemon ("true") or in foreground ("false")')


    def run(self, ctx):
        if not ctx.args.infile:
            return

        # some server args can be specifiec via test arguments
        argstr = ''

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

        if not ctx.args.daemonize:
            argstr = '-s %s %s' % (fileargstr, argstr)

            open(ctx.args.outfile, 'w').write('iperf %s' % argstr)

            ctx.run('iperf', argstr, stdout=ctx.args.outfile)
        else:
            daemonize = '-D'

            command = 'iperf -s -D %s %s' % (fileargstr, argstr)

            print command

            with open(ctx.args.outfile, 'w') as stdoutfd:
                stdoutfd.write(command)

                # create the Popen subprocess
                sp = subprocess.Popen(shlex.split(command),
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT)

                # search for the server
                # -----------------------------------
                # Running Iperf Server as a daemon
                # The Iperf daemon process ID : 11331
                pidstr = None
                for line in sp.stdout:
                    stdoutfd.write(line.strip())
                    toks = line.split(':')
                    if len(toks) == 2:
                        pidstr = toks[1]
                        break

                # write the pid to pidfilename
                if pidstr is not None:
                    open(ctx.args.default_pidfilename, 'w').write(pidstr)

                # 7. wait on subprocess
                sp.wait()


    def stop(self, ctx):
        ctx.stop()
        # iperfserver takes some time to close down
        time.sleep(5)
