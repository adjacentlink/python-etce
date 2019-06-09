#
# Copyright (c) 2015-2019 - Adjacent Link LLC, Bridgewater, New Jersey
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

import imp
import os
import sys

from etce.config import ConfigDictionary


class WrapperLoader(object):
    def __init__(self):
        self._config = ConfigDictionary()


    def loadwrappers(self):
        wrapperinstances = {}
        for syspath in sys.path:
            if not os.path.exists(syspath) or not os.path.isdir(syspath):
                continue

            if not 'etcewrappers' in os.listdir(syspath):
                continue

            wrapperspath = os.path.join(syspath, 'etcewrappers')
            if not os.path.isdir(wrapperspath):
                continue

            for cwd,dirnames,filenames in os.walk(wrapperspath):
                
                for wrapperfile in filenames:
                    try:
                        wrapperfile = os.path.join(cwd, wrapperfile.split('.')[0])
                        fullwrappername = \
                            os.path.relpath(wrapperfile, syspath)
                        relwrappername = fullwrappername[fullwrappername.index(os.sep)+1:]
                        wrapper = self._load_module(relwrappername, None)
                        if wrapper is not None:
                            basename = wrapper.__name__.split('/')[-1]
                            candidateclassname = basename.upper()
                            classinstance = None
                            for key in wrapper.__dict__:
                                if key.upper() == candidateclassname:
                                    candidateclass = wrapper.__dict__[key]
                                    if callable(candidateclass):
                                        wkey = relwrappername.replace(os.sep,'.')
                                        if not wkey in wrapperinstances:
                                            wrapperinstances[wkey] = (wrapperspath,candidateclass())
                    except:
                        continue
        return wrapperinstances

                     
    def loadwrapper(self,
                    wrappername,
                    packageprefixfilter=(None,)):
        wrapper = None

        for packagename in packageprefixfilter:
            wrapper = self._load_module(wrappername,packagename)

            if wrapper is not None:
                basename = wrapper.__name__.split('/')[-1]

                candidateclassname = basename.upper()
                
                classinstance = None
                
                for key in wrapper.__dict__:
                    if key.upper() == candidateclassname:
                        
                        candidateclass = wrapper.__dict__[key]
                        
                        if callable(candidateclass):
                            return candidateclass()

        message = 'No wrapper "%s" found' % wrappername
        raise RuntimeError(message)


    def _load_module(self, wrappername, packageprefix):
        wrapper = None

        if packageprefix:
            wrappername = packageprefix + '.' + wrappername

        # all wrappers start with etcewrappers
        wrappername = 'etcewrappers' + '.' + wrappername

        etcewrapper = wrappername.replace('.', os.sep)

        try:
            f,pathname,description = \
                imp.find_module(etcewrapper)

            wrapper = imp.load_module(etcewrapper,f,pathname,description)
        except:
            pass
        return wrapper
