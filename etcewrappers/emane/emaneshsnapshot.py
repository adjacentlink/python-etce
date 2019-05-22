#
# Copyright (c) 2015-2018 - Adjacent Link LLC, Bridgewater, New Jersey
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

import os.path

from etce.wrapper import Wrapper

try:
    from emanesh.emaneshell import ControlPortClient
except:
    from emane.shell import ControlPortClient


class EmaneshSnapshot(Wrapper):
    """
    Log the stats, tables and config of a running emulator
    instance to file.
    """

    def register(self, registrar):
        registrar.register_infile_name('emaneshsnapshot.flag')

        registrar.register_argument('controlportendpoint',
                                   '127.0.0.1:47000',
                                   'The control port endpoint of the target ' \
                                   'EMANE instance.')


    def run(self, ctx):
        # query emane instance if there is a local platform file
        if not ctx.args.infile:
            return

        cp = None

        try:
            layermapping = {}

            ipaddr,port = ctx.args.controlportendpoint.split(':')

            cp = ControlPortClient(ipaddr, int(port))

            logdirectory = ctx.args.logdirectory

            # nem 3 shim0(phyapitestshim) phy(universalphy)
            showfile = os.path.join(logdirectory, 'emaneshow.log')

            with open(showfile, 'w') as showf:
                for nemid, layertuples in cp.getManifest().items():
                    layermapping[nemid] = []
                    line = 'nem %d ' % nemid
                    for buildid,layertype,layername in layertuples:
                        layerlabel = '%d-%s' % (buildid, layertype.lower())
                        layermapping[nemid].append((buildid, layertype.lower(), layerlabel))
                        line += ' %s(%s)' % (layertype.lower(), layername)
                    showf.write(line + '\n')


            # statistics
            statsfile = os.path.join(logdirectory, 'emanestats.log')

            with open(statsfile, 'w') as sf:
                # nems
                for nemid,layertuples in sorted(layermapping.items()):
                    for buildid,_,layerlabel in layertuples:
                        for statname,statval in sorted(cp.getStatistic(buildid).items()):
                            sf.write('nem %d %s %s = %s\n' % (nemid, layerlabel, statname, str(statval[0])))
                # emulator
                for statname,statval in sorted(cp.getStatistic(0).items()):
                    sf.write('emulator %s = %s\n' % (statname, str(statval[0])))

            # configuration
            configfile = os.path.join(logdirectory, 'emaneconfig.log')

            with open(configfile, 'w') as sf:
                # nems
                for nemid,layertuples in sorted(layermapping.items()):
                    for buildid,_,layerlabel in layertuples:
                        for configname,configvaltuples in sorted(cp.getConfiguration(buildid).items()):
                            configvalstr = ''
                            if configvaltuples:
                                configvalstr = ','.join(map(str, zip(*configvaltuples)[0]))
                            sf.write('nem %d %s %s = %s\n' % (nemid, layerlabel, configname, configvalstr))

                # emulator
                for configname,configvaltuples in sorted(cp.getConfiguration(0).items()):
                    configvalstr = ''
                    if configvaltuples:
                        configvalstr = ','.join(map(str, zip(*configvaltuples)[0]))
                    sf.write('emulator %s = %s\n' % (configname, configvalstr))


            # statistic tables
            tablefile = os.path.join(logdirectory, 'emanetables.log')

            with open(tablefile, 'w') as tf:
                # nems
                for nemid,layertuples in sorted(layermapping.items()):
                    for buildid,layertype,_ in layertuples:
                        for tablename,data in sorted(cp.getStatisticTable(buildid).items()):
                            tf.write('nem %d   %s %s\n' % (nemid, layertype, tablename))
                            self.write_table_cells(tf, data)
                        
                # emulator
                for tablename,data in sorted(cp.getStatisticTable(0).items()):
                    tf.write('emulator %s\n' % tablename)
                    self.write_table_cells(tf, data)

        finally:
            if cp:
                cp.stop()


    def write_table_cells(self, tf, data):
        labels,rowtuples = data

        widths = [];

        for label in labels:
            widths.append(len(label))

        rows = []
        for rowtuple in rowtuples:
            rows.append(map(str, zip(*rowtuple)[0]))
            
        for row in rows:
            for i,value in enumerate(row):
                widths[i] = max(widths[i],len(value))

        line = ''
        for i,label in enumerate(labels):
            line += '|' + label.ljust(widths[i])
        line += "|\n"
        tf.write(line)
        
        for row in rows:
            line = ''
            for i,value in enumerate(row):
                line += '|' + value.rjust(widths[i])
            line += "|\n"
            tf.write(line)
        tf.write('\n')


    def stop(self, ctx):
        pass
