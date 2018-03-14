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


class Wrapper:
    '''
    The common base class for all ETCE Wrappers.
    '''
    def register(self, registrar):
        ''' 
        Optional method for registering:

         1. The name of the input file whose presence triggers the wrapper
            to run the wrapped application.

         2. The name of any output file created by the wrapper. This is a 
            convenience method allowing the context builds an absolute 
            filename to the common directory where test artifacts are stored.

         3. Arguments accepted by the wrapper for customizing execution - 
            typically a subset of the wrapped application's command line
            arguments. The exposed arguments can be set at runtime.
        '''
        pass


    def prerun(self, ctx):
        '''
        Optional method, called just before *run* to test or enforce wrapper 
        preconditions (if any) for running. The wrapper should throw an 
        PreconditionError when a precondition fails. 
        '''
        pass
        
        
    def run(self, ctx):
        '''
        Required method called to start the wrapped application.
        '''
        raise NotImplementedError('Wrapper.run')


    def postrun(self, ctx):
        '''
        Optional method, called just after *run* to test or enforce wrapper
        postconditions (if any) for running. The wrapper should throw an 
        PostconditionError when a postcondition fails. 
        '''
        pass


    def stop(self, ctx):
        '''
        Required method called to stop the wrapped application.
        '''
        raise NotImplementedError('Wrapper.stop')
