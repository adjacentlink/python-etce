#
# Copyright (c) 2015-2021 - Adjacent Link LLC, Bridgewater, New Jersey
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
import logging
import os
from collections import defaultdict
from etceanalytics.analyzerloader import AnalyzerLoader


class AnalyzerManager(object):
    def __init__(self, config):
        self._cache = {}

        self._loader = AnalyzerLoader(config)


    def analyzefile(self, pathinfo, resultdir, noreanalyze):
        resultfiles = defaultdict(lambda: [])

        for analyzername, analyzer in self._loader.load_by_datafile(pathinfo.datafile):
            file_root, file_suffix = analyzer.file_fields

            resultfile = os.path.join(resultdir,
                                      '%s-%s.%s' \
                                      % (pathinfo.hostname, file_root, file_suffix))

            if not os.path.isfile(resultfile) or not noreanalyze:
                analyzer.analyzefile(pathinfo, resultfile)

                logging.info('analyzefile %s: %s to %s',
                             analyzername,
                             pathinfo.absdatafile,
                             resultfile)

                resultfiles[analyzername].append(resultfile)

        return resultfiles


    def combinetrialresults(self, resultfiles, resultdir, analyzername, starttime):
        combinedtrialfiles = {}

        analyzer = self._loader.load_by_analyzer(analyzername)

        file_root, file_suffix = analyzer.file_fields

        combinedtrialfile = os.path.join(resultdir, '.'.join([file_root, file_suffix]))

        logging.info('combinetrialresults %s: %s', analyzername, combinedtrialfile)

        analyzer.combinetrialresults(resultfiles, combinedtrialfile, starttime)

        combinedtrialfiles[analyzername] = combinedtrialfile

        return combinedtrialfile


    def combinesessionresults(self,
                              trialfiles,
                              sessionresultsdir,
                              testname,
                              analyzername):
        analyzer = self._loader.load_by_analyzer(analyzername)

        file_root, file_suffix = analyzer.file_fields

        resultfile = '%s-%s.%s' % (file_root, testname, file_suffix)

        absresultfile = os.path.join(sessionresultsdir, resultfile)

        logging.info('combinesessionresults %s: %s', analyzername, absresultfile)

        return analyzer.combinesessionresults(trialfiles, absresultfile)
