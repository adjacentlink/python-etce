#
# Copyright (c) 2014-2017 - Adjacent Link LLC, Bridgewater, New Jersey
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

import copy
import os
import os.path

import etce.loader
import etce.timeutils
from etce.testdirectory import TestDirectory
from etce.stepsdoc import StepsDoc
from etce.config import ConfigDictionary
from etce.platform import Platform
from etce.wrappercontext import WrapperContext
from etce.wrapperloader import WrapperLoader


class Executer(object):
    def __init__(self):
        self._test = TestDirectory(os.getcwd(), None, merged=True)
        self._stepsdoc = StepsDoc(self._test.stepsfile())
        self._config = ConfigDictionary()


    def step(self, stepname, starttime, logsubdirectory):
        wrappers = self._stepsdoc.getwrappers(stepname)
        
        hostname = Platform().hostname()

        hostdir = os.path.join(self._test.location(), hostname)

        if not os.path.exists(hostdir):
            return

        logdirectory = os.path.join(
            self._config.get('etce','WORK_DIRECTORY'),
            logsubdirectory,
            hostname)

        if not os.path.exists(logdirectory):
            os.makedirs(logdirectory)

        if wrappers:
            # pass stepname as parameter
            trialargs = {}
            trialargs['logdirectory'] = logdirectory
            trialargs['starttime'] = starttime
            trialargs['stepname'] = stepname

            wldr = WrapperLoader()
            
            for wrappername,methodname,testargs in wrappers:
                wrapperinstance = \
                    wldr.loadwrapper(wrappername,
                                     self._stepsdoc.getpackageprefixes())
                
                # ensure each wrapper is called with the testdirectory as
                # the current working directory, and with it's own
                # instance of the wrapper context
                os.chdir(hostdir)

                ctx = WrapperContext(wrappername,
                                     wrapperinstance,
                                     trialargs,
                                     testargs,
                                     self._config,
                                     self._test)

                if methodname == 'run':
                    # run calls prerun, run, postrun to encourage
                    #   pre/post condition checks
                    wrapperinstance.prerun(ctx)
                    wrapperinstance.run(ctx)
                    wrapperinstance.postrun(ctx)
                else:
                    wrapperinstance.stop(ctx)


