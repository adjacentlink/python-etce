#
# Copyright (c) 2017 - Adjacent Link LLC, Bridgewater, New Jersey
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

import csv


class OverlayCSVReader(object):
    def __init__(self, csvfile):
        self._csvfile = csvfile
        self._column_dict = self._parse(csvfile)


    def values(self, column_name):
        if not column_name in self._column_dict:
            message = '"%s" column name not present in "%s". Quitting.' \
                       % (column_name, self._csvfile)
            raise ValueError(message)

        overlay_dict = {}

        for n,v in zip(self._column_dict['name'], 
                         self._column_dict[column_name]):
            overlay_dict[n] = v

        return overlay_dict


    def _parse(self, csvfile):
        with open(csvfile) as csvf:
            rows = list(csv.reader(csvf))

        rowlens = set([ len(r) for r in rows ])
        if len(rowlens) > 1:
            raise ValueError('"%s" file rows not the same length. Quitting.' \
                             % (csvfile))
        
        names = rows[0]

        if not 'NAME' in [ n.upper() for n in names ]:
            message = 'No "name" column header found in "%s" ' \
                      'overlay file. Quitting' % csvfile
            raise ValueError(message)

        column_vals = zip(*rows[1:])

        column_dict = {}

        for name,vals in zip(names,column_vals):
            column_dict[name] = vals

        return column_dict

