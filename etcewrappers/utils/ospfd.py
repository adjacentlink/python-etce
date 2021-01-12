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


class Ospfd(Wrapper):
    """
    Run ospfd with the specified ospfd configuration file.
    """
    def register(self, registrar):
        registrar.register_infile_name('ospfd.conf')

        registrar.register_argument('user', 'quagga', 'Run as the specified user.')


    def run(self, ctx):
        if not ctx.args.infile:
            return

        argstr = '-d --user %s -i %s -z /tmp/zebra-%s.sock -f %s' % \
                  (ctx.args.user,
                   ctx.args.default_pidfilename,
                   ctx.args.nodename,
                   ctx.args.infile)

        ctx.run('ospfd', argstr, extra_paths=('/usr/sbin', '/usr/lib/quagga'))


    def stop(self, ctx):
        ctx.stop()
