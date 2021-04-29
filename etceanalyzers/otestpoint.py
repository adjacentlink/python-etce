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
from collections import defaultdict
import logging
import sqlite3

import pandas as pd
from otestpoint.interface.measurementtable_pb2 import MeasurementTable
from etceanalytics import utils
from etceanalytics.analyzer import Analyzer
from etceanalytics.probedataaligner import ProbeDataAligner


class OTestpoint(Analyzer):
    '''
    Extract probe values from otestpoint data file into a database.
    Probes are chosen by the configuration file.
    '''
    def __init__(self, ctx):
        self._config = ctx.config


    @property
    def input_file(self):
        return 'otestpoint.data'


    @property
    def file_fields(self):
        return ('otestpoint', 'sqlite')


    def analyzefile(self, pathinfo, resultfile):
        # this is the output. key is the name of the output table, value is a dictionary
        # of form { column_name: [ list of column values ] } where all lists are the
        # same length for the same table
        dbtables = defaultdict(lambda: {})

        probe_stats_entries = self._parse_config_stats()

        self._get_stat_values(pathinfo.absdatafile, probe_stats_entries, dbtables)

        self._prune_empty_stats(dbtables)

        # map of probename, tablename and columns in table to capture
        # these must match the actual probe, table and column names
        # to extract from the otestpoint.data file.
        #
        # {probename1 : {'tablename1': [ 'column1','column2' ... ],
        #                'tablename2': [ 'column1','column2' ....]},
        #  probename2 : {'tablename1': [ 'column1','column2' ... ],
        #                'tablename2': [ 'column1','column2' ....]},
        #     ...
        probe_table_entries = self._parse_config_tables()

        self._get_table_values(pathinfo.absdatafile, probe_table_entries, dbtables)

        self._store_tables(resultfile, dbtables)


    def combinetrialresults(self, trialfiles, combinedtrialfile, starttime):
        # read node individual dbs
        concatdfs = utils.concat_sqlite_trial_tables(trialfiles)

        # concat individual node dbs
        with sqlite3.connect(combinedtrialfile) as con:
            for tablename, df in concatdfs.items():
                if df.empty:
                    logging.info('Warning found empty table "%s" in file %s". Skipping',
                                 tablename,
                                 combinedtrialfile)
                    continue

                df['timestamp'] = df.timestamp - starttime

                df.to_sql(tablename, con, if_exists='replace', index=False)

            con.commit()


    def combinesessionresults(self, combinedtrialfiles, sessionresultfile):
        # join multiple trials into one data frame
        sessiondfs = utils.concat_sqlite_session_tables(combinedtrialfiles)

        with sqlite3.connect(sessionresultfile) as con:
            for tablename, df in sessiondfs.items():
                df.to_sql(tablename, con, if_exists='replace')

            con.commit()


    def _parse_config_stats(self):
        # stats read from probe file
        stats = {}

        for s in self._config.statistics:
            probename = s.probe

            entries = s.entries

            if not probename in stats:
                stats[probename] = []

            stats[probename].extend(entries)

        return stats


    def _get_stat_values(self, datafile, probe_stats_entries, dbtables):
        # run through each probe, accumulate all of the requested stats
        # from that probe vs. the nodename and timestamp (key) into a
        # DataFrame and then concat all of the probes together
        for probename, entries in probe_stats_entries.items():
            aligner = ProbeDataAligner(list(zip([datafile,])),
                                       ((probename,),))


            tablename = probename + '_statistics'

            tablename = tablename.replace('.', '_').replace(' ', '_').lower()

            if not tablename in dbtables:
                dbtables[tablename] = defaultdict(lambda: [])

            for data in aligner:
                for pentry in data:
                    if not pentry:
                        continue

                    for entry in entries:
                        _, tag, timestamp, _, _, msg = pentry[0]

                        dbtables[tablename]['timestamp'].append(timestamp)

                        dbtables[tablename]['nodename'].append(tag)

                        val = msg.__getattribute__(entry)

                        column = entry.replace('.', '_').replace(' ', '_').lower()

                        dbtables[tablename][column].append(val)



    def _prune_empty_stats(self, dbtables):
        for _, statdict in dbtables.items():
            empties = []

            for statname, statvals in statdict.items():
                if len(statvals) == 0:
                    empties.append(statname)

            for statname in empties:
                statdict.pop(statname)


    def _parse_config_tables(self):
        probe_table_entries = {}

        for t in self._config.tables:
            probename = t.probe

            tablename = t.table

            entries = t.entries

            if not probename in probe_table_entries:
                probe_table_entries[probename] = {}

            if not tablename in probe_table_entries[probename]:
                probe_table_entries[probename][tablename] = []

            probe_table_entries[probename][tablename].extend(entries)

        return probe_table_entries


    def _get_table_values(self, datafile, probe_table_entries, dbtables):
        for probename, tabledict in probe_table_entries.items():
            aligner = ProbeDataAligner(list(zip([datafile,])),
                                       ((probename,),))

            i = 0
            for data in aligner:
                for pentry in data:
                    if len(pentry) == 0:
                        continue

                    _, tag, timestamp, _, _, msg = pentry[0]

                    i += 1

                    for probetablename, entries in tabledict.items():
                        tablename = probename + '_' + probetablename

                        tablename = tablename.replace('.', '_').replace(' ', '_').lower()

                        if not tablename in dbtables:
                            dbtables[tablename] = defaultdict(lambda: [])

                        probetable = msg.__getattribute__(probetablename)

                        columns = [entry.replace('.', '_').replace(' ', '_').lower()
                                   for entry in entries]

                        entries_and_columns = list(zip(entries, columns))

                        if isinstance(probetable, MeasurementTable):
                            self._measurement_table_to_dict(probetable,
                                                            dbtables[tablename],
                                                            timestamp,
                                                            tag,
                                                            entries_and_columns)
                        else:
                            for tentry in probetable.entries:
                                dbtables[tablename]['timestamp'].append(timestamp)

                                dbtables[tablename]['nodename'].append(tag)

                                for entry, column in entries_and_columns:
                                    val = tentry.__getattribute__(entry)

                                    dbtables[tablename][column].append(val)


    def _store_tables(self, resultfile, dbtables):
        # convert collected tables to a data frame and write to sqlite output file
        with sqlite3.connect(resultfile) as con:
            for tablename, columndict in dbtables.items():
                df = pd.DataFrame(columndict)

                df.to_sql(tablename, con, if_exists='replace')


    def _measurement_table_to_dict(self, probetable, dbtable, timestamp, tag, entries_and_columns):
        labels = list(probetable.labels)

        for row in probetable.rows:
            dbtable['timestamp'].append(timestamp)

            dbtable['nodename'].append(tag)

            for entry, column in entries_and_columns:
                colindex = labels.index(entry)

                value = row.values[colindex]

                if value.type == MeasurementTable.Measurement.TYPE_SINTEGER:
                    dbtable[column].append(value.iValue)

                elif value.type == MeasurementTable.Measurement.TYPE_UINTEGER:
                    dbtable[column].append(value.uValue)

                elif value.type == MeasurementTable.Measurement.TYPE_DOUBLE:
                    dbtable[column].append(value.dValue)

                elif value.type == MeasurementTable.Measurement.TYPE_STRING:
                    dbtable[column].append(value.sValue)
