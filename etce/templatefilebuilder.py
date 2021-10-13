#
# Copyright (c) 2014-2018 - Adjacent Link LLC, Bridgewater, New Jersey
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

import os.path

from etce.chainmap import ChainMap
from etce.templateutils import format_file, format_string
from etce.utils import configstrtoval
from etce.overlaylistchainfactory import OverlayListChainFactory


class TemplateFileBuilder(object):
    """
    Creates a realized configuration file from a template file
    using the provided text overlays for each index in the provided
    indices.
    """

    def __init__(self,
                 templatefileelem,
                 indices,
                 reserved_overlays,
                 testfile_global_overlays,
                 templates_global_overlaylists):

        self._global_overlays = testfile_global_overlays

        self._templates_global_overlaylists = templates_global_overlaylists

        self._name = templatefileelem.attrib['name']

        self._indices = indices

        self._reserved_overlays = reserved_overlays

        self._hostname_format, \
        self._output_file_name = self._read_attributes(templatefileelem)

        # build local overlay chain
        self._template_local_overlays = {}

        for overlayelem in templatefileelem.findall('./overlay'):
            oname = overlayelem.attrib['name']

            oval = overlayelem.attrib['value']

            otype = overlayelem.attrib.get('type', None)

            self._template_local_overlays[oname] = configstrtoval(oval, argtype=otype)

        self._template_local_overlaylists = \
            OverlayListChainFactory().make(templatefileelem.findall('./overlaylist'),
                                           self._indices)


    @property
    def name(self):
        return self._name


    @property
    def template_file_key(self):
        return self.name


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
        remove template filenames that appear in the subdirectory_map
        '''
        if self._name in subdirectory_map:
            subdirectory_map.pop(self._name)

        return subdirectory_map


    def instantiate(self,
                    subdirectory_map,
                    publishdir,
                    logdir,
                    runtime_overlays,
                    env_overlays,
                    etce_config_overlays):
        templatefilenameabs = subdirectory_map[self._name].full_name

        if not os.path.exists(templatefilenameabs) or \
           not os.path.isfile(templatefilenameabs):
            raise ValueError('ERROR: %s templatefile does not exist'
                             % templatefilenameabs)
        self._absname = templatefilenameabs

        for index in self._indices:
            self._createfile(publishdir,
                             logdir,
                             index,
                             runtime_overlays,
                             env_overlays,
                             etce_config_overlays)


    def _createfile(self,
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

        self._reserved_overlays['etce_hostname'] = format_string(self._hostname_format, etce_hostname_cm)

        if logdir:
            self._reserved_overlays['etce_log_path'] = \
                os.path.join(logdir, self._reserved_overlays['etce_hostname'])

        publishfile = os.path.join(publishdir,
                                   self._reserved_overlays['etce_hostname'],
                                   self._output_file_name)

        other_keys = set([])

        non_reserved_overlays = [runtime_overlays,
                                 env_overlays,
                                 self._template_local_overlaylists[index],
                                 self._template_local_overlays,
                                 self._templates_global_overlaylists[index],
                                 self._global_overlays,
                                 etce_config_overlays]

        for some_overlays in non_reserved_overlays:
            other_keys.update(some_overlays)

        key_clashes = other_keys.intersection(set(self._reserved_overlays.keys()))

        if key_clashes:
            raise ValueError('Overlay keys {%s} are reserved. Quitting.' % \
                             ','.join(map(str, key_clashes)))

        overlays = ChainMap(self._reserved_overlays, *non_reserved_overlays)

        # format str can add subdirectories, so make those if necessary
        if not os.path.exists(os.path.dirname(publishfile)):
            os.makedirs(os.path.dirname(publishfile))

        if os.path.exists(publishfile):
            print('Warning: %s already exists. Overwriting!' % publishfile)

        format_file(self._absname, publishfile, overlays)


    def _read_attributes(self, templatefileelem):
        hostname_format = \
            templatefileelem.attrib['hostname_format']

        outputfilename = \
            templatefileelem.attrib.get('output_file_name',
                                        templatefileelem.attrib['name'])

        return (hostname_format, outputfilename)


    def __str__(self):
        retstr = 'TemplateFileBuilder\n'
        retstr += self.name + '\n'
        retstr += ' '.join(map(str, self._indices))
        return retstr
