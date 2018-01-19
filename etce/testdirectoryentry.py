#
# Copyright (c) 2018 - Adjacent Link LLC, Bridgewater, New Jersey
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
from etce.config import ConfigDictionary


class TestDirectoryEntry(object):
    ''' This is a helper class for managing test directory
        files, which may be spread across two locations,
        the test directory and a base directory. Various
        parts of the absolute filename are referenced
        by these names:


        test_directory/root_sub_entry/tail
                       -------------------
                        sub_path
        -----------------------------
         root_sub_entry_absolute
        ----------------------------------
         full_name


    '''

    def __init__(self, test_directory, sub_path):
        self._test_directory = test_directory

        self._sub_path = sub_path

        self._full_name = os.path.join(self._test_directory, self._sub_path)

        sub_path_toks = sub_path.split(os.path.sep)

        self._root_sub_entry = sub_path_toks[0]

        self._root_sub_entry_absolute = os.path.join(test_directory, self._root_sub_entry)

        self._tail = ''
        if len(sub_path_toks) > 1:
            self._tail = os.path.sep.join(sub_path_toks[1:])


        self._root_sub_entry_isdir = os.path.isdir(self._root_sub_entry_absolute)
        
        suffix = ConfigDictionary().get('etce', 'TEMPLATE_DIRECTORY_SUFFIX')

        self._template_directory_member = \
            self._root_sub_entry.endswith('.' + suffix) and \
            os.path.isdir(os.path.join(test_directory, self._root_sub_entry))


    @property
    def full_name(self):
        return self._full_name


    @property
    def test_directory(self):
        return self._test_directory


    @property
    def sub_path(self):
        return self._sub_path


    @property
    def root_sub_entry(self):
        return self._root_sub_entry


    @property
    def root_sub_entry_absolute(self):
        return self._root_sub_entry_absolute

                          
    @property
    def tail(self):
        return self._tail


    @property
    def root_sub_entry_is_dir(self):
        self._root_sub_entry_isdir


    @property
    def template_directory_member(self):
        return self._template_directory_member
