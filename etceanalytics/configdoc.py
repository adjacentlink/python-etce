#
# Copyright (c) 2017-2020 - Adjacent Link LLC, Bridgewater, New Jersey
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

from collections import namedtuple, defaultdict

import etce.utils
import etce.xmldoc


class ConfigDoc(etce.xmldoc.XMLDoc):
    def __init__(self, analysisfile):
        etce.xmldoc.XMLDoc.__init__(self,
                                    'config.xsd',
                                    schemamodule='etceanalytics')

        self._analysisfile = analysisfile

        self._parsefile(analysisfile)


    @property
    def metaitems(self):
        return self._metaitems

    @property
    def analyzerconfigs(self):
        return self._analyzerconfigs

    @property
    def nodemap(self):
        return self._nodemap.copy()

    @property
    def reverse_nodemap(self):
        return self._reverse_nodemap.copy()

    def _parsefile(self, analysisfile):
        # open analysisfile, extract its contents
        '''
        <etceanalytics>
          <meta>
            <item value="platform.nemid"/>
          </meta>
          <analyzers>
            <analyzer name="otestpoint">
              <statistic probe="EMANE.PhysicalLayer.Counters.General"
                         statistics="stat1,stat2"/>
              <statistictable probe="EMANE.PhysicalLayer.Tables.Events"
                              table="pathlosseventtable"
                              columns="NEM,Pathloss dB"/>
            </analyzer>
          </analyzers>
          <nodemap>
            <node name="lha-02" number="1"/>
            <node name="lpd-23" number="2"/>
            <node name="mmt-01" number="5"/>
          </nodemap>
        </etceanalytics>
        '''
        AnalyzerConfig = namedtuple('AnalyzerConfig', 'statistics tables args')

        Statistic = namedtuple('Statistic', 'probe entries')

        Table = namedtuple('Table', 'probe table entries')

        self._metaitems = ()

        self._nodemap = defaultdict(lambda: None)

        self._reverse_nodemap = defaultdict(lambda: None)

        self._analyzerconfigs = \
            defaultdict(lambda: AnalyzerConfig(statistics=[], tables=[], args={}))

        if analysisfile is None:
            return

        self._rootelem = self.parse(analysisfile)

        self._metaitems = (e.attrib['value']
                           for e in self._rootelem.findall('./meta/item'))

        for analyzerelem in self._rootelem.findall('./analyzers/analyzer'):
            config = AnalyzerConfig(statistics=[], tables=[], args={})

            name = analyzerelem.attrib['name']

            for statelem in analyzerelem.findall('./statistic'):
                config.statistics.append(
                    Statistic(probe=statelem.attrib['probe'],
                              entries=statelem.attrib['entries'].split(',')))

            for tableelem in analyzerelem.findall('./statistictable'):
                config.tables.append(
                    Table(probe=tableelem.attrib['probe'],
                          table=tableelem.attrib['table'],
                          entries=tableelem.attrib['entries'].split(',')))

            for argelem in analyzerelem.findall('./arg'):
                config.args[argelem.attrib['name']] = \
                    etce.utils.configstrtoval(argelem.attrib['value'])

            self._analyzerconfigs[name] = config

        for nodeelem in self._rootelem.findall('./nodemap/node'):
            name = nodeelem.attrib['name']

            number = int(nodeelem.attrib['number'])

            self._nodemap[name] = number

            self._reverse_nodemap[number] = name
