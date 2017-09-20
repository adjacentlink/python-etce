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

import ConfigParser


class NetPlanFile(object):
    def __init__(self, netplanfile):
        self.parser = ConfigParser.SafeConfigParser()
        self.parser.read([ netplanfile ])
        self._utsnamemap = self._parseuts()


    def get(self, key, default=None):
        if self.parser.has_option('netplan', key):
            return self.parser.get('netplan', key)
        return default


    def getutsname(self, nodeid, default=None):
        return self._utsnamemap.get(nodeid, default)


    def __str__(self):
        s = '[netplan]\n'
        for k,v in self.parser.items('netplan'):
            s += '%s=%s\n' % (k,v)
        return s


    def _parseuts(self):
        utsnamemap = {}
        utsnames = self.get('utsnames')
        if utsnames:
            for pair in utsnames.split('|'):
                nodeidstr,utsname = pair.split(':')
                utsnamemap[int(nodeidstr)] = utsname.strip()
        return utsnamemap
