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
from collections import defaultdict

from etceanalyzers.otestpoint import OTestpoint


class OTestpointSystem(OTestpoint):
    '''
    Extract System probe CPUs and Processes probe data (when present) from
    the opentestpoint-recorder datafile to an sqlite database for post
    processing.
    '''
    def analyzefile(self, pathinfo, resultfile):
        dbtables = defaultdict(lambda: {})

        probe_table_entries = {
            'System.CPUs': {
                'cpus': ['CPU',
                         'User',
                         'Nice',
                         'System',
                         'Idle',
                         'IOWait',
                         'IRQ',
                         'SoftIRQ',
                         'Steal',
                         'Guest',
                         'GuestNice']},
            'System.Processes': {
                'processes': ['PID',
                              'Command',
                              'Affinity',
                              'User',
                              'System',
                              'Runtime']}
        }

        # call otestpoint analyzer methods to extract and save probes
        self._get_table_values(pathinfo.absdatafile, probe_table_entries, dbtables)

        self._store_tables(resultfile, dbtables)


    def combinetrialresults(self, trialfiles, combinedtrialfile, starttime):
        # let OTestpoint handle
        pass


    def combinesessionresults(self, combinedtrialfiles, sessionresultfile):
        # let OTestpoint handle
        pass
