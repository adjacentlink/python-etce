#
# Copyright (c) 2016-2018 - Adjacent Link LLC, Bridgewater, New Jersey
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

import os

from etce.templateutils import format_file,format_string
from etce.chainmap import ChainMap
from etce.config import ConfigDictionary


class TemplateDirectoryBuilder(object):
    """
    Creates a realized configuration directory from a template directory
    using the provided text overlays for each index in the provided
    indices.
    """

    def __init__(self,
                 templatedirname,
                 indices,
                 reserved_overlays,
                 testfile_global_overlays,
                 templates_global_overlaylists,
                 template_local_overlays,
                 template_local_overlaylists,
                 relative_path,
                 hostname_format):
        template_suffix = ConfigDictionary().get('etce', 'TEMPLATE_DIRECTORY_SUFFIX')

        self._name = templatedirname

        self._template_directory_name = '.'.join([self._name, template_suffix])

        self._indices = indices

        self._reserved_overlays = reserved_overlays

        self._global_overlays = testfile_global_overlays

        self._templates_global_overlaylists = templates_global_overlaylists

        self._relative_path = relative_path

        self._hostname_format = hostname_format

        self._template_local_overlays = template_local_overlays

        self._template_local_overlaylists = template_local_overlaylists


    @property
    def name(self):
        return self._name


    @property
    def template_file_key(self):
        return self._relative_path + '/'


    @property
    def template_directory_name(self):
        return self._template_directory_name


    @property
    def indices(self):
        return self._indices


    @property
    def formatted_hostnames(self):
        formatted_hostnames = []
        for index in self.indices:
            chainmap = ChainMap({'etce_index':index},
                                self._template_local_overlaylists[index],
                                self._template_local_overlays,
                                self._templates_global_overlaylists[index],
                                self._global_overlays)

            formatted_hostnames.append(format_string(self._hostname_format, chainmap))

        return formatted_hostnames


    def prune(self, subdirectory_map):
        '''
        remove template filenames that appear in the filelist
        '''
        rmentrys = []

        for relpath in subdirectory_map:
            if relpath.startswith(self._relative_path + '/'):
                rmentrys.append(relpath)

        for rmentry in rmentrys:
            subdirectory_map.pop(rmentry)

        return subdirectory_map


    def instantiate(self,
                    subdirectory_map,
                    publishdir,
                    logdir,
                    runtime_overlays,
                    env_overlays,
                    etce_config_overlays):
        for index in self.indices:
            self._createdir(subdirectory_map,
                            publishdir,
                            logdir,
                            index,
                            runtime_overlays,
                            env_overlays,
                            etce_config_overlays)


    def _createdir(self,
                   subdirectory_map,
                   publishdir,
                   logdir,
                   index,
                   runtime_overlays,
                   env_overlays,
                   etce_config_overlays):
        self._reserved_overlays['etce_index'] = index

        # etce_hostname formats are limited to the index and the
        # overlays specified in the test.xml file.
        etce_hostname_cm = ChainMap({'etce_index': self._reserved_overlays['etce_index']},
                                    self._template_local_overlaylists[index],
                                    self._template_local_overlays,
                                    self._templates_global_overlaylists[index],
                                    self._global_overlays)

        self._reserved_overlays['etce_hostname'] = \
            format_string(self._hostname_format, etce_hostname_cm)

        if logdir:
            self._reserved_overlays['etce_log_path'] = \
                os.path.join(logdir, self._reserved_overlays['etce_hostname'])

        node_publishdir = os.path.join(publishdir, self._reserved_overlays['etce_hostname'])

        non_reserved_overlays = [runtime_overlays,
                                 env_overlays,
                                 self._template_local_overlaylists[index],
                                 self._template_local_overlays,
                                 self._templates_global_overlaylists[index],
                                 self._global_overlays,
                                 etce_config_overlays]

        other_keys = set([])

        for some_overlays in non_reserved_overlays:
            other_keys.update(some_overlays)

        key_clashes = other_keys.intersection(set(self._reserved_overlays))

        if key_clashes:
            raise ValueError('Overlay keys {%s} are reserved. Quitting.' % \
                             ','.join(map(str, key_clashes)))

        overlays = ChainMap(self._reserved_overlays, *non_reserved_overlays)

        print('Processing template directory "%s" for etce_index=%d ' \
              'and destination=%s' % \
              (self.template_directory_name, index, node_publishdir))

        if not os.path.exists(node_publishdir):
            os.makedirs(node_publishdir)

        found = False

        for relpath, entry in subdirectory_map.items():
            # only process files for this template
            if not relpath.startswith(self._relative_path + '/'):
                continue

            # ignore files outside of the template directory
            pathtoks = relpath.split(os.path.sep)

            if not pathtoks[0] == self.template_directory_name:
                continue

            dstfile = os.path.join(node_publishdir, *pathtoks[1:])

            dstdir = os.path.dirname(dstfile)

            if not os.path.exists(dstdir):
                os.makedirs(dstdir)

            format_file(entry.full_name, dstfile, overlays)


    def __str__(self):
        retstr = 'TemplateDir\n'
        retstr += self._name + '\n'
        retstr += ' '.join(map(str, self._indices))
        return retstr
