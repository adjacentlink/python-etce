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

import copy
import etce.xmldoc
import lxml.etree as etree

class Network(object):
    def __init__(self, netelem):
        self._netelem = netelem
        self._parse(netelem)

    def name(self):
        return self._name

    def params(self):
        return self._params

    def _parse(self, netelem):
        self._name = netelem.attrib['name']

        self._params = {}
        paramelems = netelem.findall('./param')
        for paramelem in paramelems:
            self._params[paramelem.attrib['name']] = paramelem.attrib['val']

    def __str__(self):
        s =  'Network:\n'
        s += '\tname: %s\n' % (self.name())
        s += '\tparams:\n'
        for n,v in sorted(self.params().items()):
            s += '\t\t%s: %s\n' % (n,v)
        return s


class NodeTemplate(object):
    def __init__(self, nodetemplateelem):
        self._nodetemplateelem = nodetemplateelem

    def toelem(self, index):
        nodeelem = copy.deepcopy(self._nodetemplateelem)
        try:
            fmtcount = nodeelem.get('name').count('%')
            if fmtcount > 0:
                fields = (index,)*fmtcount
                nodeelem.set('name', nodeelem.get('name') % index)
        except:
            pass

        for paramelem in nodeelem.findall('./param'):
            try:
                fmtcount = paramelem.get('name').count('%')
                if fmtcount > 0:
                    fields = (index,)*fmtcount
                    paramelem.set('name', paramelem.get('name') % fields )
            except:
                print 'Warning, mismatched number of format fields in param name %s' % \
                    paramelem.get('name')
            try:
                fmtcount = paramelem.attrib['val'].count('%')
                if fmtcount > 0:
                    fields = (index,)*fmtcount
                    paramelem.attrib['val'] = paramelem.attrib['val'] % fields
            except:
                print 'Warning, mismatched number of format fields in param value %s' % \
                    paramelem.attrib['val']

        for interfaceelem in nodeelem.findall('./interface'):
            for paramelem in interfaceelem.findall('./param'):
                try:
                    paramelem.set('name', paramelem.get('name') % index)
                except:
                    pass
                try:
                    fmtcount = paramelem.attrib['val'].count('%')
                    if fmtcount > 0:
                        fields = (index,)*fmtcount
                        paramelem.attrib['val'] = paramelem.attrib['val'] % fields
                except:
                    pass

        return nodeelem


class Interface(object):
    def __init__(self, interfaceelem):
        self._parse(interfaceelem)

    def name(self):
        return self._name

    def net(self):
        return self._net

    def params(self):
        return self._params

    def _parse(self, interfaceelem):
        self._name = interfaceelem.attrib['name']
        self._net = interfaceelem.attrib['net']
        self._params = {}
        for paramelem in interfaceelem.findall('./param'):
            self._params[paramelem.attrib['name']] = paramelem.attrib['val']

    def __str__(self):
        s = 'Interface:\n'
        s += '\tname: %s\n' % self.name()
        s += '\tnet: %s\n' % self.net()
        s += '\tparams:\n'
        for n,v in sorted(self.params().items()):
            s += '\t\t%s: %s\n' % (n,v)
        return s


class Node(object):
    def __init__(self, nodeelem):
        self._nodeelem = nodeelem
        self._parse(nodeelem)

    def name(self):
        return self._name

    def params(self):
        return self._params

    def interfaces(self):
        return self._interfaces

    def _parse(self, nodeelem):
        self._name = nodeelem.attrib['name']
        self._params = {}
        for paramelem in nodeelem.findall('./param'):
            self._params[paramelem.attrib['name']] = paramelem.attrib['val']
        self._interfaces = [ Interface(ielem) for ielem in nodeelem.findall('./interface') ]


    def __str__(self):
        s =  'Network:\n'
        s += '\tname: %s\n' % (self.name())
        s += '\tparams:\n'
        for n,v in sorted(self.params().items()):
            s += '\t\t%s: %s\n' % (n,v)
        for i in self._interfaces:
            s += str(i)
        return s

    

