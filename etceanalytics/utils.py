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

from __future__ import absolute_import, division, print_function
from collections import defaultdict
import logging
import math
import sqlite3
import pandas as pd


def concat_csv_trial_files(csvfiles):
    # concat individual node configs
    dataframes = list(map(pd.read_csv, csvfiles))
    return pd.concat(dataframes, axis=0, ignore_index=True)


def concat_csv_session_files(csvfiles):
    dataframes = list(map(pd.read_csv, csvfiles))
    for i, df in enumerate(dataframes, start=1):
        df['trial'] = i
    return pd.concat(dataframes, axis=0, ignore_index=True)


def concat_sqlite_trial_tables(resultdbs, tablenames=None):
    trialdfs = defaultdict(lambda: [])

    # read tables from each trial - read all tables if tablenames is None
    for resultdb in resultdbs:
        with sqlite3.connect(resultdb) as con:
            thistablenames = tablenames
            if not thistablenames:
                thistablenames = \
                    sorted(
                        list(
                            {tablenametpl[0]
                             for tablenametpl
                             in con.execute('select tbl_name from sqlite_master')}))

            for tablename in thistablenames:
                trialdfs[tablename].append(pd.read_sql('select * from %s' % tablename, con))

    # prune 0 length data frames - preserves types
    trialdfs2 = defaultdict(lambda: [])
    for tablename, dflist in trialdfs.items():
        for df in dflist:
            trialdfs2[tablename].append(df)

    # but make sure we have at least one table, even if it is empty
    for tablename, dflist in trialdfs2.items():
        if len(dflist) == 0:
            dflist.append(trialdfs[tablename])

    concatdfs = defaultdict(pd.DataFrame)
    for tablename, dflist in trialdfs2.items():
        concatdfs[tablename] = \
            pd.concat(dflist, axis=0, ignore_index=True, sort=True)

    return concatdfs


def concat_sqlite_session_tables(sessiondbs, tablenames=[]):
    tablenames_set = set(tablenames)

    sessiondfs = defaultdict(lambda: [])

    for i, db in enumerate(sessiondbs, start=1):
        with sqlite3.connect(db) as con:
            tablenames_set.update(
                [tablenametpl[0]
                 for tablenametpl in con.execute('select tbl_name from sqlite_master')])

            for tablename in tablenames_set:
                try:
                    df = pd.read_sql('select * from %s' % tablename, con)

                    df['trial'] = i

                    sessiondfs[tablename].append(df)

                except sqlite3.DatabaseError:
                    logging.error('"%s" table not found in "%s". Skipping.',
                                  tablename,
                                  db)
                except pd.io.sql.DatabaseError:
                    logging.error('"%s" table not found in "%s". Skipping.',
                                  tablename,
                                  db)

    # prune 0 length data frames - preserves types
    sessiondfs2 = defaultdict(lambda: [])
    for tablename, dflist in sessiondfs.items():
        for df in dflist:
            if len(df) > 0:
                sessiondfs2[tablename].append(df)

    # but make sure we have at least one table, even if it is empty
    for tablename, dflist in sessiondfs2.items():
        if len(dflist) == 0:
            dflist.append(sessiondfs[tablename])

    # concat the iterations
    concatdfs = {}
    for tablename, dflist in sessiondfs2.items():
        concatdfs[tablename] = \
            pd.concat(dflist, axis=0, ignore_index=True, sort=True)

    return concatdfs



# Adapted from:
# https://stackoverflow.com/questions/22787209/how-to-have-clusters-of-stacked-bars-with-python-pandas
def grouped_stacked_barchart(dataframes, ax, **kwargs):
    """
    Given a list of dataframes, with identical columns and index,
    create a clustered stacked bar plot. labels is a list of the
    names of the dataframe, used for the legend title is a string
    for the title of the plot H is the hatch used for identification
    of the different dataframe

    number of dfs is number of bars in each group
    number of rows is the number of groups
    number of columns is the number of stacked colors
    """
    bars_per_group = len(dataframes)

    bar_width = None

    num_groups, num_stacked_bars = dataframes[0].shape

    # make sure all data frames contain the same set of indices
    indices = set([])

    map(lambda df: indices.update(df.index), dataframes)

    for df in dataframes:
        df = df.reindex(indices)
        df = df.replace(math.nan, 0)

    for _, df in enumerate(dataframes):
        df.plot(kind="bar",
                stacked=True,
                ax=ax,
                grid=True,
                **kwargs)

    h, _ = ax.get_legend_handles_labels()

    # legend keys are bar labels and values are associated patches (artists)
    legend = {}

    for i in range(0, bars_per_group * num_stacked_bars, num_stacked_bars):

        for pa in h[i:i+num_stacked_bars]:

            for _, rect in enumerate(pa.patches):
                # Each get_x call shifts by 1. So each of the patches in a patch
                # set gets moved over by
                bar_width = rect.get_width() / float(bars_per_group)

                x_orig = rect.get_x()

                x = x_orig + (bar_width * (float((i/num_stacked_bars)) + 0.5))

                rect.set_width(bar_width)

                rect.set_x(x)

                legend[pa.get_label()] = pa

    xt = list(map(lambda x: x / 2.0,
                  map(lambda x: x + bar_width, range(0, 2 * num_groups, 2))))

    ax.set_xticks(xt)

    ax.set_xticklabels(df.index, rotation=0)

    return legend
