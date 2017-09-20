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
from StringIO import StringIO
from collections import defaultdict

import etce.utils
import etce.xmldoc

from lxml import etree


class ExecuterDoc(etce.xmldoc.XMLDoc):
    def __init__(self, executerfile):
        etce.xmldoc.XMLDoc.__init__(self, 
                                    StringIO('''
<xs:schema xmlns:xs='http://www.w3.org/2001/XMLSchema'>

  <xs:element name="param">
    <xs:complexType>
      <xs:attribute name="name" type="xs:string"/>
      <xs:attribute name="value" type="xs:string"/>
    </xs:complexType>
  </xs:element>

  <xs:element name="executer">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="using" 
                    minOccurs="0" 
                    maxOccurs="unbounded">
          <xs:complexType>
            <xs:attribute name="package" type="xs:string"/>
          </xs:complexType>
        </xs:element>

        <xs:element name="step" 
                    minOccurs="0" 
                    maxOccurs="unbounded">
          <xs:complexType>
            <xs:choice minOccurs="0" maxOccurs="unbounded">
              <xs:element name="run">
                <xs:complexType>
                  <xs:sequence>
                    <xs:element ref="param" 
                                minOccurs="0" 
                                maxOccurs="unbounded"/>
                  </xs:sequence>
                  <xs:attribute name="wrapper" type="xs:string"/>
                </xs:complexType>
              </xs:element>
              <xs:element name="stop">
                <xs:complexType>
                  <xs:sequence>
                    <xs:element ref="param" 
                                minOccurs="0" 
                                maxOccurs="unbounded"/>
                  </xs:sequence>
                  <xs:attribute name="wrapper" type="xs:string"/>
                </xs:complexType>
              </xs:element>

            </xs:choice>
            <xs:attribute name="name" type="xs:string"/>
          </xs:complexType>
        </xs:element>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>'''))

        if executerfile is None:
            raise ValueError('No executerfile found')
        self._packageprefixes, \
        self._steplist, \
        self._filterdict, \
        self._wrapperlist = self._parseexecuter(executerfile)


    def getsteps(self, runfromstep=None, runtostep=None, filtersteps=[]):
        steplist = copy.copy(self._steplist)

        if runfromstep:
            if not runfromstep in steplist:
                errorstr = 'Specified runfromstep "%s" not a ' \
                           'stepname in executer file. steps are %s' \
                           % (runfromstep,
                              '\n'.join(steplist))
            
                raise ValueError(errorstr)

            steplist = steplist[steplist.index(runfromstep):]


        if runtostep:
            if not runtostep in steplist:
                errorstr = 'Specified runtostep "%s" not a ' \
                           'stepname in executer file. steps are %s' \
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


    def _parseexecuter(self, executerfile): 
        executerelem = self.parse(executerfile)

        packageprefixes = [ None ]
        for usingelem in executerelem.findall('./using'):
            packageprefixes.append(usingelem.attrib['package'])

        steplist = []

        filterdict = defaultdict(lambda: [])

        wrapperlist = []

        for stepelem in executerelem.findall('./step'):
            stepname = stepelem.attrib['name']

            filtername = stepelem.attrib.get('filter', None)

            stepwrappers = []

            for child in stepelem:
                paramdict = {}

                for pelem in child.findall('./param'):
                    val = etce.utils.configstrtoval(pelem.attrib['value'])

                    paramdict[pelem.attrib['name']] = val

                if child.tag is etree.Comment:
                    continue

                stepwrappers.append((child.attrib['wrapper'],
                                     child.tag,
                                     paramdict))

            if stepname in steplist:
                errstr = \
                    'Stepname "%s" appears more thane once in executer file "%s". Quitting.' % \
                    (stepname, executerfile)
                raise RuntimeError(errstr)
            
            steplist.append(stepname)

            if filtername:
                filterdict[filtername].append(stepnam)

            wrapperlist.append(tuple(stepwrappers))

        return packageprefixes,steplist,filterdict,wrapperlist
