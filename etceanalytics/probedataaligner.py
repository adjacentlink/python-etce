#
# Copyright (c) 2014,2019 - Adjacent Link LLC, Bridgewater, New Jersey
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

import logging
import sqlite3
import re
import otestpoint.interface.probereport_pb2
from otestpoint.interface import make_measurement_operator


class OtestpointProbeOperatorNotFoundError(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)


class ProbeDataAlignInput:
    def __init__(self,
                 probe_data_file,
                 probe_db_file,
                 probes):
        self._conn = sqlite3.connect(probe_db_file)

        self._ifd = open(probe_data_file, "rb")

        def regexp(expr, item):
            reg = re.compile(expr)
            return not reg.search(item) is None

        self._conn.create_function("REGEXP", 2, regexp)

        self._first = None

        self._last = None

        self._cursors = []

        self._operators = {}

        if isinstance(probes, str):
            self._probes = (probes,)
        else:
            self._probes = probes

        sql = 'SELECT time FROM probes WHERE probe REGEXP ? ORDER BY ROWID ASC LIMIT 1'

        for probe in  self._probes:
            for row in self._conn.execute(sql, [probe.replace('.', r'\.')]):
                if self._first is None or self._first < int(row[0]):
                    self._first = int(row[0])

        sql = 'SELECT time FROM probes WHERE probe REGEXP ? ORDER BY ROWID DESC LIMIT 1'

        for probe in  self._probes:
            for row in self._conn.execute(sql, [probe.replace('.', r'\.')]):
                if self._last is None or self._last > int(row[0]):
                    self._last = int(row[0])

        self._start = self._first

        self._end = self._last

    def probes(self):
        return self._probes

    def get_first_timestamp(self):
        return self._first

    def get_last_timestamp(self):
        return self._last

    def align(self, start, end):
        # Allow for files that contain no probe data
        if self._first is None:
            return

        if start < self._first:
            raise ValueError("start %s timestamp before first %s timestamp" \
                             % (start, self._first))

        if start > self._last:
            raise ValueError("start %s timestamp after last %s timestamp" \
                             % (start, self._last))

        self._start = start

        if end > self._last:
            raise ValueError("end %s timestamp after last %s timestamp" \
                             % (end, self._last))

        if end < self._first:
            raise ValueError("end %s timestamp before first %s timestamp" \
                             % (end, self._first))

        self._end = end

        sql = "SELECT offset,size FROM probes " \
            "WHERE time BETWEEN ? and ? and probe REGEXP ? ORDER BY time ASC;"


        for probe in self._probes:
            cursor = self._conn.cursor()
            self._cursors.append(cursor)
            cursor.execute(sql, [self._start, self._end, probe.replace('.', r'\.')])


    def get_next(self):
        result = []

        # Allow for files that contain no probe data
        if self._first is None:
            return result

        for cursor in self._cursors:

            row = cursor.fetchone()

            if row:
                offset, size = row

                self._ifd.seek(offset)

                msg = self._ifd.read(size)

                report = otestpoint.interface.probereport_pb2.ProbeReport()

                report.ParseFromString(msg)

                operator = self._get_operator(report)

                measurement = operator.create(report.data.blob)

                result.append((report.index,
                               report.tag,
                               report.timestamp,
                               report.tag,
                               report.data.version,
                               measurement))

            else:
                result.append(None)

        return result

    def _get_operator(self, report):
        operator = None

        if report.data.name not in self._operators:
            measurement_operator = make_measurement_operator(report.data.module,
                                                             report.data.name)

            if not measurement_operator:
                raise OtestpointProbeOperatorNotFoundError( \
                        'No operator found for module "%s" '\
                        'and name "%s". Quitting. ' \
                        % (report.data.module, report.data.name))

            operator = measurement_operator()

            self._operators[report.data.name] = operator

        else:
            operator = self._operators[report.data.name]

        return operator


class ProbeDataAligner:
    def __init__(self, inputs, probes):

        self._probe_data_align_inputs = []

        start = None
        end = None
        for filenames in inputs:
            aligners = []

            for filename, fileprobes in zip(filenames, probes):
                p = ProbeDataAlignInput(filename,
                                        filename + '.db',
                                        fileprobes)

                if p.get_first_timestamp() is None:
                    logging.debug('No entries found in file "%s" for probes "%s". Skipping.',
                                  filename,
                                  ' '.join(fileprobes))
                    continue

                if not start is None:
                    start = max(start, p.get_first_timestamp())
                else:
                    start = p.get_first_timestamp()

                if not end is None:
                    end = min(end, p.get_last_timestamp())
                else:
                    end = p.get_last_timestamp()

                aligners.append(p)

            self._probe_data_align_inputs.append(aligners)

        for aligners in self._probe_data_align_inputs:
            for align in aligners:
                align.align(start, end)

        self._start = start

        self._end = end


    def range(self):
        return (self._start, self._end)


    def __iter__(self):
        while True:
            total = []

            timestamp_cached = None

            for aligners in self._probe_data_align_inputs:
                data = []

                for align in aligners:
                    n = align.get_next()

                    for item in n:
                        if not item is None:
                            _, _, timestamp, _, _, _ = item

                            if timestamp_cached is None:
                                timestamp_cached = timestamp

                            elif timestamp_cached != timestamp:
                                raise IndexError("timestamp alignment error %d" % timestamp_cached)

                            data.append(item)

                        else:
                            return

                if len(data) > 0:
                    total.append(data)

            if len(total) > 0:
                yield total
            else:
                return
