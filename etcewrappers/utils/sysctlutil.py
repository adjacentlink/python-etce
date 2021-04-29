#
# Copyright (c) 2014-2017 - Adjacent Link LLC, Bridgewater, New Jersey
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

from __future__ import absolute_import, division, print_function

import os
try:
    import configparser
except:
    import ConfigParser as configparser

from etce.wrapper import Wrapper


class SysCtlUtil(Wrapper):
    """
    Configure Linux kernel parameters.
    The input file should have format:

      [run]
      kernelparamname=val
      ...

      [stop]
      kernelparamname=val
      ...

    Both "run" and "stop" sections are optional. Named
    parameters are set to the specified value when the
    corresponding wrapper method is called.
    """

    def register(self, registrar):
        registrar.register_infile_name('sysctlutil.conf')


    def run(self, ctx):
        if not ctx.args.infile:
            return

        parser = configparser.SafeConfigParser()
        parser.read(ctx.args.infile)

        if 'run' in parser.sections():
            for name, val in list(parser.items('run')):
                os.system('sysctl -w %s=%s' % (name, val))


    def stop(self, ctx):
        if not ctx.args.infile:
            return

        parser = configparser.SafeConfigParser()
        parser.read(ctx.args.infile)

        if 'stop' in parser.sections():
            for name, val in parser.items('stop'):
                os.system('sysctl -w %s=%s' % (name, val))
