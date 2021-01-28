#
# Copyright (c) 2021 - Adjacent Link LLC, Bridgewater, New Jersey
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
import time
from etce.wrapper import Wrapper


class InterfaceCheck(Wrapper):
    '''
    Test that the specified network interface(s) are up before
    proceeding.
    '''

    def register(self, registrar):
        registrar.register_argument(
            'devicenames',
            None,
            'comma separated list of waveform devices. wrapper checks ' \
            'for these before finishing.')

        registrar.register_argument(
            'waitsecs',
            90,
            'number of seconds to wait for the devices ' \
            'to instantiate before quitting')

        registrar.register_infile_name('interfacecheck.flag')

        registrar.run_with_sudo()


    def run(self, ctx):
        pass


    def postrun(self, ctx):
        if not ctx.args.infile:
            return

        if not ctx.args.devicenames:
            print('No devices specified, skipping.')
            return

        devicenames = ctx.args.devicenames.split(',')

        waitsecs = ctx.args.waitsecs

        print('waiting for %s' % ctx.args.devicenames)

        allup = False

        for i in range(waitsecs):
            allup = True

            for devicename in devicenames:
                if ctx.platform.isdeviceup(devicename):
                    print('[%2d]: %s state is UP' % (i, devicename))
                else:
                    allup = False

            time.sleep(1)

            if allup:
                break

        if not allup:
            raise RuntimeError('one or all of devices "%s" not found' % ctx.args.devicenames)


    def stop(self, ctx):
        pass
