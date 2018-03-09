#
# Copyright (c) 2015-2017 - Adjacent Link LLC, Bridgewater, New Jersey
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

from etce.config import ConfigDictionary


class WrapperLoader(object):
    def __init__(self):
        self._config = ConfigDictionary()


    def wrapperpaths(self):
        return self._config.get('etce',
                                'WRAPPER_DIRECTORY').split(':')


    def loadwrappers(self, wrapperpath):
        wrapperinstances = {}
        for cwd,dirnames,filenames in os.walk(wrapperpath):
            for wrapperfile in filenames:
                try:
                    wrapperfile = os.path.join(cwd, wrapperfile.split('.')[0])
                    fullwrappername = \
                        os.path.relpath(wrapperfile, wrapperpath)
                    wrapper = self._load_module(fullwrappername, None)
                    if wrapper is not None:
                        basename = wrapper.__name__.split('/')[-1]
                        candidateclassname = basename.upper()
                        classinstance = None
                        for key in wrapper.__dict__:
                            if key.upper() == candidateclassname:
                                candidateclass = wrapper.__dict__[key]
                                if callable(candidateclass):
                                    key = fullwrappername.replace(os.sep,'.')
                                    wrapperinstances[key] = (wrapperpath,candidateclass())
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
        etcewrapper = wrappername.replace('.', os.sep)
        try:
            f,pathname,description = \
                imp.find_module(etcewrapper, self.wrapperpaths())
            wrapper = imp.load_module(etcewrapper,f,pathname,description)
        except:
            pass
        return wrapper


