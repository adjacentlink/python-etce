#
# Copyright (c) 2013-2018 - Adjacent Link LLC, Bridgewater, New Jersey
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
import ConfigParser


def getconfig():
    return ConfigDictionary().asdict()


class ConfigDictionary(object):
    def __init__(self,
                 configfilename='etce',
                 defaults = {
                     'etce': {
                         'VERBOSE':'off',
                         'DEFAULT_ETCE_HOSTNAME_FORMAT':"node-${'%03d' % etce_index}",
                         'TEMPLATE_DIRECTORY_SUFFIX':'tpl',
                         'WORK_DIRECTORY':'/tmp/etce',
                         'WRAPPER_DIRECTORY':'/opt/etce/wrappers',
                         'LOCK_FILE_DIRECTORY':'/run/lock',
                         'ENV_OVERLAYS_ALLOW':''
                     },
                     'overlays': {
                     },
                 }):
        self.parser = ConfigParser.ConfigParser()
        self.parser.optionxform = str # leave case

        config_dir = os.getenv('ETCECONFIGDIR','/etc/etce')

        configfiles = [os.path.join(config_dir,'%s.conf' % configfilename),
                       os.path.join(os.path.expanduser('~'), '.%s.conf' % configfilename) ]

        
        # read function should not cause error if any of the named files
        # don't exist. Duplicate values are overlayed by values found
        # later in the list.
        self.parser.read(configfiles)

        if self.parser.has_option('etce', 'WORK_DIRECTORY'):
            user_specified_workdir = self.parser.get('etce', 'WORK_DIRECTORY')

            # enforce that user specified WORK_DIRECTORY is an absolute path
            if not user_specified_workdir[0] == '/':
                error = 'User configured WORK_DIRECTORY "%s" is not an ' \
                        'absolue path. Quitting.' % user_specified_workdir
                raise ValueError(error)
                
            # and at least 2 levels deep
            if len(user_specified_workdir.split('/')) < 3:
                error = 'User configured WORK_DIRECTORY "%s" must be ' \
                        '2 or more levels deep. Quitting.' % user_specified_workdir
                raise ValueError(error)

            allowed_roots = ('tmp', 'opt', 'home', 'var', 'mnt')
            if not user_specified_workdir.split('/')[1] in allowed_roots:
                error = 'User configured WORK_DIRECTORY "%s" is not located in one of {%s} ' \
                        'directory trees. Quitting.' % \
                        (user_specified_workdir, ', '.join(allowed_roots))
                raise ValueError(error)


        for section, namevals in defaults.items():
            if not self.parser.has_section(section):
                self.parser.add_section(section)
            for name,val in namevals.items():
                if not self.parser.has_option(section, name):
                    self.parser.set(section, name, val)

        # allow for environment override of the two path variables
        if 'WRAPPER_DIRECTORY' in os.environ:
            self.parser.set('etce', 'WRAPPER_DIRECTORY', os.environ['WRAPPER_DIRECTORY'])

    def get(self, section, key, default=None):
        if self.parser.has_option(section, key):
            return self.parser.get(section, key)
        return default

    
    def sections(self):
        return self.parser.sections()


    def items(self, section):
        return self.parser.items(section)

    
    def asdict(self):
        retdict = {}
        for section in self.sections():
            retdict[section] = {}
            for n,v in sorted(self.parser.items(section)):
                retdict[section][n] = v
        return retdict


    def __str__(self):
        retstr = ''
        for section in self.parser.sections():
            retstr += '\n[ ' + section + ' ]\n'
            pairs = [ name + ':' + str(value) \
                          for name,value in sorted(self.parser.items(section)) ]
            retstr += '\n'.join(pairs)
            retstr += '\n'
        return retstr
