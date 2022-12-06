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

from etce.wrapper import Wrapper


class MgenRemote(Wrapper):
    """
    Execute mgen in run-time remote control mode by starting a named
    mgen instance that accepts commands via a unix domain socket.

    For example:

          mgen instance mgen_etce

    Creates an mgen instance with associated socket:

          /tmp/mgen_etce

    """

    def register(self, registrar):
        registrar.register_infile_name('mgenremote.flag')

        registrar.register_outfile_name('mgen.log')

        registrar.register_argument('epochtimestamp',
                                    True,
                                    'Run with mgen epochtimestamp option.')

        registrar.register_argument('ipv6',
                                    False,
                                    'Run in ipv6 mode (True) or ipv4 (False - default)')

        registrar.register_argument('instance',
                                    None,
                                    'The default instance name is mgen-hostname, where hostname'
                                    'is the container hostname. This results in mgen accepting'
                                    'mgen commands on a unix socket at /tmp/mgen-hostname.')

        registrar.register_argument('flush',
                                    True,
                                    'Run mgen in flush log mode')


    def run(self, ctx):
        if not ctx.args.infile:
            return

        argstr = ''

        if ctx.args.epochtimestamp:
            argstr += 'epochtimestamp '

        if ctx.args.flush:
            argstr += 'flush '

        if ctx.args.ipv6:
            argstr += 'ipv6 '

        argstr += 'txlog output %s ' % ctx.args.outfile

        if ctx.args.instance:
            argstr += 'instance %s' % ctx.args.instance
        else:
            argstr += 'instance mgen-%s' % ctx.args.nodename

        ctx.daemonize('mgen', argstr)


    def stop(self, ctx):
        ctx.stop()
