#
# Copyright (c) 2018,2022 - Adjacent Link LLC, Bridgewater, New Jersey
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
from collections import defaultdict
import math
import itertools
import re
import sys

import etce.timeutils
from etce.utils import nodestr_to_nodelist,daemonize
from etce.eelsequencer import EELSequencer
from etce.wrapper import Wrapper

try:
    from emane.events import EventService, LocationEvent, PathlossEvent, AntennaProfileEvent
except:
    from emanesh.events import EventService, LocationEvent, PathlossEvent, AntennaProfileEvent



class POV(object):
    def __init__(self):
        self._position = None
        self._orientation = None
        self._velocity = None
        self._dirty = False

    @property
    def position(self):
        return self._position

    @property
    def position(self, lat, lon, alt):
        self._position = (lat, lon, alt)
        self._dirty = True

    @property
    def orientation(self):
        return self._orientation

    @property
    def orientation(self, pitch, roll, yaw):
        self._orientation = (pitch, roll, yaw)
        self._dirty = True

    @property
    def velocity(self):
        return self._velocity

    @property
    def velocity(self, azimuth, elevation, speed):
        self._velocity = (azimuth, elevation, speed)
        self._dirty = True

    @property
    def dirty(self):
        return self._dirty

    def read_reset(self):
        self._dirty = False
        return (self._location, self._orientation, self._velocity)



