#
# Copyright (c) 2022 - Adjacent Link LLC, Bridgewater, New Jersey
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
import os

from etce.wrapper import Wrapper



class MgenMonitor(Wrapper):
    """
    Execute mgen-monitor to tail an mgen log and make statistics available
    to the MGEN OpentestPoint probe
    """

    def register(self, registrar):
        # wrapper execution is triggered by an mgen.script file
        # which indicates an associated mgen instance will be present
        registrar.register_infile_name('mgen.script')

        registrar.register_outfile_name('mgen-monitor.log')

        registrar.register_argument('loglevel',
                                    'error',
                                    'log level - one of {critical, error, warning, info, debug}')

        registrar.register_argument('endpoint',
                                    '127.0.0.1:8883',
                                    'The mgen-monitor listen endpoint. ' \
                                    'The MGEN probe connects here.')


    def run(self, ctx):
        if not ctx.args.infile:
            return

        listen_address,listen_port = ctx.args.endpoint.split(':')

        mgen_logfile = os.path.join(ctx.args.outfile, 'mgen.log')

        # mgen-monitor [-h]
        #              [--log-file FILE]
        #              [--log-level LEVEL]
        #              [--pid-file PID_FILE]
        #              [--daemonize]
        #              listen-address listen-port mgen-output-file
        argstr = '--daemonize ' \
                 '--log-level %s ' \
                 '--log-file %s ' \
                 '--pid-file %s ' \
                 '%s ' \
                 '%s ' \
                 '%s ' \
                 % (ctx.args.loglevel,
                    ctx.args.outfile,
                    ctx.args.default_pidfilename,
                    listen_address,
                    listen_port,
                    mgen_logfile)

        ctx.run('mgen-monitor', argstr, genpidfile=False)


    def stop(self, ctx):
        ctx.stop()
