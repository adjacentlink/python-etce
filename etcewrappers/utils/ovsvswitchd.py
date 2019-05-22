#
# Copyright (c) 2017-2018 - Adjacent Link LLC, Bridgewater, New Jersey
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
from etce.preconditionerror import PreconditionError
import os


class OvsVSwitchd(Wrapper):
    """
    Run an instance of ovs-vswitchd. The input file is an
    empty file (a "flag"). The wrapper runs ovs-vswitchd
    when the file is present.

    This wrapper *requires* the OVS_RUNDIR environment variable to be set
    to the root directory where ovs-vswitchd will create bridge .mgmt
    files for external control. When a new bridge is added, the associated
    .mgmt endpoint is created in: OVS_RUNDIR/HOSTNAME/BRIDGENAME.mgmt to
    receive external commands.
    """

    def register(self, registrar):
        registrar.register_infile_name('ovs-vswitchd.flag')

        registrar.register_outfile_name('ovs-vswitchd.log')

        registrar.register_argument('db_server_port',
                                    9099,
                                    'Listen for commands on the given port. ' \
                                    'Connects to the ovsdb-server via the tcp option.')


    def prerun(self, ctx):
        ctx.stop()

        if not ctx.args.infile:
            return

        ovs_rundir =  os.environ.get('OVS_RUNDIR', None)

        if not ovs_rundir:
            message = 'wrapper ovsvswitchd.py: OVS_RUNDIR environment variable must be specified ' \
                      'but is not set.'
            raise PreconditionError(message)

        # make sure ovs_rundir exists
        if not os.path.exists(ovs_rundir):
            os.makedirs(ovs_rundir)


    def run(self, ctx):
        if not ctx.args.infile:
            return

        ovsvsctlfile=os.path.join(ctx.args.logdirectory,'ovs-vswitchd.ctl')

        ovsvspidfile=ctx.args.default_pidfilename

        argstr = 'tcp:127.0.0.1:%d ' \
                 '-vsyslog:err ' \
                 '-vfile:dbg ' \
                 '--mlockall ' \
                 '--no-chdir ' \
                 '--log-file=%s ' \
                 '--pidfile=%s ' \
                 '--unixctl=%s ' \
                 '--detach ' \
                 % (ctx.args.db_server_port,
                    ctx.args.outfile,
                    ovsvspidfile,
                    ovsvsctlfile)

        ctx.run('ovs-vswitchd', argstr, genpidfile=False)


    def stop(self, ctx):
        ctx.stop()
