#
# Copyright (c) 2013-2017,2019 - Adjacent Link LLC, Bridgewater, New Jersey
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

from __future__ import absolute_import, division, print_function
import os
import re
import socket
import shutil
import stat
import sys
import time
import etce.utils

from etce.platform import Platform
from etce.lxcplanfiledoc import LXCPlanFileDoc
from etce.lxcerror import LXCError


def startlxcs(lxcplan, writehosts=False, dryrun=False):
    lxcplanfiledoc = lxcplan

    if not type(lxcplan) == LXCPlanFileDoc:
        # assume file name
        lxcplanfiledoc = LXCPlanFileDoc(lxcplan)

    try:
        LXCManagerImpl().start(lxcplanfiledoc,
                               writehosts=writehosts,
                               dryrun=dryrun)
    except Exception as e:
        raise LXCError(e)


def stoplxcs(lxcplan):
    lxcplanfiledoc = lxcplan

    if not type(lxcplan) == LXCPlanFileDoc:
        # assume file name
        lxcplanfiledoc = LXCPlanFileDoc(lxcplan)

    try:
        LXCManagerImpl().stop(lxcplanfiledoc)
    except Exception as e:
        raise LXCError(e.message)



class LXCManagerImpl(object):
    def __init__(self):
        self._platform = Platform()


    def start(self, plandoc, writehosts, dryrun=False):
        hostname = socket.gethostname().split('.')[0]
        lxcrootdir = plandoc.lxc_root_directory(hostname)
        containers = plandoc.containers(hostname)

        if not containers:
            print('No containers assigned to "%s". Skipping.' % hostname)
            return

        if not lxcrootdir[0] == '/':
            print('root_directory "%s" for hostname "%s" is not an absolute path. ' \
                  'Quitting.' % \
                  (lxcrootdir, hostname))
            return

        directory_level = len(lxcrootdir.split('/')) - 1
        if not directory_level >= 3:
            print('root_directory "%s" for hostname "%s" is less than 3 levels deep. ' \
                  'Quitting.' % \
                  (lxcrootdir, hostname))
            return

        allowed_roots = ('tmp', 'opt', 'home', 'var', 'mnt')
        if not lxcrootdir.split('/')[1] in allowed_roots:
            print('root_directory "%s" for hostname "%s" is not located in one of {%s} ' \
                  'directory trees. Quitting.' % \
                  (lxcrootdir, hostname, ', '.join(allowed_roots)))
            return

        if lxcrootdir is None or len(containers) == 0:
            print('No containers assigned to host %s. Quitting.' % hostname)
            return

        # delete and remake the node root
        if os.path.exists(lxcrootdir):
            print('Removing contents of "%s" directory.' % lxcrootdir)

            for subentry in os.listdir(lxcrootdir):
                entry = os.path.join(lxcrootdir, subentry)
                if os.path.isfile(entry):
                    os.remove(entry)
                elif os.path.isdir(entry):
                    shutil.rmtree(entry)
        else:
            os.makedirs(lxcrootdir)

        # set kernelparameters
        kernelparameters = plandoc.kernelparameters(hostname)
        if len(kernelparameters) > 0:
            print('Setting kernel parameters:')

            for kernelparamname, kernelparamval in kernelparameters.items():
                os.system('sysctl %s=%s' % (kernelparamname, kernelparamval))

        self._check_reserved(containers)

        # write hosts file
        if not dryrun:
            if writehosts:
                self._writehosts(containers)

        # bring up bridge
        if not dryrun:
            for _, bridge in plandoc.bridges(hostname).items():
                if not bridge.persistent:
                    print('Bringing up bridge: %s' % bridge.devicename)

                    self._platform.bridgeup(bridge.devicename,
                                            bridge.addifs,
                                            enablemulticastsnooping=True)

                    if not bridge.ipv4 is None:
                        self._platform.adddeviceaddress(bridge.devicename,
                                                        bridge.ipv4)

                    if not bridge.ipv6 is None:
                        self._platform.adddeviceaddress(bridge.devicename,
                                                        bridge.ipv6)


                    time.sleep(0.1)

                elif not self._platform.isdeviceup(bridge.devicename):
                    raise RuntimeError('Bridge %s marked persistent is not up. Quitting.')

        # create container files
        for container in containers:
            lxc_directory = container.lxc_directory

            self._makedirs(lxc_directory)

            # make the config
            with open(os.path.join(lxc_directory, 'config'), 'w') as configf:
                configf.write(str(container))

            # make init script
            filename, initscripttext = container.initscript

            if initscripttext:
                scriptfile = os.path.join(lxc_directory, filename)

                with open(scriptfile, 'w') as sf:
                    sf.write(initscripttext)

                    os.chmod(scriptfile,
                             stat.S_IRWXU | stat.S_IRGRP | \
                             stat.S_IXGRP | stat.S_IROTH | \
                             stat.S_IXOTH)

        if dryrun:
            print('dryrun')
        else:
            self._startnodes(containers)


    def stop(self, plandoc):
        hostname = self._platform.hostname()

        noderoot = plandoc.lxc_root_directory(hostname)

        for container in plandoc.containers(hostname):
            command = 'lxc-stop -n %s -k &> /dev/null' % container.lxc_name
            print(command)
            os.system(command)

        for _, bridge in plandoc.bridges(hostname).items():
            if not bridge.persistent:
                print('Bringing down bridge: %s' % bridge.devicename)
                self._platform.bridgedown(bridge.devicename, bridge.addifs)

        os.remove(plandoc.planfile())


    def _makedirs(self, noderoot):
        os.makedirs(noderoot)

        vardir = os.path.join(noderoot, 'var')
        os.makedirs(vardir)
        os.makedirs(os.path.join(vardir, 'run'))
        os.makedirs(os.path.join(vardir, 'log'))
        os.makedirs(os.path.join(vardir, 'lib'))

        mntdir = os.path.join(noderoot, 'mnt')
        os.makedirs(mntdir)


    def _startnodes(self, containers):
        for container in containers:
            command = 'lxc-execute -f %s/config  ' \
                      '-n %s '                     \
                      '-o %s/log '                 \
                      '-- %s/init.sh '             \
                      '2> /dev/null &' %             \
                      (container.lxc_directory,
                       container.lxc_name,
                       container.lxc_directory,
                       container.lxc_directory)

            pid, sp = etce.utils.daemonize_command(command)

            if pid == 0:
                # child
                sp.wait()
                sys.exit(0)

            time.sleep(0.1)


    def _waitstart(self, nodecount, lxcroot):
        numstarted = 0
        for i in range(10):
            command = 'lxc-ls -1 --active'
            numstarted = len(self._platform.runcommand(command))
            print('Waiting for lxc containers: %d of %d are running.' % \
                  (numstarted, nodecount))

            if numstarted == nodecount:
                break

            time.sleep(1)

        print('Continuing with %d of %d running lxc containers.' % \
              (numstarted, nodecount))


    def _writehosts(self, containers):
        opentag = '#### Start auto-generated ETCE control mappings\n'
        closetag = '#### Stop auto-generated ETCE control mappings\n'
        etcehostlines = []
        searchstate = 0
        for line in open('/etc/hosts', 'r'):
            if searchstate == 0:
                if line.startswith(opentag):
                    searchstate = 1
                else:
                    etcehostlines.append(line)
            elif searchstate == 1:
                if line.startswith(closetag):
                    searchstate == 2
            else:
                etcehostlines.append(line)

        # strip off trailing white spaces lines at end of file
        etcehostlines.reverse()

        for i, line in enumerate(etcehostlines):
            if len(line.strip()) > 0:
                etcehostlines = etcehostlines[i:]
                break

        etcehostlines.reverse()

        entry_collisions = self._check_for_collisions(etcehostlines, containers)

        if entry_collisions:
            message = 'ERROR: Cannot write hosts file for hosts or ' \
                'addresses "%s", already present in /etc/hosts. Quitting.' \
                % ','.join(entry_collisions)

            raise LXCError(message)


        with open('/etc/hosts', 'w') as ofd:
            for line in etcehostlines:
                ofd.write(line)

            ofd.write('\n')

            ofd.write(opentag)

            # ipv4
            ipv4_entries = []

            for container in containers:
                for hostentry, hostaddr in container.hosts_entries_ipv4:
                    ipv4_entries.append((hostentry, hostaddr))

            for hostentry, hostaddr in sorted(ipv4_entries):
                ofd.write('%s %s\n' % (hostaddr, hostentry))

            #ipv6
            ipv6_entries = []

            for container in containers:
                for hostentry, hostaddr in container.hosts_entries_ipv6:
                    ipv6_entries.append((hostaddr, hostentry))

            for hostentry, hostaddr in sorted(ipv6_entries):
                ofd.write('%s %s\n' % (hostaddr, hostentry))

            ofd.write(closetag)


    def _check_for_collisions(self, etcehostlines, containers):
        """
        Make sure new addresses do not overwrite existing ones
        """
        ipv4re = re.compile(r'(?P<address>[\d\.]+)\s+(?P<aliases>[\w\s\-]+)(#?.*)')

        ipv6re = re.compile(r'(?P<address>[\da-f\:]+)\s+(?P<aliases>[\w\s\-]+)(#?.*)')

        current_ips = set([])

        current_aliases = set([])

        for line in etcehostlines:
            m4 = ipv4re.match(line)

            m6 = ipv6re.match(line)

            if m4:
                current_ips.add(m4.group('address'))

                current_aliases.update(m4.group('aliases').split())

            elif m6:
                current_ips.add(m6.group('address'))

                current_aliases.update(
                    [alias.strip() for alias in m6.group('aliases').split()])

        new_ips = []

        new_aliases = []

        for container in containers:
            for alias,ip in container.hosts_entries_ipv4:
                new_aliases.append(alias)
                new_ips.append(ip)

            for alias,ip in container.hosts_entries_ipv6:
                new_aliases.append(alias)
                new_ips.append(ip)

        collided_ips = current_ips.intersection(new_ips)

        collided_aliases = current_aliases.intersection(new_aliases)

        return list(collided_ips) + list(collided_aliases)


    def _check_reserved(self, containers):
        reserved_aliases = set([
            'localhost',
            'ip6-localhost',
            'ip6-loopback',
            'ip6-localnet',
            'ip6-mcastprefix',
            'ip6-allnodes',
            'ip6-allrouters'])

        reserved_ips = set([
            '127.0.0.1',
            '127.0.1.1',
            '::1',
            'fe00::0',
            'ff00::0',
            'ff02::1',
            'ff02::2'])

        for container in containers:
            new_ips = []

            new_aliases = []

            for alias,ip in container.hosts_entries_ipv4:
                new_aliases.append(alias)
                new_ips.append(ip)

            for alias,ip in container.hosts_entries_ipv6:
                new_aliases.append(alias)
                new_ips.append(ip)

            disallowed_ips = reserved_ips.intersection(new_ips)

            disallowed_aliases = reserved_aliases.intersection(new_aliases)

            if disallowed_ips:
                raise LXCError(
                    'ERROR: IPv4 address "%s" not permitted. Quitting.' \
                    % ','.join(disallowed_ips))

            if disallowed_aliases:
                raise LXCError(
                    'ERROR: hostname "%s" not permitted. Quitting.' \
                    % ','.join(disallowed_aliases))
