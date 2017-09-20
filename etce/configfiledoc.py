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
from StringIO import StringIO

import etce.xmldoc


class ConfigFileDoc(etce.xmldoc.XMLDoc):
    def __init__(self, configfile):
        etce.xmldoc.XMLDoc.__init__(self, 
                                    StringIO('''
<xs:schema xmlns:xs='http://www.w3.org/2001/XMLSchema'>

  <xs:element name="param">
    <xs:complexType>
      <xs:attribute name="name" type="xs:string"/>
      <xs:attribute name="value" type="xs:string"/>
    </xs:complexType>
  </xs:element>

  <xs:element name="testconfiguration">
    <xs:complexType>
      <xs:sequence>
        <xs:element ref="param" minOccurs="0" maxOccurs="unbounded"/>
        <xs:element name="wrapper" minOccurs="0" maxOccurs="unbounded">
          <xs:complexType>
            <xs:sequence>
              <xs:element ref="param" minOccurs="0" maxOccurs="unbounded"/>
            </xs:sequence>
            <xs:attribute name="name" type="xs:string"/>
          </xs:complexType>
        </xs:element>
      </xs:sequence>
    </xs:complexType>
  </xs:element>

</xs:schema>'''))


        self._config = self._parseconfigfile(configfile)


    def _parseconfigfile(self, configfile):
        config = {}

        if not os.path.exists(configfile):
            return config

        configelem = self.parse(configfile)
        for paramelem in configelem.findall('./param'):
            config[('default',paramelem.attrib['name'])] = \
                etce.utils.configstrtoval(paramelem.attrib['value'])

        for wrapperelem in configelem.findall('./wrapper'):
            wrappername = wrapperelem.attrib['name'] 
            for paramelem in wrapperelem.findall('./param'):
                config[(wrappername, paramelem.attrib['name'])] = \
                    etce.utils.configstrtoval(paramelem.attrib['value'])

        return config


    def hasconfig(self, wrappername, paramname):
        if (wrappername, paramname) in self._config:
            return True
        if ('default',paramname) in self._config:
            return True
        return False


    def getconfig(self, wrappername, paramname, default):
        if (wrappername, paramname) in self._config:
            return self._config[(wrappername,paramname)]
        if ('default',paramname) in self._config:
            return self._config[('default',paramname)]
        return default
