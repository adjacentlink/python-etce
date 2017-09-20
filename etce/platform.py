#
# Copyright (c) 2013-2017 - Adjacent Link LLC, Bridgewater, New Jersey
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

from __future__ import absolute_import
import signal
import platform
import etce.loader


def platform_suffix():
    return platform_suffix_list()[0]


def platform_suffix_list():
    suffixes = []
    os = platform.uname()[0].strip().lower()
    arch = platform_architecture()

    if os == 'linux':
        distname = linux_distribution()
        if distname == 'amzn1':
            suffixes.append('%s.%s.%s' % (os,distname,arch))
            suffixes.append('%s.%s' % (os,distname))
            suffixes.append('%s' % os)
        else:
            # insure no '.' in distver (ubuntu does this, for one)
            distver = platform.dist()[1].lower().replace('.','_')
            suffixes.append('%s.%s.v%s.%s' % (os,distname,distver,arch))
            suffixes.append('%s.%s.v%s' % (os,distname,distver))
            suffixes.append('%s.%s' % (os,distname))
            suffixes.append('%s' % os)

    elif os == 'windows':
        osversion = platform.release().lower()        
        suffixes.append('%s.%s.%s' % (os,osversion,arch))
        suffixes.append('%s.%s' % (os,osversion))
        suffixes.append('%s' % os)

    return suffixes


def linux_distribution():
    dist = platform.dist()[0].lower()
    if len(dist) > 0:
        return dist
    if 'amzn1' in platform.uname()[2]:
        return 'amzn1'
    return 'unknown'


def platform_architecture():
    # standardize the arch string across os's - use linux naming convention
    buswidth = platform.architecture()[0].lower()        
    arch = 'i686'
    if buswidth == '64bit':
        arch = 'x86_64'
    return arch


class Platform:
    def __init__(self):
        module = etce.loader.load_etce_module('platformimpl')
        self._impl = etce.loader.load_class_instance_from_module(module)

    def getnetworkdevicenames(self):
        return self._impl.getnetworkdevicenames()

    def adddeviceaddress(self, interface, address):
        self._impl.adddeviceaddress(interface, address)

    def removedeviceaddress(self, interface, address):
        self._impl.removedeviceaddress(interface, address)

    def isdeviceup(self, device):
        return self._impl.isdeviceup(device)

    def networkinterfaceup(self, interface):
        self._impl.networkinterfaceup(interface)

    def networkinterfacedown(self, interface):
        self._impl.networkinterfacedown(interface)

    def bridgeup(self, bridgename, addifs=[], enablemulticastsnooping=True):
        self._impl.bridgeup(bridgename, addifs, enablemulticastsnooping)

    def bridgedown(self, bridgename):
        self._impl.bridgedown(bridgename)

    def hostname(self):
        return self._impl.hostname()

    def hostname_has_local_address(self, hostname):
        return self._impl.hostname_has_local_address(hostname)

    def hostnames_has_local_address(self, hostnames):
        return self._impl.hostnames_has_local_address(hostnames)

    def hostid(self):
        return self._impl.hostid()

    def firewall(self, command):
        self._impl.firewall(command)

    def runcommand(self, commandstring):
        return self._impl.runcommand(commandstring)

    def set_igmp_version(self, version):
        self._impl.set_igmp_version(version)

    def set_date_now(self, utcdate):
        self._impl.set_date_now(utcdate)

    def get_date_now(self):
        return self._impl.get_date_now()
        
    def getallpids(self):
        return self._impl.getallpids()

    def getpids(self, commregex):
        return self._impl.getpids(commregex)

    def ps(self, psregex):
        self._impl.ps(psregex)

    def listdir(self, abspath, fileregex='.*'):
        return self._impl.listdir(abspath, fileregex)

    def rmfile(self, filename):
        self._impl.rmfile(filename)

    def checkandexpandpath(self, path_template):
        return self._impl.checkandexpandpath(path_template)

    def kill(self, pidfile, signal=signal.SIGQUIT):
        return self._impl.kill(pidfile, signal)

    def killall(self, applicationname, signal=signal.SIGQUIT):
        self._impl.killall(applicationname, signal)

    def rmdir(self, subdir):
        self._impl.rmdir(subdir)
