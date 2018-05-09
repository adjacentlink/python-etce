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

import datetime
import os
import re
import shlex
import signal
import socket
import subprocess
import sys

import etce.platformimpl
import etce.utils
from etce.apprunner import AppRunner


class PlatformImpl(etce.platformimpl.PlatformImpl):
    def hostname_has_local_address(self, hostname):
        return self.hostnames_has_local_address([hostname])


    def hostnames_has_local_address(self, hostnames):
        localips = []
        try:
            localips = self._get_local_ip_addresses()
        except:
            return False

        for hn in hostnames:
            try:
                if socket.gethostbyname(hn) in localips:
                    return True
            except:
                pass # keep trying
        return False
            

    def getnetworkdevicenames(self):
        runner = AppRunner('ip link show')

        devices = []

        devmatcher = re.compile(r'^\d+: (\w+):')

        for line in runner.stdout():
            match = devmatcher.match(line)

            if match:
                devices.append(match.group(1))

        return devices


    def adddeviceaddress(self, interface, address):
        if not os.system('ip addr add %s dev %s' % (address, interface)) == 0:
            raise RuntimeError('Failed to assign %s to %s network interface' % \
                                    (address, interface))


    def removedeviceaddress(self, interface, address):
        if not os.system('ip addr del %s dev %s' % (address, interface)) == 0:
            raise RuntimeError('Failed to remove %s from %s network interface' % \
                                    (address, interface))


    def isdeviceup(self, device):
        #10: br1:  <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP mode DEFAULT group default
        devicematcher = re.compile(r'\d+: %s(?:@\w+)?: <(.*)>' % device)

        command = 'ip link show %s' % device

        e = AppRunner(command)

        for line in e.stdout():
            match =  devicematcher.match(line)
            if match:
                attributes = match.group(1).split(',')
                return 'UP' in attributes

        return False


    def networkinterfaceup(self, interface):
        if not os.system('ip link set %s up' % interface) == 0:
            raise RuntimeError('Failed to up %s network interface' % \
                                    interface)
        while os.system('ifconfig %s > /dev/null' % interface) != 0:
            time.sleep(1)


    def networkinterfacedown(self, interface):
        if not os.system('ip link set %s down' % interface) == 0:
            raise RuntimeError('Failed to down %s network interface' % \
                                    interface)

    def bridgeup(self, bridgename, addifs, enablemulticastsnooping):
        self.runcommand('brctl addbr %s' % bridgename)
       
        self.networkinterfaceup(bridgename)

        self.runcommand('iptables -I INPUT -i %s -j ACCEPT' % bridgename )

        self.runcommand('iptables -I FORWARD -i %s -j ACCEPT' % bridgename)

        for interface in addifs:
            self.runcommand('brctl addif %s %s' % (bridgename, interface))

            self.runcommand('ip link set %s up' % interface)
            
        if enablemulticastsnooping:
            with open('/sys/devices/virtual/net/%s/bridge/multicast_snooping' % bridgename, 'w') as sf:
                sf.write('0')


    def bridgedown(self, bridgename):
        self.runcommand('iptables -D FORWARD -i %s -j ACCEPT' % bridgename)

        self.runcommand('iptables -D INPUT -i %s -j ACCEPT' % bridgename)

        self.networkinterfacedown(bridgename)

        self.runcommand('brctl delbr %s' % bridgename)


    def set_igmp_version(self, version):
        commandfmt = 'sysctl -w net.ipv4.conf.all.force_igmp_version=%s > /dev/null'

        os.system(commandfmt % str(version))


    def set_date_now(self, utcdate):
        os.system('date -s "%s"' % utcdate)


    def get_date_now(self):
        return '%s' % datetime.datetime.now()


    def getallpids(self):
        pids = []

        runner = AppRunner('ps --no-headers -eo pid,command')

        for line in runner.stdout():
            toks = line.strip().split()

            pids.append( (int(toks[0]), toks[1]) )

        return pids


    def getpids(self, command):
        allpids = self.getallpids()

        pids = []

        for pidtpl in allpids:
            if pidtpl[1] == command:
                pids.append(pidtpl[0])

        return pids
                            

    def ps(self, psregex):
        psmatcher = re.compile(psregex)

        runner = AppRunner('ps -eo args')

        for line in runner.stdout():
            if psmatcher.match(line):
                print line.strip()


    def listdir(self, abspath, fileregex='.*'):
        '''
        return the file names in abspath that match the fileregex.
        '''
        if not os.path.exists(abspath) or not os.path.isdir(abspath):
            return []

        # find all files matching regex
        matcher = re.compile(fileregex)

        allmatches = [ f for f in os.listdir(abspath) if matcher.match(f) ]

        # if regex was just a simple file name, only return it
        exactmatches = [ f for f in allmatches if f == fileregex ]

        if len(exactmatches) > 0:
            return exactmatches

        # otherwise, return allmatches
        return allmatches


    def readpid(self, pidfile):
        pid = None
        if os.path.exists(pidfile):
            if os.path.isfile(pidfile):
                try:
                    pid = int(open(pidfile).readline())
                except ValueError as e:
                    print >>sys.stderr,type(e)
                    print >>sys.stderr,'Pidfile "%s" does not contain a valid PID. Skipping.' % \
                        pidfile
                    os.remove(pidfile)
                    pid = None
            else:
                # error - pidfile is not a regular fle
                error = 'Pidfile "%s" exists but is not a regular file. ' \
                        'Quitting.' % pidfile
                raise RuntimeError(error)
        return pid


    def kill(self, pidfile, signal, sudo):
        pid = self.readpid(pidfile)

        # if found a pid, kill the process and remove the file
        if pid:
            print 'killing pid %d found in %s' % (pid, pidfile)
            commandstr = 'kill -%d %d' % (signal, pid)
            if sudo:
                commandstr = 'sudo ' + commandstr

            try:
                sp = subprocess.Popen(shlex.split(commandstr))
                sp.wait()
            finally:
                os.remove(pidfile)

        return pid


    def killall(self, applicationname, signal, sudo):
        try:
            command = \
                "kill -%d $(ps -eo pid,command | " \
                "awk '/%s[%s] /{print $1}') > /dev/null 2>&1" \
                % (signal, applicationname[:-1],applicationname[-1])

            if sudo:
                command = 'sudo ' + command
            
            os.system(command)

        except:
            print 'problem in killing %s' % applicationname


    def _get_local_ip_addresses(self):
        ipaddrs = []

        matcher = re.compile(r'inet (\d+.\d+.\d+.\d+)/\d+')

        runner = AppRunner('ip addr show')

        lines = [ line.strip() for line in runner.stdout() ]

        for line in lines:
            match = matcher.match(line)

            if match:
                ipaddrs.append(match.group(1))

        return ipaddrs


