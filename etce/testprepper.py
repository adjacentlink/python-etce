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

import os

from etce.testdirectory import TestDirectory
from etce.platform import Platform
from etce.config import ConfigDictionary
from etce.publisher import Publisher
from etce.wrapperstore import WrapperStore


class TestPrepper(object):
    def run(self, starttime, templatesubdir, trialsubdir):
        etcedir = ConfigDictionary().get('etce', 'WORK_DIRECTORY')

        templatedir = os.path.join(etcedir, templatesubdir)

        testdefdir = os.path.join(etcedir, 'current_test')

        trialdir = os.path.join(etcedir, trialsubdir)

        # instantiate the template files and write overlays
        runtimeoverlays = { 'etce_install_path':testdefdir }

        publisher = Publisher(templatedir,
                              mergedir=None,
                              trialdir=trialdir,
                              runtimeoverlays=runtimeoverlays)

        publisher.publish(testdefdir, overwrite=True)

        self._checkdir(trialdir)

        self._savemeta(trialdir)


    def _checkdir(self, logdirectory):
        if not os.path.exists(logdirectory):
            os.makedirs(logdirectory)
    

    def _savemeta(self, logdirectory):
        hostname = Platform().hostname()

        nodedirectory = os.path.join(logdirectory, hostname)

        if not os.path.exists(nodedirectory):
            os.makedirs(nodedirectory)

        backingfilename = os.path.join(nodedirectory, 'etce.store')

        store = WrapperStore(backingfilename)

        store.update(ConfigDictionary().asdict()['overlays'], section='overlays')
