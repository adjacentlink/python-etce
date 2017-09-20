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
import shlex
import signal
import subprocess
import sys

import etce.utils
import etce.timeutils
from etce.argproxy import ArgProxy
from etce.argregistrar import ArgRegistrar
from etce.platform import Platform
from etce.wrapperstore import WrapperStore
from etce.config import ConfigDictionary


class WrapperContext(ArgRegistrar):
    ''' WrapperContext groups various objects and data, useful 
        to wrappers, into a single interface. It makes two
        groups of parameters available to the wrapper - "args"
        and "overlays".

        args are parameter values passed to wrappers on a test
        by test basis. They are set in the test executer.xml file,
        the (optional) test config.xml file and from internal 
        values calculated on each test run:

           default_pidfilename
           logdirectory
           nodename
           nodeid
           starttime
           stepname
           testname
           wrappername

        Overlays are parameter values passed to wrappers from the
        etce.conf file on the host where the wrapper runs. 
    '''
    def __init__(self,
                 wrappername,
                 wrapperinstance,
                 trialargs,
                 testargs,
                 nodeconfig,
                 testdir):
        self._trialargs = trialargs
        self._testargs = testargs
        self._nodeconfig = nodeconfig
        self._testdir = testdir
        self._platform = Platform()
        self._wrappername = wrappername
        self._default_pidfilename = '%s/etce.%s.%s.pid' \
                % (ConfigDictionary().get('etce', 'LOCK_FILE_DIRECTORY'),
                   self.platform.hostname(),
                   self._wrappername)

        self._description = wrapperinstance.__doc__

        
        # start with empty dicts ...
        self._args = { 'infile':None, 'outfile': None }
        self._overlays = {}

        # ... fill in the values registered by the wrapper
        wrapperinstance.register(self)

        # ... overlay with commonly needed names
        self._args.update({
            'default_pidfilename':self._default_pidfilename,
            'nodename':self._testdir.nodename(),
            'nodeid':self._testdir.nodeid(),
            'testname':self._testdir.name(),
            'wrappername':self._wrappername
            })

        # ... and with items generated on each trial
        self._args.update(trialargs)

        storefile = os.path.join(self._trialargs['logdirectory'],
                                 'etce.store')

        self._wrapperstore = WrapperStore(storefile)


    def register_argument(self, argname, defaultval, description):
        if self._testdir.hasconfig(self._wrappername,
                                   argname):
            self._args[argname] = self._testdir.getconfig(self._wrappername,
                                                           argname,
                                                           defaultval)
        elif argname in self._testargs:
            self._args[argname] = self._testargs[argname]
        else:
            self._args[argname] = defaultval


    def register_overlay(self, overlayname, defaultval, description):
        self._overlays[overlayname] = \
            self._nodeconfig.get('overlays',overlayname,defaultval)


    def register_infile_name(self, name):
        self._args['infile'] = self._testdir.getfile(name)


    def register_outfile_name(self, name):
        self._args['outfile'] = os.path.join(
            self._trialargs['logdirectory'], name)


    def store(self, namevaldict):
        self._wrapperstore.update(self._testdir.nodename(),
                                  {self._args['wrappername']:namevaldict})


    @property
    def platform(self):
        return self._platform


    @property
    def args(self):
        return ArgProxy(self._args)


    @property
    def overlays(self):
        return ArgProxy(self._overlays)


    @property
    def default_pidfilename(self):
        return self._default_pidfilename
    
    
    def daemonize(self,
                  commandstr,
                  stdout=None,
                  stderr=None,
                  pidfilename=None,
                  genpidfile=True,
                  pidincrement=0,
                  starttime=None):
        
        # 1. call self.stop(pidfilename)
        self.stop(pidfilename)
        
        # 2. print the command name
        print commandstr
        
        # 3. shlex the command string
        command = shlex.split(commandstr)

        # 4. if daemonize - do it
        if etce.utils.daemonize() > 0:
            return

        stdoutfd = None
        stderrfd = None
        if not stdout is None:
            stdoutfd = open(stdout, 'w')
        if not stderr is None:
            if stdout == stderr:
                stderrfd = stdoutfd
            else:
                stderrfd = open(stderr, 'w')

        # 6. if genpidfile is True, and pidfilename is None,
        #    generate the pidfilename
        if genpidfile and pidfilename is None:
            pidfilename = self.default_pidfilename

        # wait until specified time to start
        if not starttime is None:
            etce.timeutils.sleep_until(starttime)
            
        # 7. create the Popen subprocess
        sp = subprocess.Popen(command, stdout=stdoutfd, stderr=stderrfd)

        # 8. write the pid to pidfilename
        if genpidfile:
            with open(pidfilename, 'w') as pidfile:
                pidfile.write(str(sp.pid+pidincrement))

        # 9. wait on subprocess
        sp.wait()

        # 10. exit, do not return, because returning
        #     will cause any subsequent wrappers in this
        #     step to be rerun
        sys.exit(0)

    
    def run(self,
            commandstr,
            stdout=None,
            stderr=None,
            pidfilename=None,
            genpidfile=True,
            pidincrement=0):
        
        # 1. call self.stop(pidfilename)
        self.stop(pidfilename)
        
        # 2. print the command name
        print commandstr
        
        # 3. shlex the command string
        command = shlex.split(commandstr)

        stdoutfd = None
        stderrfd = None
        if not stdout is None:
            stdoutfd = open(stdout, 'w')
        if not stderr is None:
            if stdout == stderr:
                stderrfd = stdoutfd
            else:
                stderrfd = open(stderr, 'w')

        # 4. if genpidfile is True, and pidfilename is None,
        #    generate the pidfilename
        if genpidfile and pidfilename is None:
            pidfilename = self.default_pidfilename

        # 5. create the Popen subprocess
        sp = subprocess.Popen(command, stdout=stdoutfd, stderr=stderrfd)

        # 6. write the pid to pidfilename
        if genpidfile:
            with open(pidfilename, 'w') as pidfile:
                pidfile.write(str(sp.pid+pidincrement))

        # 7. wait on subprocess
        sp.wait()


    def readpid(self, pidfilename):
        pid = None
        if os.path.exists(pidfilename):
            if os.path.isfile(pidfilename):
                pid = int(open(pidfilename).readline())
            else:
                # error - pidfile is not a regular fle
                error = 'pidfile %s exists but is not a regular file. ' \
                        'Quitting' % pidfilename
                raise RuntimeError(error)
        return pid


    def stop(self, pidfilename=None):
        # use default pidfilename if None specified
        if pidfilename is None:
            pidfilename = self.default_pidfilename

        pid = self.readpid(pidfilename)

        # if found a pid, kill the process and remove the file
        if pid is not None:
            try:
                print 'killing pid %d found in %s' % (pid, pidfilename)
                os.kill(pid, signal.SIGQUIT)
            except OSError as e:
                # orphaned pidfile - process already dead
                pass 
            finally:
                os.remove(pidfilename)
