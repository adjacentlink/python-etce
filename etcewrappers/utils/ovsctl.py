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

from __future__ import absolute_import, division, print_function
import os
import time

from etce.utils import daemonize
from etce.eelsequencer import EELSequencer
from etce.preconditionerror import PreconditionError
from etce.wrapper import Wrapper


class OvsCtl(Wrapper):
    """
    Send a sequence of ovs-vsctl and ovs-ofctl to an ovs-vswitchd instance.
    This wrapper *requires* the OVS_RUNDIR environment variable to be set
    to the root directory where the associated ovs-vswitchd instance creates
    bridge .mgmt files for each of its bridges. Commands in the input file
    are sent to OVS_RUNDIR/HOSTNAME/BRIDGENAME.mgmt for processing.

    The input file contains a mix of 2 recognized EEL sentences:

       1. ovs-vsctl format line

          TIME openvswitch ovs-vsctl OVS-VSCTL-COMMAND [OVS-VSCTL-ARGS]

          example:
             Add  a bridge called ovsbr0 and then add a port called lan0 to ovsbr0

             -Inf  openvswitch ovs-vsctl add-br ovsbr0
             -Inf  openvswitch ovs-vsctl add-port ovsbr0 lan0

       2. ovs-ovctl format line

          TIME openvswitch ovs-ofctl OVS-OFCTL-COMMAND [OVS-OFCTL-ARGS]

          example:
             At time T=0.0, delete all flows for bridge ovsbr0 then
             at time T=1.0, add a default flow rule to drop all packets.

              0.0  openvswitch ovs-ofctl del-flows ovsbr0
              1.0  openvswitch ovs-ofctl add-flow ovsbr0 priority=1,actions=drop
    """

    def register(self, registrar):
        registrar.register_infile_name('ovsctl.script')

        registrar.register_outfile_name('ovsctl.log')

        registrar.register_argument('daemonize',
                                    'true',
                                    'run as a daemon (true) or not (false)')

        registrar.register_argument('db_server_port',
                                    9099,
                                    'Listen for commands on the given port. ' \
                                    'Connects to the ovsdb-server via the tcp option.')


    def prerun(self, ctx):
        ctx.stop()

        ovs_rundir = os.environ.get('OVS_RUNDIR', None)

        if not ovs_rundir:
            message = 'wrapper ovsctl.py: OVS_RUNDIR environment variable must be specified ' \
                      'but is not set.'
            raise PreconditionError(message)


    def _build_ovs_vsctl_argstr(self, ctx, eventargs):
        return '--db=tcp:127.0.0.1:%d %s' % (ctx.args.db_server_port, ' '.join(eventargs))


    def _build_ovs_ofctl_argstr(self, ctx, eventargs):
        if len(eventargs) < 2:
            message = 'wrapper ovsctl.py: all ovs-ofctl sentences must specify the switch name ' \
                      'after the command'
            raise RuntimeError(message)

        ovs_rundir = os.environ.get('OVS_RUNDIR', None)

        ofcommand, switch = eventargs[0:2]

        argstr = '%s %s/%s.mgmt' % (ofcommand, ovs_rundir, switch)

        if len(eventargs) > 2:
            argstr = argstr + ' ' + ' '.join(eventargs[2:])

        return argstr


    def run(self, ctx):
        if not ctx.args.infile:
            return

        if ctx.args.daemonize:
            if daemonize() != 0:
                return

        ovsvsctlfile = os.path.join(ctx.args.logdirectory, 'ovs-vswitchd.ctl')

        sequencer = EELSequencer(ctx.args.infile,
                                 ctx.args.starttime,
                                 ('ovs-vsctl', 'ovs-ofctl'))

        builders = {'ovs-vsctl': self._build_ovs_vsctl_argstr,
                    'ovs-ofctl': self._build_ovs_ofctl_argstr}

        with open(ctx.args.outfile, 'w') as logf:
            for eventlist in sequencer:
                for _, moduleid, eventtype, eventargs in eventlist:
                    if not moduleid == 'openvswitch':
                        continue

                    if not eventtype in builders:
                        print('wrapper ovsctl.py: Warning, skipping unsupported event type "%s"')
                        continue

                    argstr = builders[eventtype](ctx, eventargs)

                    logf.write('%0.6f %s\n' % (time.time(), command))

                    ctx.run(eventtype, argstr, genpidfile=False)


    def stop(self, ctx):
        ctx.stop()
