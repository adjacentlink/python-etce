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
import os.path

from etce.config import ConfigDictionary
from etce.templateutils import format_file
from etce.utils import nodestrtonodes
from etce.overlaylistchainfactory import OverlayListChainFactory


class TemplateFile(object):
    def __init__(self, 
                 srcdir,
                 trialdir,
                 templatefileelem,
                 parentindices,
                 nodeoverlaydict, 
                 overlaydict):

        self._trialdir = trialdir
        
        self._nodeoverlaydict = nodeoverlaydict
        
        self._overlaydict = overlaydict
        
        self._name = templatefileelem.attrib['name']

        templatefilenameabs = os.path.join(srcdir, self._name)
        
        if not os.path.exists(templatefilenameabs) or \
                not os.path.isfile(templatefilenameabs):
            raise ValueError('ERROR: %s templatefile does not exist' 
                             % templatefilenameabs)
        self._absname = templatefilenameabs

        self._hostname_format, \
        self._output_file_name = self._read_attributes(templatefileelem)

        localindicesstr = templatefileelem.attrib.get('indices', None)

        self._indices = parentindices

        if not localindicesstr is None:
            self._indices = nodestrtonodes(localindicesstr)

            if not set(self._indices).issubset(set(parentindices)):
                raise ValueError('ERROR: templatefile "%s" indices value "%s" '
                                 'is not a proper subset of the parent '
                                 'indices set' % (self._name, indicesstr))


        # build local overlay chain
        localoverlaylistelems = templatefileelem.findall('./overlaylist')
        self._localnodeoverlaydict = \
            OverlayListChainFactory().make(localoverlaylistelems,
                                           self._indices)


    def name(self):
        return self._name


    def instantiate(self, publishdir):
        for index in self._indices:
            # assemble the format dictionary from the various overlays
            # most local value takes precedent
            nodeoverlays = copy.copy(self._overlaydict)
            
            for n,v in self._nodeoverlaydict[index].items():
                nodeoverlays[n] = v
                
            for n,v in self._localnodeoverlaydict[index].items():
                nodeoverlays[n] = v
                
            nodeoverlays['etce_index'] = index
            
            nodeoverlays['etce_hostname'] = self._hostname_format % nodeoverlays['etce_index']

            if self._trialdir:
                nodeoverlays['etce_log_path'] = \
                    os.path.join(self._trialdir, nodeoverlays['etce_hostname'])

            self._createfile(publishdir, nodeoverlays)


    def _createfile(self, publishdir, nodeoverlays):
        publishfile = os.path.join(publishdir, 
                                   nodeoverlays['etce_hostname'], 
                                   self._output_file_name)

        # format str can add subdirectories, so make those if necessary
        if not os.path.exists(os.path.dirname(publishfile)):
            os.makedirs(os.path.dirname(publishfile))

        if os.path.exists(publishfile):
            print 'Warning: %s already exists. Overwriting!' % publishfile

        format_file(self._absname, publishfile, nodeoverlays)


    def _read_attributes(self, templatefileelem):
        hostname_format = \
            templatefileelem.attrib.get('hostname_format', 
                                        ConfigDictionary().get('etce', 'DEFAULT_ETCE_HOSTNAME_FORMAT'))

        outputfilename = \
            templatefileelem.attrib.get('output_file_name', 
                                        templatefileelem.attrib['name'])

        return (hostname_format, outputfilename)


    def __str__(self):
        retstr = 'TemplateFile\n'
        retstr += self._name + '\n'
        retstr += ' '.join(map(str, self._indices))
        return retstr

