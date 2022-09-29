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
import os
import time

from etce.wrapper import Wrapper


class Gpsd(Wrapper):
    """
    Run gpsd.
    """

    def register(self, registrar):
        registrar.register_infile_name('gpsd.flag')

        registrar.register_outfile_name('gpsd.log')


    def run(self, ctx):
        if ctx.args.infile is None:
            return

        device = "/dev/pts/1"
        gps_pty = os.path.dirname(ctx.args.outfile) + "/gps.pty"

        retries = 5
        count = 0
        while count < retries:
            try:
                infile = open(gps_pty, 'r')
                device = infile.readline().rstrip()
                infile.close()
                break
            except:
                count += 1
                time.sleep(1)

        argstr = '-P %s/gpsd.pid -G -n -b %s' % (ctx.args.logdirectory, device)

        with open(ctx.args.outfile, 'w') as logf:
            logf.write('gpsd %s\n' % argstr)

        ctx.run('gpsd',
                argstr,
                stdout=ctx.args.outfile,
                stderr=ctx.args.outfile,
                pidincrement=1)


    def stop(self, ctx):
        ctx.stop()