class EmanePhyInit(Wrapper):
    """
    Send EMANE PHY Layer Events to set initial network conditions.

    This wrapper takes an EEL file as input. It currently recognizes these sentences:

       1. EMANE pathloss sentences of format:

          TIME nem:ID pathloss [nem:ID,PATHLOSS]+

          example:
           Set bidirectional pathloss between nem 1 and nems 2-7 to 90 and
           nem 1 and nem 8 to 200:

           -Inf  nem:1 pathloss nem:2,90 nem:3,90 nem:4,90 nem:5,90 nem:6,90 nem:7,90 nem:8,200


       2. EMANE location event sentences with latitute, longitude and altitude only:

          TIME nem:ID location gps LATITUDE,LONGITUDE,ALTITUDE

          LATITUDE and LONGITUDE units are degrees. ALTITUDE unit is meters.

          example:
           Set nem 3 location to 40.025495,-74.315441,3.0:

           -Inf  nem:3 location gps 40.025495,-74.315441,3.0


       3. EMANE orientation event sentences with pitch, roll and yaw.
          Note orientation sentences must be specified with (and after)
          an associated location sentence.

          TIME nem:ID orientation PITCH,ROLL,YAW

          PITCH,ROLL,YAW units are degrees.

          example:
           Set nem 3 pitch roll and yaw to 3.0,4.0,5.0

           -Inf  nem:3 orientation 3.0,4.0,5.0


       4. EMANE velocity event sentences with azimuth, elevation and magnitude.
          Note velocity sentences must be specified with (and after)
          an associated location sentence.

          TIME nem:ID velocity AZIMUTH,ELEVATION,MAGNITUDE

          AZIMUTH and ELEVATION units are degrees. Magnitude units is meters/second.

          example:
           -Inf  nem:3 velocity 30.0,20.0,200.0


       5. EMANE fadingselection event (emane >= 1.2.1) of format:

          TIME nem:ID fadingselection nem:ID,none|nakagami [nem:ID,none|nakagami]*

          example:
           Send fading selection event to nem 4 selecting none for nem 1 and
           nakagami for nems 2 and 3:

           -Inf nem:4 fadingselection nem:1,none nem:2,nakagami nem:3,nakagami


       6. An allinformedpathloss sentence of format:

          TIME nem:ID[(,|-)ID]* allinformedpathloss PATHLOSS

          PATHLOSS units is dB.

          example:
           Set forward and reverse pathloss between all pairs of nems 1,2 3 and 7 to 90:

           -Inf  nem:1-3,7 allinformedpathloss 90

       5. EMANE antennaprofile event of format:

          TIME nem:ID antennaprofile PROFILEID,AZIMUTH,ELEVATION

          AZIMUTH and ELEVATION units are degrees.

          example:
           Set nem 4 antenna profile to 3 with azimuth 195 and elevation 45:

           4.0 nem:4 antennaprofile 3,195,45


    As shown in all of the examples, the wrapper accepts negative time values and,
    especially, a time value of -Inf (negative infinity) which means send the event
    immediately. All finite event times are offset from the test start time.

    """

    def register(self, registrar):
        registrar.register_infile_name('emanephyinit.eel')

        registrar.register_outfile_name('emanephyinit.log')

        registrar.register_argument('eventservicegroup',
                                    '224.1.2.8:45703',
                                    'The Event Service multicast group and port.')

        registrar.register_argument('eventservicedevice',
                                    None,
                                    'Event channel multcast device.')


    def run(self, ctx):
        if not ctx.args.infile:
            return

        # position, orientation and velocities are specified as separate
        # EEL sentences - however orientation and velocity events must
        # be specified with their associated location triplets.
        # Store the most recently specified location for each nem and
        # reuse it as optional orientation and velocity sentences are
        # parsed.
        self._location_cache = {}

        handlers = {
            'allinformedpathloss':self.allinformed_pathloss,
            'location':self.location_gps,
            'orientation':self.orientation,
            'velocity':self.velocity,
            'pathloss':self.pathloss,
            'fadingselection':self.fadingselection,
            'antennaprofile':self.antennaprofile
        }

        if not ctx.args.eventservicedevice:
            message = 'Wrapper emane.emanephyinit mandatory argument "eventservicedevice" ' \
                      'not specified. Quitting.'
            raise RuntimeError(message)

        mcgroup,port = ctx.args.eventservicegroup.split(':')

        sequencer = EELSequencer(ctx.args.infile,
                                 ctx.args.starttime,
                                 list(handlers.keys()))

        service = EventService((mcgroup, int(port), ctx.args.eventservicedevice))

        with open(ctx.args.outfile, 'w+') as lfd:
            print('process infile "%s"' % ctx.args.infile)

            for eventtime,moduleid,eventtype,eventargs in sequencer.init_events:
                events = handlers[eventtype](moduleid, eventtype, eventargs)

                for nem,event in list(events.items()):
                    service.publish(nem, event)

                logline = 'process eventtype "%s" to nems {%s}' % \
                    (eventtype, ','.join(map(str, sorted(events.keys()))))

                self.log(lfd, logline)

        # return if there are no non-initialization events
        if not sequencer.has_dynamic_events:
            return

        # otherwise daemonze and carry on
        print('daemonize for dynamic events')
        if daemonize() > 0:
            return

        # reopen after daemonize
        service2 = EventService((mcgroup, int(port), ctx.args.eventservicedevice))

        # and log
        with open(ctx.args.outfile, 'a') as lfd:
            try:
                for eventlist in sequencer:
                    for eventtime, moduleid, eventtype, eventargs in eventlist:
                        if math.isinf(eventtime):
                            continue

                        events = handlers[eventtype](moduleid, eventtype, eventargs)

                        for nem,event in list(events.items()):
                            service2.publish(nem, event)

                        logline = 'process eventtype "%s" to nems {%s}' % \
                                  (eventtype, ','.join(map(str, sorted(events.keys()))))

                        self.log(lfd, logline)

            except Exception as e:
                self.log(lfd, e)

        # exit from daemonized path
        sys.exit(0)


    def allinformed_pathloss(self, moduleid, eventtype, eventargs):
        # -Inf  nem:1-3,7 allinformedpathloss 90
        nems = nodestr_to_nodelist(moduleid.split(':')[1])

        pathloss = float(eventargs[0])

        events = defaultdict(lambda: PathlossEvent())

        for x, y in itertools.product(nems, nems):
            if x == y:
                # ignore self node pathloss
                continue

            events[x].append(y, forward=pathloss)

            events[y].append(x, forward=pathloss)

        return events


    def location_gps(self, moduleid, eventtype, eventargs):
        # -Inf   nem:45 location gps 40.025495,-74.315441,3.0
        location_nem = int(moduleid.split(':')[1])

        toks = eventargs[1].split(',')

        lat, lon, alt = list(map(float, toks[0:3]))

        self._location_cache[location_nem] = (lat,lon,alt)

        events = defaultdict(lambda: LocationEvent())

        # all events are sent to nemid 0 - ie, received by every nem
        events[0].append(location_nem, latitude=lat, longitude=lon, altitude=alt)

        return events


    def orientation(self, moduleid, eventtype, eventargs):
        # -Inf   nem:45 orientation 3.0,4.0,5.0
        nem = int(moduleid.split(':')[1])

        if not nem in self._location_cache:
            raise ValueError('An orientation EEL sentence for nem "%d" '
                             'has been specified without an associated '
                             'location sentence. Quitting.'
                             % nem)

        toks = eventargs[0].split(',')

        lat, lon, alt = self._location_cache[nem]

        pitch, roll, yaw = list(map(float, toks[0:3]))

        events = defaultdict(lambda: LocationEvent())

        events[0].append(nem,
                         latitude=lat,
                         longitude=lon,
                         altitude=alt,
                         pitch=pitch,
                         roll=roll,
                         yaw=yaw)

        return events


    def velocity(self, moduleid, eventtype, eventargs):
        # -Inf   nem:45 velocity 30.0,20.0,200.0
        nem = int(moduleid.split(':')[1])

        if not nem in self._location_cache:
            raise ValueError('A velocity EEL sentence for nem "%d" '
                             'has been specified without an associated '
                             'location sentence. Quitting.'
                             % nem)

        toks = eventargs[0].split(',')

        lat, lon, alt = self._location_cache[nem]

        azimuth, elevation, magnitude = list(map(float, toks[0:3]))

        events = defaultdict(lambda: LocationEvent())

        events[0].append(nem,
                         latitude=lat,
                         longitude=lon,
                         altitude=alt,
                         azimuth=azimuth,
                         elevation=elevation,
                         magnitude=magnitude)

        return events


    def fadingselection(self, moduleid, eventtype, eventargs):
        from emane.events import FadingSelectionEvent

        # -Inf   nem:4 fadingselection nem:1,none nem:2,nakagami
        nem = int(moduleid.split(':')[1])

        events = defaultdict(lambda: FadingSelectionEvent())

        for eventarg in eventargs:
            m = re.match('nem:(?P<nem>\d+),(?P<model>\w+)', eventarg)

            # all events are sent to nemid 0 - ie, received by every nem
            events[0].append(int(m.group('nem')), model=m.group('model'))

        return events


    def pathloss(self, moduleid, eventtype, eventargs):
        # -Inf  nem:1 pathloss nem:2,90 nem:3,90 nem:4,90 nem:5,90 nem:6,90 nem:7,90 nem:8,200
        sending_nem = int(moduleid.split(':')[1])

        receiving_nems = {}

        for eventarg in eventargs:
            receiving_nem, pathloss = eventarg[eventarg.find(':')+1:].split(',')

            receiving_nems[int(receiving_nem)] = float(pathloss)

        events = defaultdict(lambda: PathlossEvent())

        for x, y in itertools.product([sending_nem], receiving_nems):
            if x == y:
                # ignore self node pathloss
                continue

            events[x].append(y, forward=receiving_nems[y])

            events[y].append(x, forward=receiving_nems[y])

        return events


    def antennaprofile(self, moduleid, eventtype, eventargs):
        # TIME nem:ID antennaprofile profileid,azimuth,elevation
        nem = int(moduleid.split(':')[1])

        events = defaultdict(lambda: AntennaProfileEvent())

        for eventarg in eventargs:
            profileid, azimuth, elevation = eventarg.split(',')

            events[0].append(nemId=nem, profile=int(profileid), azimuth=float(azimuth), elevation=float(elevation))

        return events


    def log(self, lfd, log):
        lfd.write('%s: %s\n' % (etce.timeutils.getstrtimenow(), log))

        lfd.flush()


    def stop(self, ctx):
        pass
