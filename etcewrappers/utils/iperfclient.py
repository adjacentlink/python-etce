#
# Copyright (c) 2015-2018,2020 - Adjacent Link LLC, Bridgewater, New Jersey
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



class IPerfClient(Wrapper):
    """
    Execute iperf as a client. The iperfclient file should contain, on
    each line, the ip address of the iperf server to connect to followed
    by an (optional) string of iperf client or comment arguments that will
    be appended to the iperf command. Optional arguments should not conflict
    with any arguments specified in the executer file.

    Lines starting with "#" is ignored as comments.

    The client will execute once for each non-comment line found in the
    input file.
    """

    def register(self, registrar):
        registrar.register_infile_name('iperfclient.conf')

        registrar.register_outfile_name('iperfclient.log')

        registrar.register_argument('interval',
                           None,
                           'iperf measurement interval (iperf -i switch ' \
                           'argument)')

        registrar.register_argument('bufferlen',
                           None,
                           'iperf buffer length (iperf -l switch argument)')

        registrar.register_argument('bandwidth',
                           None,
                           'iperf bandwidth (iperf client -b switch argument)')

        registrar.register_argument('transmittime',
                           None,
                           'iperf transmit time (iperf client -t switch ' \
                           'argument)')


    def run(self, ctx):
        if not ctx.args.infile:
            return

        # check for arguments specified as test args
        argsstr = '-o %s' % ctx.args.outfile

        if ctx.args.interval is not None:
            argsstr += ' -i %d ' % ctx.args.interval

        if ctx.args.bufferlen is not None:
            argsstr += ' -l %d ' % ctx.args.bufferlen

        if ctx.args.bandwidth is not None:
            # bandwidth may have a trailing prefix KMG, so may be int osr string
            try:
                argsstr += ' -b %d' % ctx.args.bandwidth
            except:
                argsstr += ' -b %s' % ctx.args.bandwidth

        if ctx.args.transmittime is not None:
            argsstr += ' -t %d' % ctx.args.transmittime

        # run the client for each non-empty, non-comment line found in
        # the input file
        for line in open(ctx.args.infile):
            line = line.strip()

            # skip empty lines and comment lines
            if len(line) == 0 or line[0] == '#':
                continue

            toks = line.split()

            serverip = toks[0]

            fileargsstr = ' '.join(toks[1:])

            argstr = '-c %s %s %s' % (serverip, fileargsstr, argsstr)

            ctx.run('iperf', argstr)


    def stop(self, ctx):
        ctx.stop()
