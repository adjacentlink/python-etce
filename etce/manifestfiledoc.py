#
# Copyright (c) 2014-2017 - Adjacent Link LLC, Bridgewater, New Jersey
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

import copy
import os
import sets

import lxml.etree

import etce.xmldoc
import etce.utils
from etce.config import ConfigDictionary


class ManifestFileDoc(etce.xmldoc.XMLDoc):
    def __init__(self, manifestfile):
        etce.xmldoc.XMLDoc.__init__(self,
                                    'manifestfile.xsd')

        if not os.path.exists(manifestfile) or not os.path.isfile(manifestfile):
            raise ValueError('Cannot find manifest file "%s". Quitting.' %
                             manifestfile)

        self._parsefile(manifestfile)


    def name(self):
        return self._name


    def tags(self):
        return copy.copy(self._tags)


    def description(self):
        return self._description


    def indices(self):
        '''
        Mapping of indices of the templatefileelem atribute
        to hostname. Hostname either determined by the default
        hostname built from configuration DEFAULT_ETCE_HOSTNAME_FORMAT
        or explicitly by the templatefileelem host attribute list.
        '''
        return copy.copy(self._indices)


    def template_file_names(self):
        return self._template_file_names


    def template_directory_names(self):
        return self._template_directory_names


    def formatted_directory_names(self):
        '''
        Union of all of the directory names generated
        by a template file or template directory
        '''
        return self._formatted_directory_names


    def findall(self, xpathstr):
        return self._rootelem.findall(xpathstr)


    def has_base_directory(self):
        return not self._basedir is None

    
    def base_directory(self):
        # relative path to local path
        if self._basedir:
            return self._basedir

        return ''


    def rewrite_without_basedir(self, outfile):
        new_root = lxml.etree.Element('manifest')

        # preserve our root
        doc_copy = copy.deepcopy(self._rootelem)
        
        for elem in doc_copy:
            new_root.append(elem)

        with open(outfile, 'w') as outf:
            outf.write(lxml.etree.tostring(new_root, pretty_print=True))


    def _parsefile(self, manifestfile):
        # open manifestfile, extract its contents
        self._rootelem = self.parse(manifestfile)

        self._basedir = self._rootelem.attrib.get('base', None)
 
        self._indices = self._parseindices(self._rootelem)

        self._template_file_names,      \
        self._template_directory_names, \
        self._formatted_directory_names = self._read_formattednames(self._rootelem)

        self._name = self.findall('./name')[0].text

        self._tags = {}

        tagelems = self.findall('./tags/tag')
        if len(tagelems):
            for tagelem in tagelems[0]:
                self._tags[tagelem.attrib['name']] = tagelem.attrib['value']

        self._description = self.findall('./description')[0].text


    def _parseindices(self, rootelem):
        indicesset = set([])

        hosts = []

        for templateselem in rootelem.findall('./templates'):

            indices = etce.utils.nodestrtonodes(
                templateselem.get('indices', None))

            indicesset.update(indices)

            for elem in list(templateselem):
                templateindicesset = \
                    set(etce.utils.nodestrtonodes(elem.attrib.get('indices', None)))

                if not templateindicesset.issubset(indicesset):
                    message = 'indices for template element "%s" are not ' \
                              'a subset of parent templatefiles indices. ' \
                              'Quitting.' % elem.attrib['name']
                    raise RuntimeError(message)

        return sorted(list(indicesset))


    def _read_formattednames(self, rootelem):
        template_file_names = set([])

        template_directory_names = set([])

        formatted_dir_names = set([])

        default_hostname_format = ConfigDictionary().get('etce', 'DEFAULT_ETCE_HOSTNAME_FORMAT')

        template_suffix = ConfigDictionary().get('etce', 'TEMPLATE_SUFFIX')

        for templateselem in rootelem.findall('./templates'):

            for templatefileelem in templateselem.findall('./file'):
                filename = templatefileelem.attrib.get('name')

                template_file_names.update([filename])

                # use the file indicesset if present
                indices = self._indices

                if 'indices' in templatefileelem.attrib:
                    indices = etce.utils.nodestrtonodes(templatefileelem.attrib['indices'])

                hostname_format = \
                    templatefileelem.attrib.get('hostname_format',
                                                default_hostname_format)

                for index in indices:
                    formatted_dir_names.update([hostname_format % index ])

            # generated template directories are hostnames for the host where
            # they will be run
            for templatedirelem in templateselem.findall('./directory'):
                template_directory = '.'.join([templatedirelem.attrib['name'], template_suffix])

                template_directory_names.update([template_directory])

                # use the file indicesset if present
                indices = self._indices

                if 'indices' in templatedirelem.attrib:
                    indices = etce.utils.nodestrtonodes(templatedirelem.attrib['indices'])

                hostname_format = templatedirelem.attrib.get('hostname_format', default_hostname_format)

                for index in indices:
                    formatted_dir_names.update([hostname_format % index])

        return (sets.ImmutableSet(template_file_names),
                sets.ImmutableSet(template_directory_names),
                sets.ImmutableSet(formatted_dir_names))
