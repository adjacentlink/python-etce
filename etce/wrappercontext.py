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


from etce.argregistrar import ArgRegistrar


class WrapperContext(ArgRegistrar):
    ''' WrapperContext groups various objects and data, useful 
        to wrappers, into a single interface. It makes two
        groups of parameters available to the wrapper - "args"
        and "overlays".

        args are parameter values passed to wrappers on a test
        by test basis. They are set in the test steps.xml file,
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
    def __init__(self, impl):
        self._impl = impl


    def register_argument(self, argname, defaultval, description):
        self._impl.register_argument(argname, defaultval, description)


    def register_overlay(self, overlayname, defaultval, description):
        self._impl.register_overlay(overlayname, defaultval, description)


    def register_infile_name(self, name):
        self._impl.register_infile_name(name)


    def register_outfile_name(self, name):
        self._impl.register_outfile_name(name)


    def store(self, namevaldict):
        self._impl.store(namevaldict)


    @property
    def platform(self):
        return self._impl.platform


    @property
    def args(self):
        return self._impl.args


    @property
    def overlays(self):
        return self._impl.overlays


    @property
    def default_pidfilename(self):
        return self._impl.default_pidfilename
    

    def daemonize(self,
                  commandstr,
                  stdout=None,
                  stderr=None,
                  pidfilename=None,
                  genpidfile=True,
                  pidincrement=0,
                  starttime=None):

        self._impl.daemonize(commandstr,
                             stdout,
                             stderr,
                             pidfilename,
                             genpidfile,
                             pidincrement,
                             starttime)


    def run(self,
            commandstr,
            stdout=None,
            stderr=None,
            pidfilename=None,
            genpidfile=True,
            pidincrement=0):

        self._impl.run(commandstr,
                       stdout,
                       stderr,
                       pidfilename,
                       genpidfile,
                       pidincrement)


    def stop(self, pidfilename=None):
        self._impl.stop(pidfilename)
