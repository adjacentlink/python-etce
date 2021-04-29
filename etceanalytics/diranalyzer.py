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
import time
import etce.timeutils
from etce.wrapperstore import WrapperStore
from etceanalytics.configdoc import ConfigDoc
from etceanalytics.analyzermanager import AnalyzerManager
from etceanalytics.pathinfo import PathInfo



class DirAnalyzer(object):
    '''
    Analyze a data directory and place the results in resultdir.

    DirAnalyzer searches in the etceanalyzers namespace for a python
    file (analyzer) that matches the prefix of the data file found in
    the data directory (example "mgen" or "emaneconfig") and loads
    it to analyze the data file.

    All output file is saved to the resultdir with the same name as
    the input file but with the file extension specified by the
    analyzer appended.
    '''
    def __init__(self, analyzerconfig):
        self._cache = {}
        self._analyzerconfig = analyzerconfig


    def analyze(self, datadir, resultdir, noreanalyze):
        if not os.path.isdir(datadir):
            logging.debug('"%s" does not exist. Skipping', datadir)
            return {}

        etce_stores = []
        for dirname, _, filenames in os.walk(datadir):
            if 'etce.store' in filenames:
                etce_stores.append(os.path.join(dirname, 'etce.store'))

        ws = WrapperStore(os.path.join(sorted(etce_stores)[0]))

        store_values = list(ws.read().values())

        starttimestr = store_values[0]['etce']['starttime']

        dt = etce.timeutils.strtimetodatetime(starttimestr)

        starttime = time.mktime(dt.timetuple())

        mgr = AnalyzerManager(self._analyzerconfig)

        # process individual data files
        trialfilesmap = defaultdict(lambda: [])

        for hostname in sorted(os.listdir(datadir)):
            hostdir = os.path.join(datadir, hostname)

            if not os.path.isdir(hostdir):
                continue

            for datafile in sorted(os.listdir(hostdir)):
                # return a map where the key is the name of any analyzer that
                # operates on datafile, and values are the node output files generated
                # by that analyzer
                resultfilesmap = mgr.analyzefile(PathInfo(datadir, hostname, datafile),
                                                 resultdir,
                                                 noreanalyze)

                for analyzer, resultfiles in resultfilesmap.items():
                    trialfilesmap[analyzer].extend(resultfiles)

        # then combine the results
        combinedfiles = defaultdict(lambda: None)

        for analyzer, trialfiles in trialfilesmap.items():

            if len(trialfiles) == 0:
                continue

            combinedfiles[analyzer] = mgr.combinetrialresults(trialfiles,
                                                              resultdir,
                                                              analyzer,
                                                              starttime)

        return combinedfiles


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description=DirAnalyzer.__doc__)

    parser.add_argument('--configfile',
                        default=None,
                        help='analysis configuration file')

    parser.add_argument('--noreanalyze',
                        action='store_true',
                        default=False,
                        help="Don't regenerate an intermediate or final " \
                        "analysis output file when it already exists.")

    parser.add_argument('datadir',
                        help='the datadir to analyze')

    parser.add_argument('resultdir',
                        help='the directory to place analysis results')

    args = parser.parse_args()

    if not os.path.exists(args.resultdir):
        logging.info('Creating result directory "%s"', args.resultdir)

        os.makedirs(args.resultdir)

    config = ConfigDoc(args.configfile)

    DirAnalyzer(config).analyze(args.datadir, args.resultdir, args.noreanalyze)
