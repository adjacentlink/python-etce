#!/usr/bin/env python
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

import argparse
import os
import shutil
import sys

from etce.clientbuilder import ClientBuilder
from etce.config import ConfigDictionary
from etce.lxcerror import LXCError
from etce.lxcmanager import startlxcs,stoplxcs
from etce.lxcplanfiledoc import LXCPlanFileDoc
from etce.platform import Platform


def startfield(args):
    this_hostname = Platform().hostname()

    plandoc = LXCPlanFileDoc(args.lxcplanfile)

    config = ConfigDictionary()
    
    workdir = config.get('etce', 'WORK_DIRECTORY')

    if not os.path.exists(workdir):
        raise LXCError('ETCE WORK_DIRECTORY "%s" not found. ' \
                       'Please create it before starting.' % workdir)
        
    # lockfile
    lockfilename = \
        os.path.join(config.get('etce', 'LOCK_FILE_DIRECTORY'),
                     'etce.lxc.lock')

    if os.path.isfile(lockfilename):
        err = 'Detected an active lxc field with root at: %s. ' \
              'Run "etce-lxc stop" first.' % \
              plandoc.lxc_root_directory(this_hostname)
        raise LXCError(err)
            
    startlxcs(plandoc,
              args.writehosts,
              args.forcelxcroot,
              args.dryrun)

    if not args.dryrun:
        shutil.copy(args.lxcplanfile, lockfilename)

    other_hosts = set(plandoc.hostnames()).difference(
        ['localhost', this_hostname])

    # start containers on other hosts, if any
    if other_hosts:
        client = None
        try:
            client = ClientBuilder().build(\
                        other_hosts,
                        user=args.user,
                        port=args.port,
                        key_filename=args.key_filename)

            # push the file and execute
            client.put(args.lxcplanfile, '.', other_hosts, doclobber=True)

            # on the destination node the netplan file gets pushed to the
            # ETCE WORK_DIRECTORY
            command = 'lxcmanager startlxcs %s writehosts=%s forcelxcroot=%s' \
                      % (os.path.basename(args.lxcplanfile),
                         args.writehosts,
                         args.forcelxcroot)

            ret = client.execute(command,
                                 other_hosts)

            for k in ret:
                print '[%s] return: %s' % (k, ret[k].retval['result'])

        finally:
            if client:
                client.close()


def stopfield(args):
    lockfiledir = ConfigDictionary().get('etce', 'LOCK_FILE_DIRECTORY')

    lockfilename = os.path.join(lockfiledir, 'etce.lxc.lock')

    if not os.path.exists(lockfilename) or not os.path.isfile(lockfilename):
        raise LXCError('Lockfile "%s" not found. Quitting.' % lockfilename)

    plandoc = LXCPlanFileDoc(lockfilename)

    other_hosts = set(plandoc.hostnames()).difference(
        ['localhost', Platform().hostname()])
    
    # stop containers on other hosts, if any
    try:
        if other_hosts:
            client = None
            try:
                client = ClientBuilder().build(other_hosts,
                                               user=args.user,
                                               port=args.port,
                                               key_filename=args.key_filename)

                # push the file and execute
                client.put(lockfilename, '.', other_hosts, doclobber=True)

                # on the destination node the netplan file gets pushed to the
                # ETCE WORK_DIRECTORY
                command = 'lxcmanager stoplxcs %s' % os.path.basename(lockfilename)

                ret = client.execute(command, other_hosts)

                for k in ret:
                    print '[%s] return: %s' % (k, ret[k].retval['result'])

            finally:
                if client:
                    client.close()
    finally:
        stoplxcs(plandoc)



def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('--key_filename',
                        action='store',
                        nargs='+',
                        default=None,
                        help='''If the LXCPLANFILE contains remote host(s),
                        connect to the hosts using the specified private
                        key file.''')
    parser.add_argument('--port',
                        action='store',
                        type=int,
                        default=None,
                        help='''If the LXCPLANFILE contains remote host(s),
                        connect to the hosts via the specified port. If not
                        specified, ETCE will look for the host's "Port" value
                        in the ~/.ssh/config file. If not found, uses the default
                        ssh port value, 22.''')
    parser.add_argument('--user',
                        action='store',
                        default=None,
                        help='''If the LXCPLANFILE contains remote host(s),
                        connect to the hosts as the specified user. If not
                        specified, ETCE will look for the host's "User" value
                        in the ~/.ssh/config file. If not found, uses the
                        current user''')
    
    subparsers = parser.add_subparsers()

    parser_start = \
        subparsers.add_parser('start', 
                              help='Start a network of LXC container and Linux bridges' \
                              'based on the description in the LXC plan file.')

    parser_start.add_argument('--dryrun',
                              action='store_true',
                              default=False,
                              help='''Create the container configurations but do not start
                              the container.''')
    parser_start.add_argument('--forcelxcroot',
                              action='store_true',
                              default=False,
                              help='''Force the deletion of the lxcroot directory
                              if it already exists.''')
    parser_start.add_argument('--writehosts',
                              action='store_true',
                              default=False,
                              help='''Add an /etc/hosts entry for interface elements in the
                              LXCPLANFILE that contain a hosts_entry_ipv4 or hosts_entry_ipv6 
                              attribute. The has form "lxc.network.ipv4 hosts_entry_ipv4" or
                              "lxc.netowrk.ipv6 hosts_entry_ipv6".''')
    parser_start.add_argument('lxcplanfile',
                              metavar='LXCPLANFILE',
                              action='store',
                              help='The LXC plan file')

    parser_start.set_defaults(func=startfield)

    parser_stop = \
        subparsers.add_parser('stop', 
                              help = 'Stop the LXC container network previously started with ' \
                              '"etce-lxc start"')

    parser_stop.set_defaults(func=stopfield)

    args = parser.parse_args()

    try:
        args.func(args)
    except LXCError as e:
        print e


if __name__=='__main__':
    main()
