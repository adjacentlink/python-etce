#
# Copyright (c) 2013-2019 - Adjacent Link LLC, Bridgewater, New Jersey
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

#try:
from __builtin__ import raw_input
#except:
#    from builtins import input as raw_input

from collections import namedtuple
import errno
import getpass
import os
import json
import paramiko
from paramiko.client import RejectPolicy,WarningPolicy,AutoAddPolicy
from paramiko.pkey import PasswordRequiredException
from paramiko.rsakey import RSAKey
import re
import select
import socket
import sys
import io
from threading import Thread, Lock
import tarfile

import etce.fieldclient 
import etce.utils

from etce.fieldconnectionerror import FieldConnectionError
from etce.etceexecuteexception import ETCEExecuteException
from etce.platform import Platform
from etce.config import ConfigDictionary


def create(hosts, **kwargs):
    return SSHClient(hosts, **kwargs)


class PutThread(Thread):
    def __init__(self, connection, src_absname, dst_absname, host):
        Thread.__init__(self, name=host)
        self._sftpclient = connection.open_sftp()
        self._src = src_absname
        self._dst = dst_absname

    def run(self):
        self._sftpclient.put(self._src, self._dst)


class GetThread(Thread):
    def __init__(self, connection, src_absname, dst_absname, host):
        Thread.__init__(self, name=host)
        self._sftpclient = connection.open_sftp()
        self._src = src_absname
        self._dst = dst_absname

    def run(self):
        self._sftpclient.get(self._src, self._dst)



class Reader(Thread):
    State = namedtuple('State', ['haveretstr', 'read', 'partial_line', 'line', 'retstrio'])

    def __init__(self, stream, lock, name, banner, read_stderr):
        Thread.__init__(self, name=name)
        self._stream = stream
        self._lock = lock
        self._banner = banner
        self._read_stderr = read_stderr
        self._state = Reader.State(False, '', '', '', io.StringIO())

        # Initialize return object
        self._remote_returnobject = { 'isexception':False,
                                      'result': None,
                                      'traceback':None }

    def read(self, ep, evt):
        haveretstr, read, partial_line, line, retstrio = self._state

        if evt & select.EPOLLIN:
            if self._read_stderr:
                read = self._stream.channel.recv_stderr(1000).decode()
            else:
                read = self._stream.channel.recv(1000).decode()
            if not read:
                return True

            eol_index = read.find('\n')
            next_line = eol_index + 1

            while eol_index >= 0:
                line = partial_line + read[:eol_index]
                read = read[next_line:]
                partial_line = ''

                if SSHClient.RETURNVALUE_OPEN_DEMARCATOR in line:
                    haveretstr = True
                elif SSHClient.RETURNVALUE_CLOSE_DEMARCATOR in line:
                    haveretstr = False
                    endidx = line.find(SSHClient.RETURNVALUE_CLOSE_DEMARCATOR)
                    retstrio.write(line[0:endidx])
                    self._remote_returnobject = json.loads(retstrio.getvalue())
                    retstrio.close()
                elif haveretstr:
                    retstrio.write(line)
                else:
                    self._lock.acquire()
                    print(self._banner + line.strip())
                    self._lock.release()

                eol_index = read.find('\n')
                next_line = eol_index + 1

            partial_line += read

        self._state = Reader.State(haveretstr, read, partial_line, line, retstrio)

        ep.modify(self._stream.channel, select.EPOLLIN | select.EPOLLONESHOT)

        return False


    def returnobject(self):
        return self._remote_returnobject


