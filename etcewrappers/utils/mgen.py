#
# Copyright (c) 2013-2018 - Adjacent Link LLC, Bridgewater, New Jersey
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

import re

from etce.wrapper import Wrapper



class Mgen(Wrapper):
    """
    Execute mgen with the specified script. This wrapper blocks
    until mgen completes. 
    """

    def register(self, registrar):
        registrar.register_infile_name('mgen.script')

        registrar.register_outfile_name('mgen.log')


    def run(self, ctx):
        if not ctx.args.infile:
            return

        hourminsec = ctx.args.starttime.split('T')[1]

        argstr = 'input %s txlog output %s start %s' % \
            (ctx.args.infile, 
             ctx.args.outfile,
             hourminsec)

        if self._isipv6(ctx.args.infile):
            argstr = 'ipv6 input %s txlog output %s start %s' % \
                (ctx.args.infile, 
                 ctx.args.outfile,
                 hourminsec)                

        ctx.run('mgen', argstr)


    def stop(self, ctx):
        ctx.stop()


    def _isipv6(self, mgenfile):
        #0.0 JOIN FF02:0:0:0:0:0:0:20 INTERFACE emane0
        joinipv6matcher = re.compile(r'\d+.\d+\s+JOIN\s+([0-9A-F:]+)\s+')

        #1.0 ON  11 UDP SRC 5001 DST  FF02:0:0:0:0:0:0:20/5000 PERIODIC [100 1000] INTERFACE emane0
        onipv6matcher = re.compile(r'\d+.\d+\s+ON.*DST\s+([0-9A-F:]+)\s+')

        for line in open(mgenfile, 'r'):
            if joinipv6matcher.match(line):
                return True
            if onipv6matcher.match(line):
                return True

        return False
