#
# Copyright (c) 2015-2018 - Adjacent Link LLC, Bridgewater, New Jersey
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

import etce.timeutils
from etce.eelsequencer import EELSequencer
from etce.wrapper import Wrapper


class EmaneEventTDMASchedule(Wrapper):
    """
    Issue TDMA schedule events using emaneevent-tdmaschedule based on events
    listed in the input EEL file. EEL lines require this format:

       TIME NEMIDS tdmaschedule SCHEDULEXMLFILE

    Example: Issue schedule events at time 3.0 and 47.0 to different NEM
             groups.

       3.0  nem:1-5,7 tdmaschedule schedule-003.xml
       47.0 nem:9     tdmaschedule schedule-047.xml
    """

    def register(self, registrar):
        registrar.register_infile_name('scenario.eel')

        registrar.register_outfile_name('tdmaschedule.log')

        registrar.register_argument('eventservicegroup',
                                    '224.1.2.8:45703',
                                    'The Event Service multicast group and port.')

        registrar.register_argument('eventservicedevice',
                                    None,
                                    'Event channel multcast device.')


    def run(self, ctx):
        if not ctx.args.infile:
            return

        if not ctx.args.eventservicedevice:
            message = 'Wrapper emane.emaneeventtdmaschedule mandatory ' \
                      'argument "eventservicedevice" not specified. Quitting.'
            raise RuntimeError(message)

        mcgroup, mcport = ctx.args.eventservicegroup.split(':')

        sequencer = EELSequencer(ctx.args.infile,
                                 ctx.args.starttime,
                                 ('tdmaschedule',))

        for eventlist in sequencer:
            for _, _, _, eventargs in eventlist:
                # parse inputs
                # 0.0   nem:1-5 tdmaschedule tdmaschedules/t000.xml

                schedulexml = eventargs[0]

                # build argstr
                argstr =  \
                          '--device %s --group %s --port %s %s' \
                          % (ctx.args.eventservicedevice, mcgroup, mcport, schedulexml)

                ctx.run('emaneevent-tdmaschedule', argstr, genpidfile=False)

                # and log it
                with open(ctx.args.outfile, 'a') as lf:
                    lf.write('%s: emaneevent-tdmaschedule %s\n' \
                             % (etce.timeutils.getstrtimenow(),
                                argstr))


    def stop(self, ctx):
        pass