class ExecuteThread(Thread):
    ReturnObject = namedtuple('ReturnObject', ['keyboard_interrupt', 'retval'])

    lock = Lock()
    
    def __init__(self, connection, command, host):
        Thread.__init__(self, name=host)
        self._connection = connection
        self._command = command
        self._banner = '[' + host + '] '
        self._remote_returnobject = ExecuteThread.ReturnObject(False, None)
        self._read_pipe, self._write_pipe = os.pipe()


    def interrupt(self):
        try:
            os.write(self._write_pipe, 'interrupt')
        except OSError as e:
            if e.errno == errno.EBADF:
                # ignore a write error on a thread that has already
                # terminated and closed its interrupt pipe. we don't care.
                pass
            else:
                # rethrow otherwise
                raise e


    def run(self):
        stdi, stdo, stde = self._connection.exec_command(self._command)

        readers = { stdo.channel.fileno():Reader(stdo, 
                                                 ExecuteThread.lock, 
                                                 self.name + '-stdo',
                                                 self._banner,
                                                 False) }

        readers_finished = { stdo.channel.fileno(): False }

        ep = select.epoll()

        ep.register(stdo.channel, select.EPOLLIN | select.EPOLLONESHOT)

        if stde.channel.fileno() != stdo.channel.fileno():
            readers[stde.channel.fileno()] = Reader(stde, 
                                                    ExecuteThread.lock, 
                                                    self.name + '-stde',
                                                    self._banner,
                                                    True)

            readers_finished[stde.channel.fileno()] = False

            ep.register(stde.channel, select.EPOLLIN | select.EPOLLONESHOT)

        # also, register our read pipe for keyboard interrupt
        ep.register(self._read_pipe, select.EPOLLIN)

        try:
            while not all(readers_finished.values()):
                results = ep.poll()
                for fd,evt in results:
                    if fd == self._read_pipe:
                        raise KeyboardInterrupt
                    else:
                        readers_finished[fd] = readers[fd].read(ep, evt)
            self._remote_returnobject = \
                ExecuteThread.ReturnObject(False,
                                           readers[stdo.channel.fileno()].returnobject())

        except KeyboardInterrupt:
            self._remote_returnobject = \
                ExecuteThread.ReturnObject(True,
                                           readers[stdo.channel.fileno()].returnobject())

        finally:
            os.close(self._read_pipe)
            os.close(self._write_pipe)


    def returnobject(self):
        return self._remote_returnobject



