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
import os


class OvsdbServer(Wrapper):
    """
    Run an instance of ovsdb-server. The input file is an
    empty file (a "flag"). The wrapper runs ovsdb-server
    when the file is present.
    """

    def register(self, registrar):
        registrar.register_infile_name('ovsdb-server.flag')

        registrar.register_outfile_name('ovsdb-server.log')

        registrar.register_argument('db_server_port',
                                    9099,
                                    'Listen for commands on the given port. ' \
                                    'Configures the "--remote" option using ' \
                                    'ptcp.')

    def prerun(self, ctx):
        ctx.stop()



    def run(self, ctx):
        if not ctx.args.infile:
            return

        dbfile = os.path.join(ctx.args.logdirectory, 'ovs.db')

        os.system('ovsdb-tool create %s' % dbfile)

        ovsdbctlfile = os.path.join(ctx.args.logdirectory, 'ovsdb-server.ctl')

        ovsdbpidfile = ctx.args.default_pidfilename

        argstr = \
           '%s  ' \
           '-vsyslog:err ' \
           '-vfile:info ' \
           '--remote=ptcp:%d ' \
           '--private-key=db:Open_vSwitch,SSL,private_key ' \
           '--certificate=db:Open_vSwitch,SSL,certificate ' \
           '--bootstrap-ca-cert=db:Open_vSwitch,SSL,ca_cert ' \
           '--no-chdir ' \
           '--log-file=%s ' \
           '--pidfile=%s ' \
           '--unixctl=%s ' \
           '--detach ' \
           % (dbfile,
              ctx.args.db_server_port,
              ctx.args.outfile,
              ovsdbpidfile,
              ovsdbctlfile)

        ctx.run('ovsdb-server', argstr, genpidfile=False)


    def stop(self, ctx):
        ctx.stop()
