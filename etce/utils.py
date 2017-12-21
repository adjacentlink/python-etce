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
import os.path
import resource
import shlex
import shutil
import subprocess
import sys
import syslog
import tarfile
import tempfile

import etce.timeutils

from etce.config import ConfigDictionary


def generate_tempfile_name(directory=None, prefix=None):
    # create a unique name by creating a temporaryfile
    # then deleting & using the name.
    # mkstemp returns a tuple (filedescriptor, filename)
    fd = name = None

    if directory:
        if prefix:
            fd,name = tempfile.mkstemp(dir=directory, prefix=prefix)
        else:
            fd,name = tempfile.mkstemp(dir=directory)
            
        os.close(fd)
        os.remove(name)
    else:
        if prefix:
            fd,name = tempfile.mkstemp(prefix=prefix)
        else:
            fd,name = tempfile.mkstemp()

        os.close(fd)
        os.remove(name)
        name = os.path.basename(name)

    return name


# tar and zip src to dstarchive.
def tarzip(srclist, dstarchive=None):
    if not srclist:
        return None

    for src in srclist:
        if not os.path.exists(src):
            raise RuntimeError('%s does not exist' % src)

    if not dstarchive:
        dstarchive = generate_tempfile_name() + '.tgz'
    try:
        t = tarfile.open(dstarchive, 'w:gz')
        for src in srclist:
            t.add(src, os.path.basename(src))
    finally:
        t.close()    
    
    return dstarchive


def prepfiles(srcsubdir):
    # find the named subdir, tar it up and return it's absolute path
    # or None if path doesn't exist
    etcedir = ConfigDictionary().get('etce','WORK_DIRECTORY')
    srcabsdir = os.path.join(etcedir, srcsubdir)
    parentdir = os.path.dirname(srcabsdir)
    child = os.path.basename(srcabsdir)
    cwd = os.getcwd()
    try:
        os.chdir(parentdir)
        if not os.path.exists(child):
            return None
        tarfile = tarzip([child])
        return os.path.join(parentdir, tarfile)
    finally:
        os.chdir(cwd)


def untarzip(tarname, dstpath, clobber, minclobberdepth, deletetar):
    # already a directory? just return path
    if os.path.isdir(tarname):
        return tarname
    # not a tarfile
    if not tarfile.is_tarfile(tarname):
        return tarname

    # get first level names in the tarfile
    t = tarfile.open(tarname, 'r:gz')
    tarsubdirs = set([ name.split(os.sep)[0] for name in t.getnames()])

    # calculate the absolute destination path, rooted at WORK_DIRECTORY
    etcedir = ConfigDictionary().get('etce', 'WORK_DIRECTORY')
    while dstpath.find('/') == 0 or dstpath.find('.') == 0:
        dstpath = dstpath[1:]
    extractdir = os.path.join(etcedir, dstpath)

    # make the extractdir if it doesn't exist
    if not os.path.exists(extractdir):
        os.makedirs(extractdir)

    # do not extract anything if ...
    targetentries = set(os.listdir(extractdir))
    collisionentries = tarsubdirs.intersection(targetentries)
    if len(collisionentries) > 0:
        # ... there is a collision ...
        if not clobber:
            firstcollision =  collisionentries.pop()
            error = 'Error: directory %s already exists. ' \
                    'Quitting.' % os.path.join(extractdir, firstcollision)
            raise RuntimeError(error)
        else:
            # ... or the target directory is less than minclobber depth
            depth = sum([ 1 for tok in extractdir.split('/')
                          if len(tok.strip()) > 0])
            if depth < minclobberdepth:
                error = 'Error: target directory %s is less than ' \
                        'minclobberdepth(%d). Quitting.' % (extractdir, minclobberdepth)
                raise RuntimeError(error)
    try:
        for entry in collisionentries:
            fullentry = os.path.join(extractdir, entry)
            if os.path.isdir(fullentry):
                shutil.rmtree(os.path.join(extractdir, entry))
            else:
                os.remove(fullentry)
        t.extractall(extractdir)
    finally:
        t.close()

    if deletetar:
        os.remove(tarname)

    return extractdir


def daemonize_command(commandstr,
                      stdout=None,
                      stderr=None,
                      starttime=None):

    # 1. print the command name
    print commandstr

    # 2. shlex the command string
    command = shlex.split(commandstr)

    # 3. if daemonize - do it
    pid = daemonize()
    if  pid > 0:
        return pid,None

    stdoutfd = None
    stderrfd = None
    if not stdout is None:
        stdoutfd = open(stdout, 'w')
    if not stderr is None:
        if stdout == stderr:
            stderrfd = stdoutfd
        else:
            stderrfd = open(stderr, 'w')


    # 4. wait until specified time to start
    if starttime:
        etce.timeutils.sleep_until(starttime)

    # 5. create the Popen subprocess
    sp = subprocess.Popen(command, stdout=stdoutfd, stderr=stderrfd)

    return 0,sp


def daemonize():
    softlimit,hardlimit = resource.getrlimit(resource.RLIMIT_NOFILE)

    pid = os.fork()
    if pid > 0:
        # parent should return to client calling daemonize
        return pid

    os.chdir('/')
    os.umask(0)
    os.setsid()

    # double fork
    pid = os.fork()
    if pid > 0:            
        sys.exit(0)

    for fd in range(0,hardlimit):
        try:
            os.close(fd)
        except:
            pass

    fd0 = os.open("/dev/null",os.O_RDWR)
    fd1 = os.dup(fd0)
    fd2 = os.dup(fd0)

    return 0


def hostsfromarg(hostlist):
    hosts = []
    for entry in hostlist:
        # either it's a file
        if os.path.exists(entry) and os.path.isfile(entry):
            with open(entry, 'r') as f:
                hosts = [ host.strip() for host in f if host.strip() ]
        # or the name of a node
        else:
            hosts.append(entry)

    return hosts  


def timestamp():
    dt = datetime.datetime.now()
    return '%04d%02d%02d%02d%02d%02d' % (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)


def nodestrtonodes(nodestr):
    nodes = []
    if nodestr is None:
        return nodes
    if len(nodestr.strip()) == 0:
        return nodes

    noderanges = nodestr.split(',')
    for noderange in noderanges:
        endpoints = noderange.split('-')
        startendpoint = int(endpoints[0])
        stopendpoint = int(endpoints[-1])
        newnodes = []
        if startendpoint > stopendpoint:
            newnodes = [ i for i in range(startendpoint,stopendpoint-1,-1) ]
        else:
            newnodes = [ i for i in range(startendpoint,stopendpoint+1) ]
        for i in newnodes:
            if not i in nodes:
                nodes.append(i)
    return nodes


def configstrtoval(valstr):
    # float
    try:
        if '.' in valstr:
            result = float(valstr)
            return result
    except ValueError:
        pass
    #int
    try:
        result = int(valstr)
        return result
    except ValueError:
        pass
    # boolean
    if valstr.upper() == 'TRUE':
        return True
    if valstr.upper() == 'FALSE':
        return False
    # string
    return valstr

