#
# Copyright (c) 2019 - Adjacent Link LLC, Bridgewater, New Jersey
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


import os.path
from etce.wrapper import Wrapper


class NRLSMF(Wrapper):
    """
    Run an instance of nrlsmf. The input file should consist of, at most,
    one line of nrlsmf command line arguments, for example:

    merge emane0,lan0 hash MD5

    Comment lines, beginning with '#' are permitted. The
    line should not contain 'log', 'debug' or 'instance' arguments.
    Debug level is passed as a wrapper argument to allow manipulation
    without altering configuration. Logs are written to the wrapper
    outfile. A control socket is created in the output directory. Use
    the 'socketdirectory' parameter to change location.
    """
    def register(self, registrar):
        registrar.register_argument('debuglevel', 0, 'log level')

        registrar.register_argument(
            'socketdirectory',
            None,
            """Directory where the nrlsmf Unix control socket
            is written for runtime control. Default is
            the host output directory for the test trial.
            The socket is named "HOSTNAME_nrlsmf_unix_socket.""")

        registrar.register_infile_name('nrlsmf.conf')

        registrar.register_outfile_name('nrlsmf.log')


    def run(self, ctx):
        if not ctx.args.infile:
            return

        argstr = ''

        conflines = [line.strip() for line
                     in open(ctx.args.infile).readlines()
                     if len(line.strip()) > 0
                     and line[0] != '#']

        # take the last non-comment line as the argument string
        if len(conflines) > 0:
            argstr = conflines[-1]

        socketdirectory = ctx.args.logdirectory

        if ctx.args.socketdirectory:
            socketdirectory = ctx.args.socketdirectory

        argstr += \
            ' instance %s' % \
            os.path.join(socketdirectory,
                         '%s_nrlsmf_unix_socket' % ctx.platform.hostname())

        argstr += \
            ' log %s debug %d' % (ctx.args.outfile, int(ctx.args.debuglevel))

        ctx.daemonize('nrlsmf', argstr)


    def stop(self, ctx):
        ctx.stop()
