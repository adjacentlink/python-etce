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


class SMCRouted(Wrapper):
    """
    Run smcrouted with the specified smcrouted configuration file.
    """
    def register(self, registrar):
        registrar.register_infile_name('smcrouted.script')

        registrar.register_outfile_name('smcrouted.log')

        registrar.register_argument(
            'N',
            False,
            '''
            Invoke the smcrouted -N options which
            which requires the user to add each interface to the router.
            In configuration this requires a "phyint" sentence for every
            interface that needs to be included for multicast routing.
            In the default mode, all interfaces are available for multicast at start up.
            ''')


    def run(self, ctx):
        if not ctx.args.infile:
            return

        argstr = '-P %s -f %s -I %s' % \
                 (ctx.args.default_pidfilename, ctx.args.infile, ctx.args.nodename)

        if ctx.args.N:
            argstr = '-N ' + argstr

        ctx.run('smcrouted',
                argstr,
                genpidfile=False,
                stdout=ctx.args.outfile,
                stderr=ctx.args.outfile)


    def stop(self, ctx):
        ctx.stop()
