#
# Copyright (c) 2016-2021 - Adjacent Link LLC, Bridgewater, New Jersey
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
import logging
import re
import sys
import sqlite3
from collections import defaultdict
from functools import reduce

import pandas as pd
from pandas import DataFrame
from etceanalytics import utils
from etceanalytics.analyzer import Analyzer


def to_dataframes(sqlitefile, keepselfrxs=False):
    con = sqlite3.connect(sqlitefile)

    rx = pd.read_sql('select * from rx', con)

    tx = pd.read_sql('select * from tx', con)

    if not keepselfrxs:
        rx = rx[rx.txnode != rx.rxnode]

    rx['latency'] = rx.rxtime - rx.txtime

    return (rx, tx)


class Mgen(Analyzer):
    '''
    Analyse mgen log file
    '''
    def __init__(self, ctx):
        self._config = ctx.config

        flow_allocations_str = self._config.args.get('flowformat', '0:3:2')

        flow_allocations = list(map(int, flow_allocations_str.split(':')))

        if not sum(flow_allocations) == 5:
            logging.debug('Invalid flowformat "%s", integer fields must sum to 5. Quitting',
                          flow_allocations_str)

            sys.exit(1)

        _, txid_power, flownum_power = flow_allocations

        self._flownum_divisor = reduce(lambda x, y: x*y, [10]*flownum_power, 1)

        self._txid_divisor = reduce(lambda x, y: x*y, [10]*txid_power, 1)


    @property
    def input_file(self):
        return 'mgen.log'


    @property
    def file_fields(self):
        return ('mgen', 'sqlite')


    def analyzefile(self, pathinfo, resultfile):
        absdatafile = pathinfo.absdatafile
        hostname = pathinfo.hostname

        # 1614953760.000801 START Mgen Version 5.1.1
        startre = re.compile(r'(\S+) START Mgen Version (\S+)')

        # 1614954180.001577 STOP
        stopre = re.compile(r'(\S+) STOP')

        # 1454037130.420791 LISTEN proto>UDP port>10101
        listenre = re.compile(r'(\S+) LISTEN proto>\S+ port>(\S+)')

        # 1614890300.004376 IGNORE proto>UDP port>10103
        ignorere = re.compile(r'(\S+) IGNORE proto>\S+ port>(\S+)')

        # 1454037191.363841 SEND proto>UDP flow>10101 seq>1 srcPort>5001 dst>224.1.2.1/10101 size>256
        sendre = re.compile(r'(\S+) SEND proto>\S+ flow>(\S+) seq>(\S+) srcPort>\S+ dst>\S+ size>(\S+)')

        # 1454037200.282077 RECV proto>UDP flow>10101 seq>1964 src>192.168.254.1/5001 dst>224.1.2.1/10101 sent>1454037199.215943 size>256 gps>INVALID,999.000000,999.000000,-999
        recvre = re.compile(r'(\S+) RECV proto>\S+ flow>(\S+) seq>(\S+) src>\S+ dst>\S+ sent>(\S+) size>(\S+)')

        # extract send and recv info
        txcols = {
            'txnode':[], 'txtime':[], 'flowid':[], 'sequence':[], 'size':[]
        }

        rxcols = {
            'rxnode':[], 'txtime':[], 'flowid':[], 'sequence':[], 'size':[], 'rxtime':[]
        }

        # rxflowsdict key is the port and value is a dicof of the start and stop times
        rxflowsdict = defaultdict(lambda: {})
        rxflowscols = {
            'rxnode':[], 'start':[], 'stop':[], 'port':[]
        }

        metacols = {'node':[hostname], 'start':[], 'stop':[], 'mgenversion':[]}

        for line in open(absdatafile):
            match = recvre.match(line)
            if match:
                rxtime, flowid, seq, txtime, size = match.groups()
                rxcols['rxnode'].append(hostname)
                rxcols['txtime'].append(self._timestrtofloat(txtime))
                rxcols['flowid'].append(int(flowid))
                rxcols['sequence'].append(int(seq))
                rxcols['size'].append(int(size))
                rxcols['rxtime'].append(self._timestrtofloat(rxtime))
            else:
                match = sendre.match(line)
                if match:
                    txtime, flowid, seq, size = match.groups()
                    txcols['txnode'].append(hostname)
                    txcols['txtime'].append(self._timestrtofloat(txtime))
                    txcols['flowid'].append(int(flowid))
                    txcols['sequence'].append(int(seq))
                    txcols['size'].append(int(size))
                else:
                    match = listenre.match(line)
                    if match:
                        time, port = match.groups()
                        rxflowsdict[int(port)]['start'] = self._timestrtofloat(time)
                    else:
                        match = ignorere.match(line)
                        if match:
                            time, port = match.groups()

                            rxflowsdict[int(port)]['stop'] = self._timestrtofloat(time)
                        else:
                            match = startre.match(line)
                            if match:
                                startstr, mgenversion = match.groups()

                                metacols['start'].append(self._timestrtofloat(startstr))

                                metacols['mgenversion'].append(mgenversion)
                            else:
                                match = stopre.match(line)
                                if match:
                                    stopstr, = match.groups()

                                    metacols['stop'].append(self._timestrtofloat(stopstr))
                                else:
                                    logging.debug('%s unparsed line: %s',
                                                  absdatafile,
                                                  line.strip())

        # flatten rxflowsdict
        for port, times in sorted(rxflowsdict.items()):
            rxflowscols['rxnode'].append(hostname)

            rxflowscols['port'].append(port)

            rxflowscols['start'].append(times['start'])

            rxflowscols['stop'].append(times['stop'])

        # write each table to sqlite file as a data frame
        con = sqlite3.connect(resultfile)

        metadf = DataFrame(metacols)

        self._write_meta(con,
                         metadf,
                         'CREATE TABLE meta (' \
                         'node TEXT, '     \
                         'start DOUBLE, '      \
                         'stop DOUBLE, '       \
                         'mgenversion TEXT, '  \
                         'PRIMARY KEY (node));')

        rxflowsdf, rxdf, txdf = self._parse_flows(rxflowscols, rxcols, txcols)

        self._write_rxflows(con,
                            rxflowsdf,
                            'CREATE TABLE rxflows (' \
                            'txid INT, '           \
                            'flow INT, '             \
                            'rxnode TEXT, '          \
                            'start DOUBLE, '         \
                            'stop DOUBLE, '          \
                            'PRIMARY KEY (txid, flow));')

        txidscols = {'txnode':[], 'txid':[]}

        txids = txdf.txid.unique()
        if txids:
            txidscols['txnode'].append(hostname)
            txidscols['txid'].append(txids[0])

        self._write_txids(con,
                          DataFrame(txidscols),
                          'CREATE TABLE txids (' \
                          'txnode TEXT, '        \
                          'txid INT, '           \
                          'PRIMARY KEY(txnode));')

        txdf.drop(['txid'], axis=1, inplace=True)
        self._write_tx(con,
                       txdf,
                       'CREATE TABLE tx ('
                       'txnode TEXT, '
                       'flow INT, '
                       'sequence INT, '
                       'size INT, '
                       'txtime double, '
                       'PRIMARY KEY (txnode,flow,sequence));')

        self._write_rx(con,
                       rxdf,
                       'CREATE TABLE rx (' \
                       'rxnode TEXT, '     \
                       'txid INT, '    \
                       'flow INT, '        \
                       'sequence INT, '    \
                       'occurrence INT, '  \
                       'size INT, '        \
                       'txtime double, '   \
                       'rxtime double, '   \
                       'PRIMARY KEY (txid,flow,sequence,occurrence));')

        con.close()


    def _parse_flows(self, rxflowscols, rxcols, txcols):
        rxflows = DataFrame(rxflowscols)

        rxflows['txid'] = rxflows.port.apply(lambda x: int((x / self._flownum_divisor) % self._txid_divisor))

        rxflows['flow'] = (rxflows.port % self._flownum_divisor).apply(int)

        rxflows.drop(['port'], axis=1, inplace=True)

        tx = DataFrame(txcols)

        tx['txid'] = tx.flowid.apply(lambda x: int((x / self._flownum_divisor) % self._txid_divisor))

        if len(tx.txnode.unique()) > 1:
            raise ValueError('Found multiple transmit node ids "%s". Quitting.' \
                             % ','.join(map(str, tx.txnode.unique())))

        tx['flow'] = (tx.flowid % self._flownum_divisor).apply(int)

        tx.drop(['flowid'], axis=1, inplace=True)

        rx = DataFrame(rxcols)

        rx['txid'] = rx.flowid.apply(lambda x: int((x / self._flownum_divisor) % self._txid_divisor))

        rx['flow'] = rx.flowid.apply(lambda x: int(x % self._flownum_divisor))

        rx.drop(['flowid'], axis=1, inplace=True)

        rx['occurrence'] = 1

        rx['occurrence'] = rx.groupby(['txid', 'flow', 'sequence']).cumsum().occurrence

        return (rxflows, rx, tx)


    def combinetrialresults(self, trialfiles, combinedtrialfile, starttime):
        tablenames = ['rx', 'rxflows', 'tx', 'txids', 'meta']

        concatdfs = utils.concat_sqlite_trial_tables(trialfiles, tablenames)

        # Perform some checking and tidying when combining individual mgen files to aggregate
        #
        #     1. Normalize all rx, tx and rxflows times to the minimum reported mgen start time
        #        (and check that the mgen_starttime is the same as the scenario startt time).
        #
        mgen_starttime = min(map(int, concatdfs['meta'].start.unique()))

        # we expect the mgen start time and scenario start time to be the same
        if not mgen_starttime == int(starttime):
            logging.info('Warning. MGEN start time "%d" and scenario start time "%d" are different. ',
                         mgen_starttime, int(starttime))

        if not concatdfs['tx'].empty:
            concatdfs['tx']['txtime'] = concatdfs['tx'].txtime - mgen_starttime

        if not concatdfs['rx'].empty:
            concatdfs['rx']['txtime'] = concatdfs['rx'].txtime - mgen_starttime
            concatdfs['rx']['rxtime'] = concatdfs['rx'].rxtime - mgen_starttime

        if not concatdfs['rxflows'].empty:
            concatdfs['rxflows']['start'] = concatdfs['rxflows'].start - mgen_starttime
            concatdfs['rxflows']['stop'] = concatdfs['rxflows'].stop - mgen_starttime

        #     2. convert txids to txnode names in rx and rxflows tables.
        #        Conversion comes from the txids table. The tx table already has
        #        the txnode name.
        txidsdf = concatdfs['txids']

        txid_to_name = dict(zip(txidsdf.txid, txidsdf.txnode))

        rxdf = concatdfs['rx']
        rxdf['txnode'] = rxdf.txid.apply(lambda txid: txid_to_name[txid])
        rxdf.drop(['txid'], axis=1, inplace=True)

        rxflowsdf = concatdfs['rxflows']
        # ignore any flows that a node registers to listen for, but
        # are not actually transmitted by any node in the scenario
        rxflowsdf.drop(rxflowsdf.index[~rxflowsdf.txid.isin(txid_to_name.keys())], inplace=True)

        rxflowsdf['txnode'] = rxflowsdf.txid.apply(lambda txid: txid_to_name[txid])
        rxflowsdf.drop(['txid'], axis=1, inplace=True)

        with sqlite3.connect(combinedtrialfile) as con:
            self._write_rxflows(con,
                                concatdfs['rxflows'],
                                'CREATE TABLE rxflows (' \
                                'txnode TEXT, '          \
                                'rxnode TEXT, '          \
                                'flow INT, '             \
                                'start DOUBLE, '         \
                                'stop DOUBLE, '          \
                                'PRIMARY KEY (txnode, rxnode, flow));')

            self._write_tx(con,
                           concatdfs['tx'],
                           'CREATE TABLE tx (' \
                           'txnode TEXT, '     \
                           'flow INT, '        \
                           'sequence INT, '    \
                           'size INT, '        \
                           'txtime double, '   \
                           'PRIMARY KEY (txnode,flow,sequence));')

            self._write_rx(con,
                           concatdfs['rx'],
                           'CREATE TABLE rx (' \
                           'txnode TEXT, '     \
                           'rxnode TEXT, '      \
                           'flow INT, '        \
                           'sequence INT, '    \
                           'occurrence INT, '  \
                           'size INT, '        \
                           'txtime double, '   \
                           'rxtime double, '   \
                           'PRIMARY KEY (txnode,rxnode,flow,sequence,occurrence));')

            self._write_meta(con,
                             concatdfs['meta'],
                             'CREATE TABLE meta (' \
                             'node TEXT, '     \
                             'start DOUBLE, '      \
                             'stop DOUBLE, '       \
                             'mgenversion TEXT, '  \
                             'PRIMARY KEY (node));')


    def combinesessionresults(self, combinedtrialfiles, sessionresultfile):
        sessiondfs = utils.concat_sqlite_session_tables(combinedtrialfiles,
                                                        ('rx', 'tx', 'rxflows', 'meta'))

        # concat node tx, rx and rxflows dataframes into a single table
        with sqlite3.connect(sessionresultfile) as con:
            self._write_rxflows(con,
                                sessiondfs['rxflows'],
                                'CREATE TABLE rxflows (' \
                                'trial INT, '            \
                                'txnode TEXT, '          \
                                'rxnode TEXT, '          \
                                'flow INT, '             \
                                'start DOUBLE, '         \
                                'stop DOUBLE, '          \
                                'PRIMARY KEY (trial, txnode, rxnode, flow));')

            self._write_tx(con,
                           sessiondfs['tx'],
                           'CREATE TABLE tx (' \
                           'trial INT, '       \
                           'txnode TEXT, '      \
                           'flow INT, '        \
                           'sequence INT, '    \
                           'size INT, '        \
                           'txtime double, '   \
                           'PRIMARY KEY (trial,txnode,flow,sequence));')

            self._write_rx(con,
                           sessiondfs['rx'],
                           'CREATE TABLE rx (' \
                           'trial INT, '       \
                           'txnode TEXT, '     \
                           'rxnode TEXT, '     \
                           'flow INT, '        \
                           'sequence INT, '    \
                           'occurrence INT, '  \
                           'size INT, '        \
                           'txtime double, '   \
                           'rxtime double, '   \
                           'PRIMARY KEY (trial,txnode,rxnode,flow,sequence,occurrence));')

            self._write_meta(con,
                             sessiondfs['meta'],
                             'CREATE TABLE meta (' \
                             'trial INT, '       \
                             'node TEXT, '         \
                             'start DOUBLE, '      \
                             'stop DOUBLE, '       \
                             'mgenversion TEXT, '  \
                             'PRIMARY KEY (trial,node));')


    def _timestrtofloat(self, timestr):
        timeval = None
        try:
            timeval = float(timestr)
        except ValueError:
            # HH:MM:SS.xxxxxx
            h, m, s = timestr.split(':')
            timeval = float(int(h) * 60 * 60) + float(int(m) * 60) + float(s)
        return timeval


    def _write_meta(self, con, df, schema):
        con.execute('DROP TABLE IF EXISTS meta;')

        con.execute(schema)

        df.to_sql('meta',
                  con,
                  if_exists='append', index=False)

        con.commit()


    def _write_rxflows(self, con, df, schema):
        con.execute("DROP TABLE IF EXISTS rxflows;")

        con.execute(schema)

        df.to_sql('rxflows',
                  con,
                  if_exists='append', index=False)

        con.commit()


    def _write_rx(self, con, df, schema):
        con.execute("DROP TABLE IF EXISTS rx;")

        con.execute(schema)

        df.to_sql('rx', con, index=False, if_exists='append')

        con.commit()


    def _write_tx(self, con, df, schema):
        con.execute("DROP TABLE IF EXISTS tx;")

        con.execute(schema)

        df.to_sql('tx', con, index=False, if_exists='append')

        con.commit()


    def _write_txids(self, con, df, schema):
        con.execute("DROP TABLE IF EXISTS txids;")

        con.execute(schema)

        df.to_sql('txids', con, index=False, if_exists='append')

        con.commit()
