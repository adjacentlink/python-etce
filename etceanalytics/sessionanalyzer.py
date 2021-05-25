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
from collections import defaultdict
import logging
import os
import shutil
import traceback
from etceanalytics.analyzermanager import AnalyzerManager
from etceanalytics.diranalyzer import DirAnalyzer
from etceanalytics.sessiondirectory import SessionDirectory


class SessionAnalyzer(object):
    '''
    Analyze an ETCE session directory and place the results in
    SESSION_DIRECTORY/results.
    '''
    def __init__(self, analyzerconfig, args):
        self._cache = {}

        self._analyzerconfig = analyzerconfig

        self._args = args


    def analyze(self, sessiondir, noreanalyze=True, keepfiles=False):
        if not os.path.isdir(sessiondir):
            logging.error('"%s" does not exist. Skipping.', sessiondir)

            return

        directory_analyzer = DirAnalyzer(self._analyzerconfig)

        sd = SessionDirectory(sessiondir)

        if not os.path.exists(sd.resultsdir):
            os.makedirs(sd.resultsdir)

        testfiles = defaultdict(lambda: [])

        for testname, trialdirs in sd.testdirsmap.items():

            for trialdir in trialdirs:
                if not os.path.exists(trialdir.resultsdir):
                    os.makedirs(trialdir.resultsdir)

                try:
                    dirfiles = directory_analyzer.analyze(trialdir.datadir,
                                                          trialdir.resultsdir,
                                                          noreanalyze)

                    for analyzer, combinedfile in sorted(dirfiles.items()):
                        testfiles[(testname, analyzer)].append(combinedfile)

                except:
                    logging.error('Error while processing trial directory "%s"'
                                  % trialdir.datadir)

                    logging.error(traceback.format_exc())

                    if not self._args.keepgoing:
                        logging.error('Quitting.')

                        exit(1)

        mgr = AnalyzerManager(self._analyzerconfig)

        for testname, analyzer in sorted(testfiles):
            try:
                mgr.combinesessionresults(testfiles[(testname, analyzer)],
                                          sd.resultsdir,
                                          testname,
                                          analyzer)
            except:
                logging.error('Error while combining results for "%s"'
                              % testname)

                logging.error(traceback.format_exc())

                if not self._args.keepgoing:
                    logging.error('Quitting.')

                    exit(1)

        # remove intermediate results
        if not keepfiles:
            for _, trialdirs in sd.testdirsmap.items():
                for trialdir in trialdirs:
                    shutil.rmtree(trialdir.resultsdir)
