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

import importlib
import pkgutil
import logging
from collections import defaultdict
from .analyzercontext import AnalyzerContext


class AnalyzerLoader(object):
    def __init__(self, analyzerconfig):
        self._metaitems = analyzerconfig.metaitems

        self._analyzerconfigs = analyzerconfig.analyzerconfigs

        # cache_by_datafile keys are datafile names, values are list of keys to cache_by_analyzer
        # cache_by_analyzer keys are the analyzer class name, values are the analyzer instance
        self._cache_by_datafile, self._cache_by_analyzer = self._loadanalyzers()


    def load_by_datafile(self, datafile):
        return sorted({name:self._cache_by_analyzer[name]
                       for name in self._cache_by_datafile[datafile]}.items())


    def load_by_analyzer(self, analyzername):
        return self._cache_by_analyzer[analyzername]


    def _loadanalyzers(self):
        analyzermod = importlib.import_module('etceanalyzers')

        analyzerinstances = {}

        self._returnmembers('etceanalyzers', analyzermod, analyzerinstances)

        cache_by_analyzer = defaultdict(lambda: None)

        cache_by_datafile = defaultdict(lambda: [])

        for name, (_, instance) in analyzerinstances.items():
            cache_by_analyzer[name] = instance

            cache_by_datafile[instance.input_file].append(name)

        return (cache_by_datafile, cache_by_analyzer)


    def _returnmembers(self, modpath, module, analyzerdict):
        for _, name, ispkg in pkgutil.walk_packages(module.__path__):
            if ispkg:
                thismodpath = '.'.join([modpath, name])

                self._returnmembers(thismodpath,
                                    importlib.import_module(thismodpath),
                                    analyzerdict)
            else:
                thismodpath = '.'.join([modpath, name])

                try:
                    thisclass = importlib.import_module(thismodpath)

                    normalized_classname = name.replace('_', '').upper()

                    for entry in thisclass.__dict__:
                        if entry.upper() == normalized_classname:

                            analyzerconfig = \
                                self._analyzerconfigs[name]

                            ctx = AnalyzerContext(self, analyzerconfig)

                            candidateclass = thisclass.__dict__[entry]

                            if callable(candidateclass):
                                o = candidateclass(ctx)

                                if not thismodpath in analyzerdict:
                                    relative_analyzerpath = '.'.join(thismodpath.split('.')[1:])

                                    analyzerdict[relative_analyzerpath] = (thisclass.__file__, o)

                except Exception as e:
                    logging.debug(e)


    def _load_module(self, analyzername, packageprefix, root):
        analyzer = None

        if packageprefix:
            analyzername = packageprefix + '.' + analyzername

        # all analyzers start with etceanalyzers
        analyzername = root + '.' + analyzername

        try:
            analyzer = importlib.import_module(analyzername)
        except ImportError as e:
            logging.debug(e.msg)

        return analyzer
