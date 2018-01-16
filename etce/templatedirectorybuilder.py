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

import copy
import os

from etce.utils import nodestr_to_nodelist
from etce.templateutils import format_file
from etce.chainmap import ChainMap
from etce.config import ConfigDictionary
from etce.overlaylistchainfactory import OverlayListChainFactory


class TemplateDirectoryBuilder(object):
    def __init__(self,
                 templatedirelem,
                 indices,
                 testfile_global_overlays,
                 templates_global_overlaylists):

        self._global_overlays = testfile_global_overlays

        self._templates_global_overlaylists = templates_global_overlaylists

        template_suffix = ConfigDictionary().get('etce', 'TEMPLATE_SUFFIX')
        
        self._name = templatedirelem.attrib['name']

        self._template_directory_name = '.'.join([self._name, template_suffix])
        
        self._indices = indices
        
        self._relative_path, \
        self._hostname_format = self._read_attributes(templatedirelem)

        # build local overlay chain
        self._template_local_overlays = {}

        for overlayelem in templatedirelem.findall('./overlay'):
            oname = overlayelem.attrib['name']

            oval = overlayelem.attrib['value']

            self._template_local_overlays[oname] = etce.utils.configstrtoval(oval)

        self._template_local_overlaylists = \
            OverlayListChainFactory().make(templatedirelem.findall('./overlaylist'),
                                           self._indices)


    @property
    def name(self):
        return self._name


    @property
    def template_directory_name(self):
        return self._template_directory_name
    
    @property
    def hostname_format(self):
        return self._hostname_format
    

    @property
    def indices(self):
        return self._indices

    
    def prune(self, filelist):
        '''
        remove template filenames that appear in the filelist
        '''
        rmfiles = []

        for subfile in filelist:
            if subfile.startswith(self._relative_path + '/'):
                rmfiles.append(subfile)

        for rmfile in rmfiles:
            filelist.pop(filelist.index(rmfile))

        return filelist


    def instantiate(self,
                    srcdir,
                    publishdir,
                    logdir,
                    runtime_overlays,
                    env_overlays,
                    etce_config_overlays):
        templatedir = os.path.join(srcdir, self._relative_path)

        if not os.path.exists(templatedir) or \
           not os.path.isdir(templatedir):
            raise ValueError('ERROR: %s templatedir does not exist' 
                             % template_dir)

        for index in self.indices:
            self._createdir(templatedir,
                            publishdir,
                            logdir,
                            index,
                            runtime_overlays,
                            env_overlays,
                            etce_config_overlays)


    def _createdir(self,
                   templatedir,
                   publishdir,
                   logdir,
                   index,
                   runtime_overlays,
                   env_overlays,
                   etce_config_overlays):
        # assemble the format dictionary from the various overlays
        # most local value takes precedent
        reserved_overlays = {}

        reserved_overlays['etce_index'] = index

        reserved_overlays['etce_hostname'] = \
            self._hostname_format % reserved_overlays['etce_index']

        if logdir:
            reserved_overlays['etce_log_path'] = \
                os.path.join(logdir, reserved_overlays['etce_hostname'])
            
        node_publishdir = os.path.join(publishdir, reserved_overlays['etce_hostname'])

        non_reserved_overlays = [ runtime_overlays,
                                  env_overlays,
                                  self._template_local_overlaylists[index],
                                  self._template_local_overlays,
                                  self._templates_global_overlaylists[index],
                                  self._global_overlays,
                                  etce_config_overlays ] 
        
        other_keys = set([])

        map(other_keys.update, non_reserved_overlays)

        key_clashes =  other_keys.intersection(set(reserved_overlays))

        if key_clashes:
            raise ValueError('Overlay keys {%s} are reserved. Quitting.' % \
                             ','.join(map(str,key_clashes)))

        overlays = ChainMap(reserved_overlays, *non_reserved_overlays)
        
        print 'Processing template directory "%s" for etce_index=%d and destination=%s' % \
            (templatedir, index, node_publishdir)

        if not os.path.exists(node_publishdir):
            os.makedirs(node_publishdir)


        # To publish a directory:
        # 1. walk the directory (and each of its subdirectories)
        # 2. for each file found, fill in its template variables
        #    and save to the publish directory with the same
        #    relative path and filename.
        for absdirname,subdirnames,filenames in os.walk(templatedir):
            dirname = ''

            if absdirname != templatedir:
                dirname = absdirname.replace(templatedir+'/', '')

            for subdirname in subdirnames:
                abssubdir = os.path.join(node_publishdir,dirname,subdirname)
                os.makedirs(abssubdir)

            for filename in filenames:
                srcfile = os.path.join(absdirname,filename)

                dstfile = os.path.join(node_publishdir,dirname,filename)

                format_file(srcfile, dstfile, overlays)


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

