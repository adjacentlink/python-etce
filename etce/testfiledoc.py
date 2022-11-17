#
# Copyright (c) 2018,2022 - Adjacent Link LLC, Bridgewater, New Jersey
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

import lxml.etree

import etce.xmldoc
import etce.utils
from etce.templatedirectorybuilder import TemplateDirectoryBuilder
from etce.templatedirectorybuilderconfig import TemplateDirectoryBuilderConfig
from etce.templatefilebuilder import TemplateFileBuilder
from etce.templatefilebuilderconfig import TemplateFileBuilderConfig
from etce.overlaycsvreader import OverlayCSVReader
from etce.overlaylistchainfactory import OverlayListChainFactory


class TestFileDoc(etce.xmldoc.XMLDoc):
    def __init__(self, testfile):
        etce.xmldoc.XMLDoc.__init__(self,
                                    'testfile.xsd')

        if not os.path.exists(testfile) or not os.path.isfile(testfile):
            raise ValueError('Cannot find test file "%s". Quitting.' %
                             testfile)

        self._rootelem = self._parsefile(testfile)


    @property
    def name(self):
        return self._name


    @property
    def tags(self):
        return copy.copy(self._tags)


    @property
    def description(self):
        return self._description


    @property
    def reserved_overlays(self):
        return copy.copy(self._reserved_overlays)


    @property
    def indices(self):
        ''' Return the numeric test indices defined by the (optional) test.xml
            templates indices attribute.'''
        return copy.copy(self._indices)


    def global_overlays(self, subdirectory_map):
        global_overlays = copy.copy(self._global_overlays)

        for csvfile, column in self._global_overlay_csvfiles:
            csvfileabs = subdirectory_map[csvfile].full_name

            global_overlays.update(OverlayCSVReader, csvfileabs).values(column)

        return global_overlays


    @property
    def templates(self):
        return self._templates


    @property
    def template_directory_names(self):
        return self._template_directory_names


    @property
    def formatted_directory_names(self):
        '''
        Union of all of the directory names generated
        by a template file or template directory
        '''
        return self._formatted_directory_names


    @property
    def has_base_directory(self):
        return not self._base_directory is None


    @property
    def base_directory(self):
        # relative path to local path
        if self._base_directory:
            return self._base_directory

        return ''


    def rewrite_without_base_directory(self, outfile):
        new_root = lxml.etree.Element('test')

        # preserve our root
        doc_copy = copy.deepcopy(self._rootelem)

        for elem in doc_copy:
            new_root.append(elem)

        with open(outfile, 'w') as outf:
            outf.write(lxml.etree.tostring(new_root, pretty_print=True).decode())


    def rewrite_without_overlays_and_templates(self, outfile):
        new_root = lxml.etree.Element('test')

        # preserve our root
        doc_copy = copy.deepcopy(self._rootelem)

        remove_tags = ('overlays', 'templates')

        for elem in doc_copy:
            if elem.tag in remove_tags:
                continue

            new_root.append(elem)

        with open(outfile, 'w') as outf:
            outf.write(lxml.etree.tostring(new_root, pretty_print=True).decode())


    def _parsefile(self, testfile):
        rootelem = self.parse(testfile)

        self._base_directory = rootelem.attrib.get('base', None)

        self._name = rootelem.findall('./name')[0].text

        self._tags = {}

        tagelems = rootelem.findall('./tags/tag')
        if len(tagelems):
            for tagelem in tagelems[0]:
                self._tags[tagelem.attrib['name']] = tagelem.attrib['value']

        self._description = rootelem.findall('./description')[0].text

        self._global_overlays = {}

        for oelem in rootelem.findall("./overlays/overlay"):
            #<overlay name='FREQ1' value='2347000000'/>
            name = oelem.attrib['name']

            val = oelem.attrib['value']

            argtype = oelem.attrib.get('type', None)

            self._global_overlays[name] = etce.utils.configstrtoval(val, argtype=argtype)

        self._global_overlay_csvfiles = []

        for oelem in rootelem.findall("./overlays/overlaycsv"):
            #<overlaycsv file='FREQ1' column='2347000000'/>
            self._global_overlay_csvfile.append((oelem.attrib['file'], oelem.attrib['column']))

        self._indices,                  \
        self._reserved_overlays,        \
        self._templates,                \
        self._template_directory_names, \
        self._formatted_directory_names = self._parse_templates(rootelem)

        return rootelem


    def _parse_templates(self, rootelem):
        all_indices = []

        reserved_overlays = {}

        templates = []

        template_directory_names = set([])

        formatted_dir_names = set([])

        for templateselem in rootelem.findall('./templates'):
            all_indices = etce.utils.nodestr_to_nodelist(templateselem.get('indices'))

            all_indices_set = set(all_indices)

            templates_global_overlaylists = \
                OverlayListChainFactory().make(templateselem.findall("./overlaylist"),
                                               all_indices)

            reserved_overlays['etce_indices'] = ','.join(map(str, sorted(all_indices_set)))

            # On first pass:
            #  1. Check individual file or directory indices are a proper subset of the
            #     templates indices (all_indices).
            #  2. Build up reserved_overlays with reserved indices sets. etce_indices
            #     contains all_indices. For each file or directory, etce_NAME_indices
            #     contains the indices just allocated to that template, where NAME
            #     is the template name with any '.' chars converted to '_'.
            #     The values for each of these overlays is a string that is the comma
            #     separated list of indices. The idea is to make these value accessible
            #     for loop variable in template files.
            #
            for elem in list(templateselem):
                # ignore comments
                if isinstance(elem, lxml.etree._Comment):
                    continue

                template_indices = all_indices

                template_name = elem.attrib.get('name')

                template_indices_str = elem.attrib.get('indices')

                if template_indices_str:
                    template_indices = etce.utils.nodestr_to_nodelist(template_indices_str)

                if not set(template_indices).issubset(all_indices_set):
                    message = 'indices for template element "%s" are not ' \
                              'a subset of parent templatefiles indices. ' \
                              'Quitting.' % elem.attrib['name']
                    raise RuntimeError(message)

                reserved_overlay_name = 'etce_%s_indices' % template_name.replace('.', '_')

                reserved_overlays[reserved_overlay_name] = ','.join(map(str, sorted(template_indices)))

            # for second pass, make templates
            for elem in list(templateselem):
                # ignore comments
                if isinstance(elem, lxml.etree._Comment):
                    continue

                template_indices = all_indices

                template_name = elem.attrib.get('name')

                template_indices_str = elem.attrib.get('indices')

                if template_indices_str:
                    template_indices = etce.utils.nodestr_to_nodelist(template_indices_str)

                if elem.tag == 'directory':
                    tdbconfig = TemplateDirectoryBuilderConfig(elem, template_indices)

                    templates.append(TemplateDirectoryBuilder(tdbconfig,
                                                              copy.copy(reserved_overlays),
                                                              self._global_overlays,
                                                              templates_global_overlaylists))
                elif elem.tag == 'file':
                    tfbconfig = TemplateFileBuilderConfig(elem, template_indices)

                    templates.append(TemplateFileBuilder(tfbconfig,
                                                         copy.copy(reserved_overlays),
                                                         self._global_overlays,
                                                         templates_global_overlaylists))

        for t in templates:
            formatted_dir_names.update(t.formatted_hostnames)

            if isinstance(t, TemplateDirectoryBuilder):
                template_directory_names.update([t.template_directory_name])

        return (all_indices,
                reserved_overlays,
                templates,
                frozenset(template_directory_names),
                frozenset(formatted_dir_names))
