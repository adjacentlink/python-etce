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

from __future__ import absolute_import, division, print_function

import os
import shlex
from signal import SIGQUIT
import subprocess
import sys

import etce.utils
import etce.timeutils
from etce.argproxy import ArgProxy
from etce.argregistrar import ArgRegistrar
from etce.platform import Platform
from etce.wrappererror import WrapperError
from etce.wrapperstore import WrapperStore


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
        self._sudo = False
        self._default_pidfilename = \
            '%s/etce.%s.%s.pid' \
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


    def run_with_sudo(self):
        # ignore run with sudo requests when configured to do so
        if self._config.get('etce', 'IGNORE_RUN_WITH_SUDO').lower() == 'yes':
            return
        self._sudo = True


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
                  command,
                  argstr,
                  stdout=None,
                  stderr=None,
                  pidfilename=None,
                  genpidfile=True,
                  pidincrement=0,
                  starttime=None,
                  extra_paths=[]):

        commandstr = self._build_commandstr(command, argstr, extra_paths)

        # print the commandstr and return on a dryrun

        if self._trialargs['dryrun']:
            print(commandstr)
            sys.stdout.flush()
            return

        # 1. call self.stop(pidfilename)
        self.stop(pidfilename)

        # run the command
        pid, subproc = etce.utils.daemonize_command(commandstr,
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
                pidfile.write(str(subproc.pid+pidincrement))

        # 4. wait on subprocess
        subproc.wait()

        # 5. exit, do not return, because returning
        #    will cause any subsequent wrappers in this
        #    step to be rerun
        sys.exit(0)


    def run(self,
            command,
            argstr,
            stdout=None,
            stderr=None,
            pidfilename=None,
            genpidfile=True,
            pidincrement=0,
            extra_paths=[]):

        commandstr = self._build_commandstr(command, argstr, extra_paths)

        # print the commandstr and return on a dryrun
        if self._trialargs['dryrun']:
            print(commandstr)
            sys.stdout.flush()
            return

        self.stop(pidfilename)

        print(commandstr)
        sys.stdout.flush()

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
        sp = subprocess.Popen(shlex.split(commandstr), stdout=stdoutfd, stderr=stderrfd)

        # write the pid to pidfilename
        if genpidfile:
            with open(pidfilename, 'w') as pidfile:
                pidfile.write(str(sp.pid+pidincrement))

        # wait on subprocess
        sp.wait()


    def stop(self, pidfilename=None, signal=SIGQUIT, sudo=True):
        # use default pidfilename if None specified
        if pidfilename is None:
            pidfilename = self._default_pidfilename

        # if found a pid, kill the process and remove the file
        self._platform.kill(pidfilename, signal, sudo)


    def _build_commandstr(self, command, argstr, extra_paths):
        all_paths = os.environ['PATH'].split(':') + list(extra_paths)

        existing_paths = filter(os.path.isdir, all_paths)

        found_paths = []

        for existing_path in existing_paths:
            if command in os.listdir(existing_path):
                found_paths.append(existing_path)

        if not found_paths:
            raise WrapperError('Cannot find command "%s" in system paths {%s}. Quitting.' \
                               % (command, ','.join(all_paths)))

        commandstr = ' '.join([os.path.join(found_paths[0], command), argstr])

        # run with sudo if wrapper requested it
        if self._sudo:
            commandstr = 'sudo ' + commandstr

        return commandstr
