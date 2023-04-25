#
# Copyright (c) 2023 - Adjacent Link LLC, Bridgewater, New Jersey
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


class EmaneJammerSimpleService(Wrapper):
    """
    Run emane-jammer-simple-service with the provided configuration file.
    """

    def register(self, registrar):
        registrar.register_argument('loglevel', 'info', 'one of {critical, error, warning, info, debug, notset}')

        registrar.register_infile_name('emane-jammer-simple-service.xml')

        registrar.register_outfile_name('emane-jammer-simple-service.log')


    def run(self, ctx):
        if not ctx.args.infile:
            return

        """
        -h, --help           show this help message and exit
        --config-file FILE   plugin config file.
        --log-file FILE      log file.
        --log-level LEVEL    log level [default: info].
        --pid-file PID_FILE  write pid file
        --daemonize, -d      daemonize application [default: False]
        """
        argstr = '--daemonize ' \
                 '--config-file %s ' \
                 '--log-level %s ' \
                 '--log-file %s ' \
                 '--pidfile %s ' \
                 'emane_jammer_simple.service.plugin.Plugin' \
                 % (ctx.args.infile,
                    ctx.args.loglevel,
                    ctx.args.outfile,
                    ctx.args.default_pidfilename)

        ctx.run('waveform-resourced', argstr, genpidfile=False)


    def stop(self, ctx):
        ctx.stop()
