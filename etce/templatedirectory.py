#
# Copyright (c) 2016-2017 - Adjacent Link LLC, Bridgewater, New Jersey
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

from etce.utils import nodestrtonodes
from etce.templateutils import format_file
from etce.config import ConfigDictionary
from etce.overlaylistchainfactory import OverlayListChainFactory


class TemplateDirectory(object):
    def __init__(self, 
                 srcdir,
                 trialdir,
                 templatedirelem, 
                 parentindices,
                 nodeoverlaydict, 
                 overlaydict):

        self._trialdir = trialdir
        
        self._nodeoverlaydict = nodeoverlaydict
        
        self._overlaydict = overlaydict

        self._name = templatedirelem.attrib['name']

        self._template_subdir, \
        self._hostname_format = self._read_attributes(templatedirelem)

        templatedirnameabs = os.path.join(srcdir, self._template_subdir)
        
        if not os.path.exists(templatedirnameabs) or \
                not os.path.isdir(templatedirnameabs):
            raise ValueError('ERROR: %s templatedir does not exist' 
                             % templatedirnameabs)
        self._absname = templatedirnameabs

        localindicesstr = templatedirelem.attrib.get('indices', None)

        self._indices = parentindices

        if not localindicesstr is None:
            self._indices = nodestrtonodes(localindicesstr)

            if not set(self._indices).issubset(set(parentindices)):
                raise ValueError('ERROR: templatefile "%s" indices value "%s" '
                                 'is not a proper subset of the parent '
                                 'indices set' % (self._name, indicesstr))

        # build local overlay chain
        localoverlaylistelems = templatedirelem.findall('./overlaylist')
        self._localnodeoverlaydict = \
            OverlayListChainFactory().make(localoverlaylistelems,
                                           self._indices)


    @property
    def name(self):
        return self._name


    @property
    def template_subdir(self):
        return self._template_subdir

    
    @property
    def absname(self):
        return self._absname


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
                nodeoverlays['etce_log_path'] = os.path.join(self._trialdir,
                                                             nodeoverlays['etce_hostname'])
            
            node_publishdir = os.path.join(publishdir, nodeoverlays['etce_hostname'])

            print 'Processing template directory "%s" for index=%d and destination=%s' % \
                (self._absname, index, node_publishdir)

            self._createdir(node_publishdir, nodeoverlays)


    def _createdir(self, node_publishdir, nodeoverlays):
        if not os.path.exists(node_publishdir):
            os.makedirs(node_publishdir)
        # To publish a directory:
        # 1. walk the directory (and each of its subdirectories)
        # 2. for each file found, fill in its template variables
        #    and save to the publish directory with the same
        #    relative path and filename.
        for absdirname,subdirnames,filenames in os.walk(self._absname):
            dirname = ''

            if absdirname != self._absname:
                dirname = absdirname.replace(self._absname+'/', '')

            for subdirname in subdirnames:
                abssubdir = os.path.join(node_publishdir,dirname,subdirname)
                os.makedirs(abssubdir)

            for filename in filenames:
                srcfile = os.path.join(absdirname,filename)

                dstfile = os.path.join(node_publishdir,dirname,filename)

                format_file(srcfile, dstfile, nodeoverlays)


    def _read_attributes(self, templatedirelem):
        template_subdir = '.'.join([self._name,
                                    ConfigDictionary().get('etce', 'TEMPLATE_SUFFIX')])

        default_hostname_format = ConfigDictionary().get('etce', 'DEFAULT_ETCE_HOSTNAME_FORMAT')

        hostname_format = templatedirelem.attrib.get('hostname_format', default_hostname_format)

        return (template_subdir, hostname_format)


    def __str__(self):
        retstr = 'TemplateDir\n'
        retstr += self._name + '\n'
        retstr += ' '.join(map(str, self._indices))
        return retstr

