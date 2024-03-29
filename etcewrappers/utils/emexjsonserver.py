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
import os

from etce.wrapper import Wrapper


class EmexJsonServer(Wrapper):
    """
    Execute emex-jsonserver to serve Emex Testpoint Probe tables
    and statistics as JSON strings.
    """


    def register(self, registrar):
        '''
        The input file is a mapping of hostname to
        nem and and ip-address.

        <emex-monitor-tag-map>
          <nem>
            <map tag="lteenb-001-r1" nem="1"/>
            <map tag="lteenb-002-r1" nem="2"/>
            <map tag="lteue-001-r1" nem="3"/>
            <map tag="lteue-002-r1" nem="4"/>
          </nem>
          <ip-address>
            <map tag="lteepc-001-h1" ip-address="10.0.1.1"/>
            <map tag="lteue-001-r1" ip-address="10.0.1.2"/>
            <map tag="lteue-002-r1" ip-address="10.0.1.3"/>
          </ip-address>
        </emex-monitor-tag-map>
        '''
        registrar.register_infile_name('emexjsonserver.xml')

        registrar.register_outfile_name('emexjsonserver.log')

        registrar.register_argument('loglevel',
                                    'error',
                                    'log level - one of {critical, error, warning, info, debug}')

        registrar.register_argument('orientation',
                                    'records',
                                    'json format orientation - one of ' \
                                    '{dist, list, series, split, record, index}')

        registrar.register_argument('otestpointendpoint',
                                    '127.0.0.1:9002',
                                    'The opentestpoint-broker publish endpoint from ' \
                                    'which the data is read.')

        registrar.register_argument('clientendpoint',
                                    '127.0.0.1:48001',
                                    'The opentestpoint-broker publish endpoint from ' \
                                    'which the data is read.')


    def run(self, ctx):
        if not ctx.args.infile:
            return
        """
        usage: emex-jsonserver [-h]
                               [--tag-map TAG_MAP]
                               [--verbose]
                               [--pid-file PID_FILE]
                               [--daemonize]
                               [--log-file FILE]
                               [--log-level LEVEL]
                               [--orientation ORIENTATION]
                               [--relative-timestamp]
                               otestpointendpoint
                               clientendpoint

        positional arguments:
          otestpointendpoint    OpenTestPoint publish endpoint.
          clientendpoint        Endpoint where JSON statistics are served.

        optional arguments:
          -h, --help            show this help message and exit
          --tag-map TAG_MAP     tag map XML file.
          --verbose, -v         verbose output [default: False]
          --pid-file PID_FILE   write pid file
          --daemonize, -d       daemonize application [default: False]
          --log-file FILE       log file.
          --log-level LEVEL     log level [default: info].
          --orientation ORIENTATION
                                orientation format of the json output. [default: records].
          --relative-timestamp  Display timestamps relative to the first testpoint report time.
        """
        argstr = '--daemonize ' \
                 '--tag-map %s ' \
                 '--log-level %s ' \
                 '--log-file %s ' \
                 '--pid-file %s ' \
                 '%s ' \
                 '%s ' \
                 % (ctx.args.infile,
                    ctx.args.loglevel,
                    ctx.args.outfile,
                    ctx.args.default_pidfilename,
                    ctx.args.otestpointendpoint,
                    ctx.args.clientendpoint)

        ctx.run('emex-jsonserver', argstr, genpidfile=False)


    def stop(self, ctx):
        ctx.stop()
