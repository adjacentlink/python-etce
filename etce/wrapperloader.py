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
import os
import pkgutil
import sys

from etce.config import ConfigDictionary


class WrapperLoader(object):
    """
    Provides methods for dynamically importing and
    instantiating ETCE Wrapper instances.
    """

    def __init__(self):
        self._config = ConfigDictionary()


    def loadwrappers(self):
        wrapperinstances = {}

        wrappermod = importlib.import_module('etcewrappers')

        self.returnmembers('etcewrappers', wrappermod, wrapperinstances)

        return wrapperinstances


    def returnmembers(self, modpath, module, wrapperdict):
        for instance, name, ispkg in pkgutil.walk_packages(module.__path__):
            if ispkg:
                try:
                    thismodpath = '.'.join([modpath, name])
                    thismod = importlib.import_module(thismodpath)
                    self.returnmembers(thismodpath, importlib.import_module(thismodpath), wrapperdict)
                except Exception as e:
                    pass
            else:
                thismodpath = '.'.join([modpath, name])
                try:
                    thisclass = importlib.import_module(thismodpath)
                    for entry in thisclass.__dict__:
                        if name.upper() == entry.upper():
                            candidateclass = thisclass.__dict__[entry]
                            if callable(candidateclass):
                                o = candidateclass()
                                if not thismodpath in wrapperdict:
                                    relative_wrapperpath = '.'.join(thismodpath.split('.')[1:])
                                    wrapperdict[relative_wrapperpath] = (thisclass.__file__, o)

                except Exception as e:
                    pass


    def loadwrapper(self,
                    wrappername,
                    packageprefixfilter=(None,)):
        wrapper = None

        for packagename in packageprefixfilter:
            wrapper = self._load_module(wrappername, packagename)

            if wrapper is not None:
                basename = wrapper.__name__.split('.')[-1]

                candidateclassname = basename.upper()

                classinstance = None

                for key in wrapper.__dict__:
                    if key.upper() == candidateclassname:

                        candidateclass = wrapper.__dict__[key]

                        if callable(candidateclass):
                            return ('%s.%s' % (packagename, wrappername), candidateclass())

        message = 'No wrapper "%s" found' % wrappername
        raise RuntimeError(message)


    def _load_module(self, wrappername, packageprefix):
        wrapper = None

        if packageprefix:
            wrappername = packageprefix + '.' + wrappername

        # all wrappers start with etcewrappers
        wrappername = 'etcewrappers' + '.' + wrappername

        try:
            wrapper = importlib.import_module(wrappername)
        except:
            pass
        return wrapper
