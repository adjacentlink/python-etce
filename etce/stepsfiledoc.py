#
# Copyright (c) 2014-2018 - Adjacent Link LLC, Bridgewater, New Jersey
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
from collections import defaultdict,namedtuple

import etce.utils
import etce.xmldoc

from lxml import etree


class StepsFileDoc(etce.xmldoc.XMLDoc):
    WrapperEntry = namedtuple('WrapperEntry', ['name', 'decorator'])

    def __init__(self, stepsfile):
        etce.xmldoc.XMLDoc.__init__(self,
                                    'stepsfile.xsd')

        if stepsfile is None:
            raise ValueError('No stepsfile found')
        self._packageprefixes, \
        self._steplist, \
        self._filterdict, \
        self._wrapperlist = self._parsesteps(stepsfile)


    def getsteps(self, runfromstep=None, runtostep=None, filtersteps=[]):
        steplist = copy.copy(self._steplist)

        if runfromstep:
            if not runfromstep in steplist:
                errorstr = 'Specified runfromstep "%s" not a ' \
                           'stepname in steps file. steps are\n%s' \
                           % (runfromstep,
                              '\n'.join(steplist))
            
                raise ValueError(errorstr)

            steplist = steplist[steplist.index(runfromstep):]


        if runtostep:
            if not runtostep in steplist:
                errorstr = 'Specified runtostep "%s" not a ' \
                           'stepname in steps file. steps are\n%s' \
                           % (runtostep,
                              '\n'.join(steplist))
                
                raise ValueError(errorstr)

            steplist = steplist[:steplist.index(runtostep) + 1]

        filtermatches = []

        for step_prefix in filtersteps:
            for stepname in steplist:
                if stepname.startswith(step_prefix):
                    filtermatches.append(stepname)
        
        return tuple([step for step in steplist if not step in filtermatches])


    def getwrappers(self, stepname):
        if stepname in self._steplist:
            return self._wrapperlist[self._steplist.index(stepname)]

        return None


    def getpackageprefixes(self):
        return tuple(self._packageprefixes)


    def _parsesteps(self, stepsfile):
        stepselem = self.parse(stepsfile)

        packageprefixes = [ None ]
        for usingelem in stepselem.findall('./using'):
            packageprefixes.append(usingelem.attrib['package'])

        steplist = []

        filterdict = defaultdict(lambda: [])

        wrapperlist = []

        for stepelem in stepselem.findall('./step'):
            stepname = stepelem.attrib['name']

            filtername = stepelem.attrib.get('filter', None)

            stepwrappers = []

            for child in stepelem:
                argdict = {}

                for pelem in child.findall('./arg'):
                    val = etce.utils.configstrtoval(pelem.attrib['value'])

                    argdict[pelem.attrib['name']] = val

                if child.tag is etree.Comment:
                    continue

                stepwrappers.append(
                    (StepsFileDoc.WrapperEntry(name = child.attrib['wrapper'],
                                               decorator = None),
                     child.tag,
                     argdict))

            if stepname in steplist:
                errstr = \
                    'Stepname "%s" appears more thane once in steps file "%s". Quitting.' % \
                    (stepname, stepsfile)
                raise RuntimeError(errstr)
            
            steplist.append(stepname)

            if filtername:
                filterdict[filtername].append(stepnam)

            wrapperlist.append(tuple(stepwrappers))

        return packageprefixes,steplist,filterdict,wrapperlist
