#
# Copyright (c) 2013-2019 - Adjacent Link LLC, Bridgewater, New Jersey
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

import time

from etce.wrapper import Wrapper
from etce.postconditionerror import PostconditionError


class EmaneEventService(Wrapper):
    """
    Run emaneeventservice with the provided configuration file.
    """

    def register(self, registrar):
        registrar.register_argument('loglevel',
                                    3,
                                    'log level - [0,3]')

        registrar.register_argument('daemonize',
                                    True,
                                    'Run as daemon [True, False].')

        registrar.register_infile_name('eventservice.xml')

        registrar.register_outfile_name('emaneeventservice.log')

        registrar.run_with_sudo()


    def run(self, ctx):
        if not ctx.args.infile:
            return

        hourminsec = ctx.args.starttime.split('T')[1]

        daemonize_option = '--daemonize' if ctx.args.daemonize else ''

        argstr = '%s ' \
                 '%s ' \
                 '--realtime ' \
                 '--loglevel %d ' \
                 '--logfile %s ' \
                 '--pidfile %s ' \
                 '--starttime %s' % \
                 (ctx.args.infile,
                  daemonize_option,
                  ctx.args.loglevel,
                  ctx.args.outfile,
                  ctx.args.default_pidfilename,
                  hourminsec)

        ctx.run('emaneeventservice', argstr, genpidfile=False)


    def postrun(self, ctx):
        if not ctx.args.infile:
            return

        time.sleep(1)

        name = 'emaneeventservice'

        pids = ctx.platform.getpids(name)

        if len(pids) == 0:
            e = 'postrun fail: no %s running' % name
            raise PostconditionError(e)

        if len(pids) > 1:
            e = 'postrun fail: multiple %s instances running' % name
            raise PostconditionError(e)


    def stop(self, ctx):
        ctx.stop()
