#
# Copyright (c) 2019,2022 - Adjacent Link LLC, Bridgewater, New Jersey
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

from etce.wrapper import Wrapper
import os


class SpectrumMonitor(Wrapper):
    """
    Run emane-spectrum-monitor with the provided configuration file.
    """

    def register(self, registrar):
        registrar.register_infile_name('emane-spectrum-monitor.xml')

        registrar.register_outfile_name('emane-spectrum-monitor.log')

        registrar.register_argument('loglevel', 2, 'log level - [0,4]')

        registrar.register_argument('record', False, 'record spectrum data to file')

        registrar.run_with_sudo()


    def run(self, ctx):
        if not ctx.args.infile:
            return

        argstr = '--realtime ' \
                 '--daemonize ' \
                 '--config %s ' \
                 '--loglevel %d ' \
                 '--logfile %s ' \
                 '--pidfile %s' \
                 % (ctx.args.infile,
                    ctx.args.loglevel,
                    ctx.args.outfile,
                    ctx.args.default_pidfilename)

        if ctx.args.record:
            argstr += ' --spectrumquery.recorderfile %s' % \
                      os.path.join(ctx.args.logdirectory, 'emane-spectrum-monitor.data')

        ctx.run('emane-spectrum-monitor', argstr, genpidfile=False)


    def stop(self, ctx):
        ctx.stop()
