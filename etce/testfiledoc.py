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

import copy
import os
import sets

import lxml.etree

import etce.xmldoc
import etce.utils
from etce.templatedirectorybuilder import TemplateDirectoryBuilder
from etce.templatefilebuilder import TemplateFileBuilder
from etce.overlaycsvreader import OverlayCSVReader
from etce.overlaylistchainfactory import OverlayListChainFactory


class TestFileDoc(etce.xmldoc.XMLDoc):
    def __init__(self, testfile):
        etce.xmldoc.XMLDoc.__init__(self,
                                    'testfile.xsd')

        if not os.path.exists(testfile) or not os.path.isfile(testfile):
            raise ValueError('Cannot find test file "%s". Quitting.' %
                             testfile)

        self._parsefile(testfile)


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


    def global_overlays(self, mergedir):
        global_overlays = copy.copy(self._global_overlays)
        
        for csvfile,column in self._global_overlay_csvfiles:
            csvfileabs = os.path.join(mergedir,csvfile)
            
            global_overlays.update(OverlayCSVReader,csvfileabs).values(column)

        return global_overlays


    def templates(self):
        return self._templates

    
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
        new_root = lxml.etree.Element('test')

        # preserve our root
        doc_copy = copy.deepcopy(self._rootelem)
        
        for elem in doc_copy:
            new_root.append(elem)

        with open(outfile, 'w') as outf:
            outf.write(lxml.etree.tostring(new_root, pretty_print=True))


    def _parsefile(self, testfile):
        self._rootelem = self.parse(testfile)

        self._basedir = self._rootelem.attrib.get('base', None)

        self._name = self.findall('./name')[0].text

        self._tags = {}

        tagelems = self.findall('./tags/tag')
        if len(tagelems):
            for tagelem in tagelems[0]:
                self._tags[tagelem.attrib['name']] = tagelem.attrib['value']

        self._description = self.findall('./description')[0].text

        self._global_overlays = {}
        
        for oelem in self._rootelem.findall("./overlays/overlay"):
            #<overlay name='FREQ1' value='2347000000'/>
            name = oelem.attrib['name']
            val = oelem.attrib['value']
            self._global_overlays[name] = etce.utils.configstrtoval(val)

        self._global_overlay_csvfiles = []

        for oelem in self._rootelem.findall("./overlays/overlaycsv"):
            #<overlaycsv file='FREQ1' column='2347000000'/>
            self._global_overlay_csvfile.append((oelem.attrib['file'], oelem.attrib['column']))

        self._indices,                  \
        self._templates,                \
        self._template_directory_names, \
        self._formatted_directory_names = self._parse_templates(self._rootelem)


    def _parse_templates(self, rootelem):
        indices = []

        templates = []

        template_directory_names = set([])

        formatted_dir_names = set([])

        for templateselem in rootelem.findall('./templates'):
            indices = etce.utils.nodestr_to_nodelist(templateselem.get('indices'))

            indices_set = set(indices)
            
            templates_global_overlaylists = \
                OverlayListChainFactory().make(templateselem.findall("./overlaylist"),
                                               indices)

            for elem in list(templateselem):
                # ignore comments
                if isinstance(elem, lxml.etree._Comment):
                    continue

                template_indices = indices

                template_indices_str = elem.attrib.get('indices')

                if template_indices_str:
                    template_indices =  etce.utils.nodestr_to_nodelist(template_indices_str)

                if not set(template_indices).issubset(indices_set):
                    message = 'indices for template element "%s" are not ' \
                              'a subset of parent templatefiles indices. ' \
                              'Quitting.' % elem.attrib['name']
                    raise RuntimeError(message)

                if elem.tag == 'directory':
                    templates.append(TemplateDirectoryBuilder(elem, 
                                                              template_indices,
                                                              self._global_overlays,
                                                              templates_global_overlaylists))
                elif elem.tag == 'file':
                    templates.append(TemplateFileBuilder(elem, 
                                                         template_indices,
                                                         self._global_overlays,
                                                         templates_global_overlaylists))

        for t in templates:
            for index in t.indices:
                formatted_dir_names.update([t.hostname_format % index ])

            if isinstance(t, TemplateDirectoryBuilder):
                template_directory_names.update([t.template_directory_name])

        return (indices,
                templates,
                sets.ImmutableSet(template_directory_names),
                sets.ImmutableSet(formatted_dir_names))
