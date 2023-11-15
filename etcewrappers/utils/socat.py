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

import os
import shlex
import subprocess
from etce.wrapper import Wrapper
from etce.timeutils import getstrtimenow


class Socat(Wrapper):
    """
    Issue socat commands. The input files should consist
    of any valid arguments to the socat command listed one per line.
    Comment lines starting with '#" are permitted. For example:

     TCP-LISTEN:5001,fork,reuseaddr helper:9001
     TCP-LISTEN:5002,fork,reuseaddr helper:9002

    """

    def register(self, registrar):
        registrar.register_infile_name('socat.script')
        registrar.register_outfile_name('socat.log')


    def run(self, ctx):
        if not ctx.args.infile:
            return

        with open(ctx.args.outfile, 'a') as lfd:
            for linenum,line in enumerate(open(ctx.args.infile), start=1):
                # skip comments
                if line.startswith('#'):
                    continue

                # skip empty lines
                argstr = line.strip()

                if len(argstr) == 0:
                    continue

                cmdline = 'socat -lf%s %s' % \
                    (os.path.join(ctx.args.logdirectory,
                                  'socat.%d.log' % linenum), argstr)

                subprocess.Popen(shlex.split(cmdline),
                                 stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.STDOUT)

                print(cmdline)

                lfd.write('%s: %s\n' % (getstrtimenow(), cmdline))


    def stop(self, ctx):
        pass
