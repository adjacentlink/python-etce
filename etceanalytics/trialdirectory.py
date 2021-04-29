#
# Copyright (c) 2015 - Adjacent Link LLC, Bridgewater, New Jersey
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
import os
import re


class TrialDirectory(object):
    @staticmethod
    def istrialdir(sessiondir, subdir):
        if not os.path.isdir(os.path.join(sessiondir, subdir, 'data')):
            return False

        if not re.match(r'\S+-\S+-\d{8}T\d{6}', subdir):
            return False

        return True


    def __init__(self, sessiondir, subdir):
        self._trialdir = os.path.join(sessiondir, subdir)

        self._testname, self._datetime = \
            (re.match(r'\S+-(\S+)-(\d{8}T\d{6})', subdir)).groups()

        self._datadir = os.path.join(sessiondir, subdir, 'data')

        self._resultsdir = os.path.join(sessiondir, subdir, 'results')

        self._templatedir = os.path.join(sessiondir, subdir, 'template')


    @property
    def trialdir(self):
        return self._trialdir


    @property
    def testname(self):
        return self._testname


    @property
    def datetime(self):
        return self._datetime


    @property
    def datadir(self):
        return self._datadir


    @property
    def resultsdir(self):
        return self._resultsdir


    @property
    def templatedir(self):
        return self._templatedir
