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

import getpass
import os
import json
import paramiko
import re
import socket
import StringIO
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


class ReadThread(Thread):
    def __init__(self, stream, lock, name, banner):
        Thread.__init__(self, name=name)
        self._stream = stream
        self._lock = lock
        self._banner = banner
        # Initialize return as a an exception message - No Value Returned
        self._returnobject = { 'isexception':True,
                               'result': None,
                               'traceback':None }

    def run(self):
        retstrio = StringIO.StringIO()
        haveretstr = False
        for line in self._stream:
            if SSHClient.RETURNVALUE_OPEN_DEMARCATOR in line:
                haveretstr = True
            elif SSHClient.RETURNVALUE_CLOSE_DEMARCATOR in line:
                haveretstr = False
                endidx = line.find(SSHClient.RETURNVALUE_CLOSE_DEMARCATOR)
                retstrio.write(line[0:endidx])
                self._returnobject = json.loads(retstrio.getvalue())
                retstrio.close()
            elif haveretstr:
                retstrio.write(line)
            else:
                self._lock.acquire()
                print self._banner + line.strip()
                self._lock.release()
           
    def returnobject(self):
        return self._returnobject


class ExecuteThread(Thread):
    lock = Lock()
    def __init__(self, connection, command, host):
        Thread.__init__(self, name=host)
        self._connection = connection
        self._command = command
        self._banner = '[' + host + '] '

    def run(self):
        stdi, stdo, stde = self._connection.exec_command(self._command)
        self._stdoreader = ReadThread(stdo, 
                                      ExecuteThread.lock, 
                                      self.name + '-stdo',
                                      self._banner)
        self._stdereader = ReadThread(stde, 
                                      ExecuteThread.lock, 
                                      self.name + '-stde',
                                      self._banner)
        self._stdoreader.start()
        self._stdereader.start()
        self._stdoreader.join()
        self._stdereader.join()

    def returnobject(self):
        return self._stdoreader.returnobject()


class SSHClient(etce.fieldclient.FieldClient):
    RETURNVALUE_OPEN_DEMARCATOR='***********ETCESSH_RETURN_VALUE_START********************'
    RETURNVALUE_CLOSE_DEMARCATOR='***********ETCESSH_RETURN_VALUE_STOP********************'

    def __init__(self, hosts, **kwargs):
        etce.fieldclient.FieldClient.__init__(self, hosts)

        self._connection_dict = {}

        user = kwargs.get('user', None)

        port = kwargs.get('port', None)

        key_filenames = kwargs.get('key_filename', [])

        self._envfile = kwargs.get('envfile', None)

        self._config = ConfigDictionary()

        if user is None:
            user = self._config.get('etce', 'SSH_USER')

        if port is None:
            port = int(self._config.get('etce', 'SSH_PORT'))

        for host in hosts:
            try:
                client = paramiko.SSHClient()

                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                self._connection_dict[host] = client

                try:
                    self._connection_dict[host].connect(hostname=host,
                                                        username=user,
                                                        port=int(port),
                                                        key_filename=key_filenames,
                                                        allow_agent=False)
                except paramiko.ssh_exception.AuthenticationException as e:
                    if key_filenames:
                        client.connect(hostname=host,
                                       username=user,
                                       port=int(port),
                                       key_filename=key_filenames,
                                       allow_agent=False,
                                       password=getpass.getpass('Passphrase for %s: ' % key_filenames[0]))
                    else:
                        raise e

            except socket.gaierror as ge:
                message = '%s "%s". Quitting.' % (ge.strerror, host)
                raise FieldConnectionError(message)

            except paramiko.ssh_exception.NoValidConnectionsError as e:
                raise FieldConnectionError('Unable to connect to host "%s". Quitting.' % host)

            except Exception as e:
                print 'here exception'
                message = 'Unable to connect to host "%s" (%s). Quitting.' % (host, str(e))
                raise FieldConnectionError(message)

            
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
                    print 'Skipping host "%s". Source and destination are the same.' % host
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


    def execute(self, commandstr, hosts, workingdir=None):
        # execute an etce command over ssh
        threads = []

        fullcommandstr = ''
        if self._envfile is not None:
            fullcommandstr += '. %s; ' % self._envfile
        fullcommandstr += 'etce-exec.ssh '
        if not workingdir is None:
            fullcommandstr += '--cwd %s ' % workingdir
        fullcommandstr += commandstr
        for host in hosts:
            if host in self._connection_dict:
                threads.append(ExecuteThread(self._connection_dict[host],
                                             fullcommandstr,
                                             host))
        # start the threads
        for t in threads:
            t.start()

        # collect the return objects and monitor for exception
        returnobjs = {}
        exception = False
        for t in threads:
            t.join()
            returnobjs[t.name] = t.returnobject()
            if returnobjs[t.name]['isexception']:
                exception = True

        # raise an exception if any return object is an exception
        if exception:
            raise ETCEExecuteException(returnobjs)

        # return in error free case
        return returnobjs


    def collect(self, remotesrc, localdstdir, hosts):
        print 'Collecting files from hosts "%s" to "%s."' % (', '.join(hosts), localdstdir)

        if len(hosts) == 0:
            print '   Warning: no hosts.'
            return

        remotesubdir = self._normalize_remotesrc(remotesrc)

        srchosts = []
        # make the destination if it does not exist
        if not os.path.exists(localdstdir) or not os.path.isdir(localdstdir):
            print 'Warning: local directory "%s" does not exist. Will attempt to make.' % \
                localdstdir
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
                    print '   Skipping host "%s". Source and destination are the same.' % host
                    continue
                srchosts.append(host)

        if not srchosts:
            # No hosts to pull files from
            return

        # prep the items to fetch - tar them up and get their names
        retvals = self.execute('utils prepfiles %s' % remotesrc, srchosts)
        tarfiles = {}
        for host in retvals:
            if retvals[host]['result'] is not None:
                tarfiles[host] = retvals[host]['result']
        
        if not tarfiles:
            print '   Warning: no files to transfer.'
            return

        # Create GetThread for the hosts that have a tarfile to transfer
        threads = [ GetThread(self._connection_dict[host],
                              tfile,
                              os.path.join('/tmp',os.path.basename(tfile)),
                              host) for host,tfile in tarfiles.items() ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # extract the tarfiles to the dst directory
        threads = []
        for h,tfile in tarfiles.items():
            ltf = os.path.join('/tmp', os.path.basename(tfile))
            if not os.path.exists(ltf) or not os.path.isfile(ltf):
                raise RuntimeError('%s does not exist' % ltf)
            tf = None
            try:
                tf = tarfile.open(ltf, 'r:gz')
                tf.extractall(localdstdir)
                command = 'etce-exec.ssh platform rmfile %s' % tfile
                if self._envfile is not None:
                    command = '. %s; %s' % (self._envfile, command)
                # also set up a thread to remove the tarfile on remotes
                threads.append(ExecuteThread(self._connection_dict[host],
                                             command,
                                             host))
            finally:
                if not tf is None:
                    tf.close()
                os.remove(ltf)

        # execute the remove threads
        for t in threads:
            t.start()

        # collect the return objects and monitor for exception
        returnobjs = {}
        exception = False
        for t in threads:
            t.join()
            returnobjs[t.name] = t.returnobject()
            if returnobjs[t.name]['isexception']:
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


    def close(self):
        for host in self._connection_dict:
            self._connection_dict[host].close()
        