class SSHClient(etce.fieldclient.FieldClient):
    RETURNVALUE_OPEN_DEMARCATOR='***********ETCESSH_RETURN_VALUE_START********************'
    RETURNVALUE_CLOSE_DEMARCATOR='***********ETCESSH_RETURN_VALUE_STOP********************'

    def __init__(self, hosts, **kwargs):
        etce.fieldclient.FieldClient.__init__(self, hosts)

        self._connection_dict = {}

        self._execute_threads = []

        # ssh authentication is revised (5/7/2019):
        #
        # As tested against paramiko 1.16
        #
        # User must specify the ssh key file to use for authentication. They
        # can specify the key file explicitly with the sshkey parameter -
        # if the filename is not absolute, it is assumed to be a file located
        # in ~/.ssh. If sshkey is None, try to determine the key file from
        # ~/.ssh/config. If that also fails, check for the default ssh rsa
        # key ~/.ssh/id_rsa and attempt to use that.
        #
        # paramiko also allows provides a paramiko.agent.Agent class for
        # querying a running ssh-agent for its loaded keys. The agent
        # agent can be used:
        #
        #   1. by calling connect with allow_agent = True (the default)
        #   2. by calling Agent().get_keys() and passing to connect as pkey
        #
        # In the first case, the connect call selects the first key found
        # in the running agent and prompts for a passphrase - without indicating
        # the key it is prompting for. In the second case, the only identifying
        # information that can be obtained from an agent returned key object is
        # its md5 fingerprint - which is correct but not convenient for
        # helping the user select and identify the agent key to use. For these
        # reasons, ignore the agent for authentication and make the user identify
        # the key file(s) to use - preferable via there .ssh/config file.

        user = kwargs.get('user', None)

        port = kwargs.get('port', None)

        policystr = kwargs.get('policy', 'reject')

        sshkey = kwargs.get('sshkey', None)

        user_specified_key_file = None

        if sshkey:
            if sshkey[0] == '/':
                user_specified_key_file = sshkey
            else:
                user_specified_key_file = os.path.expanduser(os.path.join('~/.ssh', sshkey))

            if not os.path.exists(user_specified_key_file):
                raise FieldConnectionError(
                    'sshkey "%s" doesn\'t exist. Quitting.' % \
                    user_specified_key_file)

        self._envfile = kwargs.get('envfile', None)

        self._config = ConfigDictionary()

        ssh_config_file = os.path.expanduser('~/.ssh/config')

        ssh_config = None

        if os.path.exists(ssh_config_file):
            ssh_config = paramiko.SSHConfig()
            ssh_config.parse(open(ssh_config_file))

        authenticated_keys = {}

        policy = RejectPolicy

        if policystr == 'warning':
            policy = WarningPolicy
        elif policystr == 'autoadd':
            policy = AutoAddPolicy

        policy = self._set_unknown_hosts_policy(hosts, port, ssh_config, policy)

        for host in hosts:
            host_config = None

            if ssh_config:
                host_config = ssh_config.lookup(host)

            host_user = os.path.basename(os.path.expanduser('~'))
            if user:
                host_user = user
            elif host_config:
                host_user = host_config.get('user', host_user)

            host_port = 22
            if port:
                host_port = port
            elif host_config:
                host_port = host_config.get('port', host_port)

            host_key_filenames = []
            if user_specified_key_file:
                host_key_filenames = [ user_specified_key_file ]
            elif host_config:
                host_key_filenames = host_config.get('identityfile', host_key_filenames)

            if not host_key_filenames:
                default_rsa_keyfile = os.path.join(os.path.expanduser('~'), '.ssh', 'id_rsa')
                if os.path.exists(default_rsa_keyfile) and os.path.isfile(default_rsa_keyfile):
                    host_key_filenames = [default_rsa_keyfile]
                else:
                    message = 'Unable to find an RSA SSH key associated with host "%s". '\
                              'Either:\n\n' \
                              ' 1) specify a key using the "sshkey" option\n' \
                              ' 2) add a "Host" rule to your ~/.ssh/config file identifying the key\n' \
                              ' 3) create a default RSA key ~/.ssh/id_rsa".\n\n' \
                              'Quitting.' % host
                    raise FieldConnectionError(message)

            try:
                pkey = None

                for host_key_file in host_key_filenames:
                    if host_key_file in authenticated_keys:
                        pkey = authenticated_keys[host_key_file]
                    else:
                        pkey = None
                        try:
                            # Assume key is not passphrase protected first
                            pkey = RSAKey.from_private_key_file(host_key_file, None)
                        except PasswordRequiredException as pre:
                            # if that fails, prompt for passphrase
                            pkey = RSAKey.from_private_key_file(
                                host_key_file,
                                getpass.getpass('Enter passphrase for %s: ' % host_key_file))

                    authenticated_keys[host_key_file] = pkey

                    break

                if not pkey:
                    message = 'Unable to connect to host "%s", cannot authenticate. ' \
                              'Quitting.' % host,
                    raise FieldConnectionError(message)

                client = paramiko.SSHClient()

                client.load_system_host_keys()

                client.load_host_keys(os.path.expanduser('~/.ssh/known_hosts'))

                client.set_missing_host_key_policy(policy())

                client.connect(hostname=host,
                               username=host_user,
                               port=int(host_port),
                               pkey=pkey,
                               allow_agent=False)

                self._connection_dict[host] = client

            except socket.gaierror as ge:
                message = '%s "%s". Quitting.' % (ge.strerror, host)
                raise FieldConnectionError(message)

            except paramiko.ssh_exception.NoValidConnectionsError as e:
                raise FieldConnectionError('Unable to connect to host "%s", ' \
                                           'NoValidConnectionsError. Quitting.' % host)

            except Exception as e:
                raise FieldConnectionError(e)


    def sourceisdestination(self, host, srcfilename, dstfilename):
        if srcfilename == dstfilename:
            p = Platform()        
            if p.hostname_has_local_address(host):
                return True
        return False


    def put(self, 
            localsrc, 
            remotedst, 
            hosts, 
            doclobber=False,
            minclobberdepth=2):
        # this is intended to work like 'cp -R src dstdir' where src
        # can be a file name or directory name (relative or absolute path)
        # and destination is always a directory. dstdir can be relative
        # or absolute also, but it is rooted at WORK_DIRECTORY on the receiving
        # nodes. Examples:
        #
        # src is a file
        #  src=foo.txt, dst='/': moves foo.txt to WORK_DIRECTORY/foo.txt
        #  src=/home/bar/foo.txt, dst='/': moves foo.txt to WORK_DIRECTORY/foo.txt
        # src is a directory
        #  src=./foo/bar, dst='bar': moves bar to WORK_DIRECTORY/bar/bar
        #  src=/opt/foo/bar, dst='bar': moves bar to WORK_DIRECTORY/bar/bar
        # 
        remotesubdir = self._normalize_remotedst(remotedst)
        srcdir,srcbase = self._normalize_split_localsubdir(localsrc)
            
        if not os.path.exists(localsrc):
            raise RuntimeError('Error: "%s" doesn\'t exist. Quitting.' % srcbase)

        srctar = ''
        cwd = os.getcwd()
        try:
            # move to directory containing the src
            if len(srcdir) > 0:
                os.chdir(srcdir)

            # eliminate cases where src and dst are same path on same host
            # this is local directory that we are putting
            tmppath = os.getcwd()
            abssrc = os.path.join(tmppath, srcbase)
            # this is where this node would resolve the put location if it 
            # were a receiver
            etcedir = self._config.get('etce', 'WORK_DIRECTORY')
            tmpsubdir = remotesubdir
            if tmpsubdir == '.':
                tmpsubdir = ''
            absdst = os.path.join(etcedir, tmpsubdir, srcbase)
            dsthosts = []
            # only move when not same host and same directory
            for host in hosts:
                if self.sourceisdestination(host, abssrc, absdst):
                    print('Skipping host "%s". Source and destination are the same.' % host)
                    continue
                dsthosts.append(host)

            # continue if we have at least one non self host
            if len(dsthosts) == 0:
                return

            # first step, move the tar file to remote /tmp
            srctar = etce.utils.tarzip([srcbase])
            abssrctar = os.path.join(os.getcwd(), srctar)
            absdsttar = os.path.join('/tmp', srctar)
            threads = []
            for host in dsthosts:
                # create name of tar file on destination
                if host in self._connection_dict:
                    threads.append(PutThread(self._connection_dict[host],
                                             abssrctar,
                                             absdsttar,
                                             host))
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # now extract tarfile on dst hosts to the output path
            deletetar = True
            command = 'utils untarzip %s %s %s %d %s' % (absdsttar,
                                                         remotesubdir,
                                                         str(doclobber),
                                                         minclobberdepth,
                                                         str(deletetar))
            self.execute(command, hosts)
        finally:
            if os.path.exists(srctar):
                os.remove(srctar)
            os.chdir(cwd)


    def interrupt(self):
        for thread in self._execute_threads:
            thread.interrupt()

            
    def execute(self, commandstr, hosts, workingdir=None):
        # execute an etce command over ssh
        self._execute_threads = []

        fullcommandstr = ''

        if self._envfile is not None:
            fullcommandstr += '. %s; ' % self._envfile
        fullcommandstr += 'etce-field-exec '

        if not workingdir is None:
            fullcommandstr += '--cwd %s ' % workingdir

        fullcommandstr += commandstr
        for host in hosts:
            host_fullcommandstr = 'export HOSTNAME=%s; ' % host + fullcommandstr
            if host in self._connection_dict:
                self._execute_threads.append(ExecuteThread(self._connection_dict[host],
                                                           host_fullcommandstr,
                                                           host))

        # start the threads
        for t in self._execute_threads:
            t.start()

        # collect the return objects and monitor for exception
        returnobjs = {}
        
        exception = False

        keyboard_interrupt = False

        for t in self._execute_threads:
            # cycle on join to allow keyboard interrupts
            # to occur immediately
            while t.isAlive():
                t.join(5.0)
            
            returnobjs[t.name] = t.returnobject()
            
            if returnobjs[t.name].retval['isexception']:
                exception = True
            elif returnobjs[t.name].keyboard_interrupt:
                keyboard_interrupt = True
                
        # raise an exception if any return object is an exception
        if exception:
            raise ETCEExecuteException(returnobjs)

        if keyboard_interrupt:
            raise KeyboardInterrupt()

        # return in error free case
        return returnobjs


    def collect(self, remotesrc, localdstdir, hosts):
        if len(hosts) == 0:
            print('   Warning: no hosts.')
            return

        remotesubdir = self._normalize_remotesrc(remotesrc)

        srchosts = []
        # make the destination if it does not exist
        if not os.path.exists(localdstdir) or not os.path.isdir(localdstdir):
            print('Warning: local directory "%s" does not exist. Will attempt to make.' % \
                localdstdir)
            os.makedirs(localdstdir)
            srchosts = hosts
        else:
            # eliminate cases where src and dst are same path on same host
            # abssrc is where transfer would come from is this host is
            # among the remote hosts 
            etcedir = self._config.get('etce', 'WORK_DIRECTORY')
            abssrc = os.path.join(etcedir, remotesubdir)
            # figure out absolute name of local destination
            cwd = os.getcwd()
            os.chdir(localdstdir)
            absroot = os.getcwd()
            os.chdir(cwd)
            absdst = os.path.join(absroot, os.path.basename(remotesubdir))

            for host in hosts:
                if self.sourceisdestination(host, abssrc, absdst):
                    print('   Skipping host "%s". Source and destination are the same.' % host)
                    continue
                srchosts.append(host)

        if not srchosts:
            # No hosts to pull files from
            return

        # prep the items to fetch - tar them up and get their names
        retvals = self.execute('utils prepfiles %s' % remotesrc, srchosts)

        tarfiles = {}

        for host in retvals:
            if retvals[host].retval['result'] is not None:
                tarfiles[host] = retvals[host].retval['result']

        if not tarfiles:
            print('   Warning: no files to transfer.')
            return

        # Retrieve and extract data from each remote host
        removers = []
        for host,tfile in tarfiles.items():
            host_is_local = False

            if os.path.exists(tfile):
                # ignore file if it is already on local machine
                host_is_local = True

            getter = GetThread(self._connection_dict[host],
                               tfile,
                               os.path.join('/tmp',os.path.basename(tfile)),
                               host)

            getter.start()
            getter.join()

            ltf = os.path.join('/tmp', os.path.basename(tfile))
            if not os.path.exists(ltf) or not os.path.isfile(ltf):
                raise RuntimeError('%s does not exist' % ltf)

            tf = None
            try:
                command = 'etce-field-exec platform rmfile %s' % tfile
                if self._envfile is not None:
                    command = '. %s; %s' % (self._envfile, command)
                # also set up a thread to remove the tarfile on remotes
                removers.append(ExecuteThread(self._connection_dict[host],
                                             command,
                                             host))

                absolute_localdstdir = localdstdir
                if not absolute_localdstdir[0] == '/':
                    absolute_localdstdir = os.path.join(localdstdir, remotesrc)

                if host_is_local and os.path.exists(absolute_localdstdir):
                    print('Skipping collection from local host "%s".' % host)
                else:
                    print('Collecting files from host "%s" to "%s".' % (host, localdstdir))
                    tf = tarfile.open(ltf, 'r:gz')
                    tf.extractall(localdstdir)
                    tf.close()

            finally:
                os.remove(ltf)

        # execute the remove threads
        for t in removers:
            t.start()

        # collect the return objects and monitor for exception
        returnobjs = {}
        exception = False
        for t in removers:
            t.join()
            returnobjs[t.name] = t.returnobject()
            if returnobjs[t.name].retval['isexception']:
                exception = True

        # raise an exception if any return object is an exception
        if exception:
            raise ETCEExecuteException(returnobjs)



    def _normalize_remotesrc(self, remotesubdir):
        subdirre = re.compile(r'\w+(?:/\w*)*')
        if not subdirre.match(remotesubdir):
            raise ValueError('Error: %s is not a valid source' % remotesubdir)
        tmpsubdir = remotesubdir
        while tmpsubdir.rfind('/') == (len(tmpsubdir) - 1):
            tmpsubdir = tmpsubdir[:-1]
        return tmpsubdir


    def _normalize_remotedst(self, remotesubdir):
        subdir = remotesubdir.strip()
        if len(subdir) == 0 or subdir == '.':
            return '.'
        subdirre = re.compile(r'(?:\./)?(\w+/?)+')
        match = subdirre.match(subdir)
        if not match:
            raise ValueError('Error: %s is not a valid destination' % remotesubdir)
        if subdir[-1] == '/':
            subdir == subdir[:-1]
        if subdir[0] == '.':
            subdir = subdir[2:]
        # '..' not permitted in destination 
        if '..' in subdir.split('/'):
            raise ValueError('Error: ".." not permitted in destination path')
        # for simplicity, disallow '.' in remotedst also
        if '.' in subdir.split('/'):
            raise ValueError('Error: "." not permitted in multi-level destination path')
        return subdir


    def _normalize_split_localsubdir(self, localsubdir):
        srcbase = os.path.basename(localsubdir)
        srcdir = os.path.dirname(localsubdir)
        # disallow . or .. as srcbase or in srcdir
        if srcbase == '..' or srcbase == '.':
            raise ValueError('Error: src cannot be ".." or "."')
        if len(srcbase) == 0:
            raise ValueError('Error: No source specified')
        if '..' in srcdir.split('/'):
            raise ValueError('Error: ".." not permitted in src')
        if '.' in srcdir.split('/'):
            raise ValueError('Error: "." not permitted is src')

        return srcdir,srcbase


    def _set_unknown_hosts_policy(self, hosts, port, ssh_config, policy):
        known_hosts_filename = os.path.expanduser('~/.ssh/known_hosts')

        if not os.path.exists(known_hosts_filename) or \
           not os.path.isfile(known_hosts_filename):
            raise FieldConnectionError(
                'Error: ~/.ssh/known_hosts file does not exist, ' \
                'please create it.')

        all_host_keys = paramiko.util.load_host_keys(known_hosts_filename)

        # build list of hosts that don't have an ssh-rsa entry in known_hosts
        unknown_hosts = []

        for host in hosts:
            host_config = None

            if ssh_config:
                host_config = ssh_config.lookup(host)

            host_port = 22
            if port:
                host_port = port
            elif host_config:
                host_port = host_config.get('port', host_port)

            # try host and [host]:port as keys to check in known_hosts as
            # format depends on ssh version
            keys_to_check = set([host, '[%s]:%d' % (host, int(host_port))])

            found_keys = keys_to_check.intersection(set(all_host_keys.keys()))

            if not found_keys:
                unknown_hosts.append(host)
            else:
                host_keys = all_host_keys.get(sorted(found_keys)[0], None)

                rsakey = host_keys.get('ssh-rsa', None)

                if not rsakey:
                    unknown_hosts.append(host)

        # if we found an unknown host and we're configured to reject, ask user for permission to add
        if unknown_hosts and (policy == RejectPolicy):
            unknown_hosts_str = '{' + ', '.join(sorted(unknown_hosts)) + '}'
            response = raw_input('Unknown hosts: %s. Add to known_hosts (Y/N) [N]? ' % unknown_hosts_str)

            if not response.upper() == 'Y':
                print('Quitting.', file=sys.stderr)
                exit(1)

            return AutoAddPolicy

        return policy


    def close(self):
        for host in self._connection_dict:
            self._connection_dict[host].close()
        