class NetPlanDoc(etce.xmldoc.XMLDoc):
    def __init__(self, netplanfile):
        etce.xmldoc.XMLDoc.__init__(self, 
                                    StringIO('''
<xs:schema xmlns:xs='http://www.w3.org/2001/XMLSchema'>

  <xs:element name="param">
    <xs:complexType>
      <xs:attribute name="name" type="xs:string" use="required"/>
      <xs:attribute name="val" type="xs:string" use="required"/>
      <xs:attribute name="units" type="xs:string" use="optional"/>
    </xs:complexType>
  </xs:element>
  
  <xs:element name="node">
    <xs:complexType>
      <xs:sequence>
        <xs:element ref="param" minOccurs="0" maxOccurs="unbounded"/>
        <xs:element name="interface" minOccurs="0" maxOccurs="unbounded">
          <xs:complexType>
            <xs:sequence>
              <xs:element ref="param" minOccurs="0" maxOccurs="unbounded"/>
            </xs:sequence>
            <xs:attribute name="name" type="xs:string" use="required"/>
            <xs:attribute name="net" type="xs:string" use="required"/>
          </xs:complexType>
        </xs:element>
      </xs:sequence>
      <xs:attribute name="name" type="xs:string" use="required"/>
      <xs:attribute name="extension" type="xs:string" use="optional"/>
    </xs:complexType>
  </xs:element>

  <xs:element name="repeat">
    <xs:complexType>
      <xs:choice minOccurs="1" maxOccurs="unbounded">
        <xs:element ref="node"/>
        <xs:element name="edge">
          <xs:complexType>
            <xs:attribute name="source" type="xs:string" use="required"/>
            <xs:attribute name="target" type="xs:string" use="required"/>
          </xs:complexType>
        </xs:element>
      </xs:choice>
      <xs:attribute name="name" type="xs:string" use="required"/>
      <xs:attribute name="range" type="xs:string" use="required"/>
    </xs:complexType>
  </xs:element>

  <xs:element name="networkplan">
    <xs:complexType>
      <xs:sequence>

        <xs:element name="addressPool" minOccurs="0" maxOccurs="unbounded">
          <xs:complexType>
            <xs:simpleContent>
              <xs:extension base="xs:string">
                <xs:attribute name="name" type="xs:string" use="required"/>
              </xs:extension>
            </xs:simpleContent>
          </xs:complexType>
        </xs:element>

        <xs:element name="network" minOccurs="1" maxOccurs="unbounded">
          <xs:complexType>
            <xs:sequence>
              <xs:element ref="param" minOccurs="0" maxOccurs="unbounded"/>
              <xs:element name="graph" minOccurs="0" maxOccurs="1">
                <xs:complexType>
                  <xs:sequence>
                    <xs:element ref="repeat" minOccurs="0" maxOccurs="unbounded"/>
                  </xs:sequence>
                </xs:complexType>
              </xs:element>
            </xs:sequence>
            <xs:attribute name="name" type="xs:string" use="required"/>
          </xs:complexType>
        </xs:element>

        <xs:choice minOccurs="1" maxOccurs="unbounded">
          <xs:element ref="node"/>
          <xs:element ref="repeat"/>
        </xs:choice>
      </xs:sequence>
    </xs:complexType>
  </xs:element>

</xs:schema>'''))

        self._netplanfile = netplanfile
        self._parsefile(netplanfile)

    def netplanfile(self):
        return self._netplanfile

    def networks(self):
        return self._networks

    def nodes(self):
        return self._nodes

    def _parsefile(self, netplanfile):
        # open netplanfile, extract its contents
        self._rootelem = self.parse(netplanfile)

        # parse networks
        netelems = self._rootelem.findall('./network')
        self._networks = [ Network(netelem) for netelem in netelems ]

        # parse nodes, possibly embedded in repeat blocks
        repeatelems = self._rootelem.findall('./repeat')
        self._nodes = []
        if repeatelems:
            for repeatelem in repeatelems:
                minindex,maxindex = [ int(num) for num in repeatelem.attrib['range'].split('-') ]
                indices = range(minindex, maxindex+1)
                nodeelems = repeatelem.findall('./node')
                nodetemplates = [ NodeTemplate(nodeelem) for nodeelem in nodeelems ]
                self._nodes = [ Node(nt.toelem(i)) for nt in nodetemplates for i in indices ]
        else:
            nodeelems = self._rootelem.findall('./node')
            self._nodes = [ Node(nodeelem) for nodeelem in nodeelems ]

    def __str__(self):
        s = 'NetPlan:\n'
        for network in self.networks():
            s += str(network)
        for node in self.nodes():
            s += str(node)
        return s


if __name__=='__main__':
    import sys
    npd = NetPlanDoc(sys.argv[1])
    print npd
