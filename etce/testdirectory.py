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

import os
import re
import shutil 

from etce.config import ConfigDictionary
from etce.configfiledoc import ConfigFileDoc
from etce.field import Field
from etce.manifestfiledoc import ManifestFileDoc
from etce.platform import Platform
from etce.templateutils import get_file_overlays
from etce.testdirectoryerror import TestDirectoryError
import etce.utils


class TestDirectory(object):
    MANIFESTFILENAME = 'manifest.xml'
    STEPSFILENAME = 'steps.xml'
    CONFIGFILENAME = 'config.xml'
    HOSTFILENAME = 'nodefile.txt'
    DOCSUBDIRNAME = 'doc'

    def __init__(self, rootdir, basedir_override):
        
        self._rootdir = rootdir
        
        self._platform = Platform()

        self._manifestfile = ManifestFileDoc(
            os.path.join(self._rootdir,
                         TestDirectory.MANIFESTFILENAME))

        self._merged = not self._manifestfile.has_base_directory()
        
        self._basedir = self._manifestfile.base_directory()

        if not basedir_override is None:
            self._basedir = basedir_override

        self._configfile = ConfigFileDoc(
            os.path.join(self._rootdir,
                         TestDirectory.CONFIGFILENAME))

        # a hostfile gets added into the test directory
        # when moved to remote host.
        hostfile = os.path.join(self._rootdir, 
                                TestDirectory.HOSTFILENAME)

        # set of verified nodes is empty if the hostfile doesn't
        self._verified_nodes = []
        if os.path.exists(hostfile) or os.path.isfile(hostfile):
            self._verified_nodes = self._verify_nodes_in_hostfile(hostfile)


    def hasconfig(self, wrappername, argname):
        return self._configfile.hasconfig(wrappername, argname)


    def getconfig(self, wrappername, argname, default):
        return self._configfile.getconfig(wrappername, argname, default)


    def location(self):
        return self._rootdir

    
    def info(self):
        return { 'name':self.name(),
                 'description':self.description() }


    def name(self):
        return self._manifestfile.name()


    def tags(self):
        return self._manifestfile.tags()


    def description(self):
        return self._manifestfile.description()

    
    def overlay_names(self):
        return self._find_overlay_names()


    def stepsfile(self):
        return TestDirectory.STEPSFILENAME


    def __str__(self):
        info = self.info()
        s = '-' * len(info['name']) + '\n'
        s += info['name'] + '\n'
        s += '-' * len(info['name']) + '\n'
        s += 'location:\n\t%s\n' % self._rootdir
        s += 'description:\n\t%s\n' % info['description']
        s += 'overlays:\n'
        for p in self.overlay_names():
            s += '\t%s\n' % p
        return s


    def determine_nodenames(self):
        # Determine the nodenames defined by the test files and templates by
        #
        # 1. read the base directory and test directory aqnd take any
        #    subdiretory that does not end with .TEMPLATE_SUFFIX to
        #    be a nodename
        #
        # 2. add all of the directory names that will be generated
        #    by template directories
        #
        # 3. remove the doc subdirectory (the doc subdirectory is ignored,
        #                                 a place for additional test
        #                                 documentation).
        #
        template_suffix = ConfigDictionary().get('etce', 'TEMPLATE_SUFFIX')

        hostnames = set([])

        # if this is already a merged test directory, ignore base directory
        # search 
        if not self._merged:
            for entry in os.listdir(os.path.join(self.location(), self._basedir)):
                abs_entry = os.path.join(self.location(), self._basedir, entry)

                if os.path.isdir(abs_entry):
                    if entry.split('.')[-1] == template_suffix:
                        continue
                    hostnames.update([entry])

        for entry in os.listdir(self.location()):
            abs_entry = os.path.join(self.location(), entry)

            if os.path.isdir(abs_entry):
                if entry.split('.')[-1] == template_suffix:
                    continue
                hostnames.update([entry])

        formatted_dirnames = self._manifestfile.formatted_directory_names()

        hostnames.update(formatted_dirnames)

        # and the doc directory
        hostnames.difference_update([TestDirectory.DOCSUBDIRNAME])

        return list(hostnames)


    def _verify_nodes_in_hostfile(self, hostfile):
        field = Field(hostfile)

        hostnames = field.leaves()

        nodenames = self.determine_nodenames()

        for nodename in nodenames:
            if not nodename in hostnames:
                errstr = 'Hostname "%s" required by test, but not ' \
                         'found in nodefile "%s". Quitting.' \
                         % (nodename, nodefile)
                raise TestDirectoryError(errstr)
                
        return nodenames


    def nodename_from_hostname(self, hostname):
        if hostname in self._verified_nodes:
            return hostname

        samehosts = self._find_this_host_names(self._verified_nodes)

        if len(samehosts) == 1:
            return samehosts[0]

        return None


    def nodename(self):
        return self.nodename_from_hostname(self._platform.hostname())


    def nodeid(self):
        nodename = self.nodename()

        if not nodename:
            return None

        regex = re.compile(r'(\d+)')

        match = regex.search(nodename)

        if match:
            return int(match.group(1))
        return None


    def getfile(self, name):
        for entry in os.listdir(os.path.join(self._rootdir, self.nodename())):
            if entry == name:
                if os.path.isfile(entry):
                    return os.path.join(self._rootdir, self.nodename(), entry)
                    
        return None


    def _find_this_host_names(self, namelist):
        ''' Determine which names in namelist map to an 
            ip address on this host.
        '''
        return [ other for other in namelist 
                 if self._platform.hostname_has_local_address(other) ]


    def _find_overlay_names(self):
        overlays = set([])

        search_dirs = [self._basedir]

        if not self._merged:
            # push the basedirectory if this directory is not already merged
            search_dirs.insert(0, 
                               os.path.join(self.location(), self._basedir))

        for search_dir in search_dirs:
            for dirname,dirnames,filenames in os.walk(search_dir):
                if TestDirectory.DOCSUBDIRNAME in dirname.split('/'):
                    # ignore doc sub directory
                    continue
                for filename in filenames:
                    overlays.update(
                        get_file_overlays(os.path.join(dirname,filename)))

        return tuple(sorted(overlays))
