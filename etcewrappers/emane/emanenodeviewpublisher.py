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


class EmaneNodeViewPublisher(Wrapper):
    """
    Run an instance of emane-node-view-publisher.

    emane-node-view-publisher is usually run from a virtual
    environment or from a built directory. Use pythonpath
    and path arguments to points to the local installation.
    """

    def register(self, registrar):
        registrar.register_infile_name('emane-node-view-publisher.xml')
        registrar.register_outfile_name('emane-node-view-publisher.log')
        registrar.register_argument('path',
                                    '/opt/emane-node-view/bin',
                                    'PATH to built emane-node-view-publisher script.')


    def run(self, ctx):
        if not ctx.args.infile:
            return

        cmdline = '%s/emane-node-view-publisher %s' % (ctx.args.path, ctx.args.infile)

        logfile = '%s/emane-node-view-publisher.log' % ctx.args.logdirectory

        subprocess.Popen(shlex.split(cmdline),
                         stdout=open(logfile, 'w+'),
                         stderr=subprocess.STDOUT)

        print(cmdline)


    def stop(self, ctx):
        pass
