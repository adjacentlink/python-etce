#
# Copyright (c) 2015,2017 - Adjacent Link LLC, Bridgewater, New Jersey
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
from pandas import DataFrame
from etceanalytics import utils
from etceanalytics.analyzer import Analyzer


class EmaneConfig(Analyzer):
    '''
    Parse emane configuration snapshot and save to csv file
    '''
    def __init__(self, ctx):
        pass


    @property
    def input_file(self):
        return 'emaneconfig.log'


    @property
    def file_fields(self):
        return ('emaneconfig', 'csv')


    def analyzefile(self, pathinfo, resultfile):
        #                      nem 1 2-phy propagationmodel = precomputed
        matcher = re.compile(r'nem (\d+) ([\w\-]+) (\w+) = (\w+)')

        vals = {'nemid':[], 'layer':[], 'name':[], 'val':[]}

        for line in open(pathinfo.absdatafile):
            match = matcher.match(line)

            if match:
                nemid, layername, name, val = match.groups()

                vals['nemid'].append(nemid)

                vals['layer'].append(layername)

                vals['name'].append(name)

                vals['val'].append(val)

        df = DataFrame(vals)

        df.to_csv(resultfile,
                  columns=['nemid', 'layer', 'name', 'val'])


    def combinetrialresults(self, trialfiles, combinedtrialfile, starttime):
        concatdf = utils.concat_csv_trial_files(trialfiles)

        concatdf.to_csv(combinedtrialfile,
                        columns=['nemid', 'layer', 'name', 'val'])


    def combinesessionresults(self, combinedtrialfiles, sessionresultfile):
        concatdf = utils.concat_csv_session_files(combinedtrialfiles)

        concatdf.to_csv(sessionresultfile,
                        columns=['trial', 'nemid', 'layer', 'name', 'val'])
