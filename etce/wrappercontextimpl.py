#
# Copyright (c) 2014-2018 - Adjacent Link LLC, Bridgewater, New Jersey
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


class WrapperContextImpl(ArgRegistrar):
    ''' WrapperContextImpl implements the WrapperContext interface.'''
    def __init__(self,
                 wrappername,
                 wrapperinstance,
                 trialargs,
                 testargs,
                 config,
                 testdir):
        self._trialargs = trialargs
        self._testargs = testargs
        self._config = config
        self._testdir = testdir
        self._platform = Platform()
        self._wrappername = wrappername
        self._default_pidfilename = '%s/etce.%s.%s.pid' \
                                    % (os.path.join(self._config.get('etce', 'WORK_DIRECTORY'), 'lock'),
                                       self.platform.hostname(),
                                       self._wrappername)

        self._description = wrapperinstance.__doc__


        # start with reserved args set here ...
        self._args = {
            'default_pidfilename':self._default_pidfilename,
            'nodename':self._testdir.nodename(),
            'nodeid':self._testdir.nodeid(),
            'testname':self._testdir.name(),
            'wrappername':self._wrappername,
            'infile':None,
            'outfile':None
        }

        # ... and the ones passed in
        self._args.update(trialargs)

        # these are the reserved args that cannot be overwritten
        self._reserved_args = set(self._args)

        # fill in the arguments registered by the wrapper
        wrapperinstance.register(self)
        
        storefile = os.path.join(self._trialargs['logdirectory'],
                                 'etce.store')

        self._wrapperstore = WrapperStore(storefile)

        self._wrapperstore.update({'etce':{'starttime': self._trialargs['starttime']}},
                                  self._args['nodename'])

        
    def register_argument(self, argname, defaultval, description):
        if argname in self._reserved_args:
            raise ValueError('Wrapper "%s" attempting to register a ' \
                             'reserved argument "%s". Quitting.' % \
                             (self._args['wrappername'],
                              argname))

        if self._testdir.hasconfig(self._wrappername, argname):
            self._args[argname] = \
                self._testdir.getconfig(self._wrappername, argname, defaultval)
        elif argname in self._testargs:
            self._args[argname] = self._testargs[argname]
        else:
            self._args[argname] = defaultval


    def register_infile_name(self, name):
        self._args['infile'] = self._testdir.getfile(name)


    def register_outfile_name(self, name):
        self._args['outfile'] = os.path.join(self._trialargs['logdirectory'], name)


    def store(self, namevaldict):
        self._wrapperstore.update({self._args['wrappername']:namevaldict},
                                  self._args['nodename'])


    @property
    def platform(self):
        return self._platform


    @property
    def args(self):
        return ArgProxy(self._args)


    def daemonize(self,
                  commandstr,
                  stdout=None,
                  stderr=None,
                  pidfilename=None,
                  genpidfile=True,
                  pidincrement=0,
                  starttime=None):

        # print the commandstr and return on a dryrun         
        if self._trialargs['dryrun']:
            print commandstr
            return
        
        # 1. call self.stop(pidfilename)
        self.stop(pidfilename)

        # run the command
        pid,subprocess = \
                         etce.utils.daemonize_command(commandstr,
                                                      stdout,
                                                      stderr,
                                                      starttime)

        # return on parent
        if pid > 0:
            return

        # 2. if genpidfile is True, and pidfilename is None,
        #    generate the pidfilename
        if genpidfile and pidfilename is None:
            pidfilename = self._default_pidfilename

        # 3. write the pid to pidfilename
        if genpidfile:
            with open(pidfilename, 'w') as pidfile:
                pidfile.write(str(subprocess.pid+pidincrement))

        # 4. wait on subprocess
        subprocess.wait()

        # 5. exit, do not return, because returning
        #    will cause any subsequent wrappers in this
        #    step to be rerun
        sys.exit(0)


    def run(self,
            commandstr,
            stdout=None,
            stderr=None,
            pidfilename=None,
            genpidfile=True,
            pidincrement=0):

        # print the commandstr and return on a dryrun         
        if self._trialargs['dryrun']:
            print commandstr
            return
        
        self.stop(pidfilename)

        print commandstr

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

        #    generate the pidfilename
        if genpidfile and pidfilename is None:
            pidfilename = self._default_pidfilename

        # create the Popen subprocess
        sp = subprocess.Popen(command, stdout=stdoutfd, stderr=stderrfd)

        # write the pid to pidfilename
        if genpidfile:
            with open(pidfilename, 'w') as pidfile:
                pidfile.write(str(sp.pid+pidincrement))

        # wait on subprocess
        sp.wait()


    def stop(self, pidfilename=None, signal=signal.SIGQUIT, decorator=''):
        # use default pidfilename if None specified
        if pidfilename is None:
            pidfilename = self._default_pidfilename

        pid = self._platform.readpid(pidfilename)

        # if found a pid, kill the process and remove the file
        if pid:
            try:
                print 'killing pid %d found in %s' % (pid, pidfilename)
                command = '%s kill -%d %d' % (pid, signal)
                sp = subprocess.Popen(command)
                sp.wait()
                #os.kill(pid, signal.SIGQUIT)
            except OSError as e:
                # orphaned pidfile - process already dead
                pass 
            finally:
                os.remove(pidfilename)
