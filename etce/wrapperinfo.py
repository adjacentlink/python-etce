#
# Copyright (c) 2015-2017 - Adjacent Link LLC, Bridgewater, New Jersey
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


from etce.wrapperloader import WrapperLoader
from etce.argregistrar import ArgRegistrar


class WrapperInfoPrinter(ArgRegistrar):
    def __init__(self, wrapperpath, description, ignore_sudo):
        self._wrapperpath = wrapperpath
        self._description = description
        self._args = []
        self._infile_name = None
        self._outfile_name = None
        self._ignore_sudo = ignore_sudo
        self._sudo = False

    # register a test argument
    def register_argument(self, argname, defaultval, description):
        self._args.append((argname, defaultval, description))

    # register the file prefix expected for input files
    def register_infile_name(self, name):
        self._infile_name = name

    # register the output file outfile_name produced
    def register_outfile_name(self, name):
        self._outfile_name = name

    # register the output file outfile_name produced
    def run_with_sudo(self):
        self._sudo = True

    def __str__(self):
        s = ''
        s += 'path:\n'
        s += '\t%s\n' % self._wrapperpath
        s += 'description:\n'
        s += '\t%s\n' % str(self._description)
        s += 'input file name:\n'
        s += '\t%s\n' % str(self._infile_name)
        s += 'output file name:\n'
        s += '\t%s\n' % str(self._outfile_name)
        if not self._ignore_sudo:
            s += 'run with sudo:\n'
            s += '\t%s\n' % str(self._sudo)
        if len(self._args) > 0:
            s += 'arguments:\n'
            for argname,defaultval,description in sorted(self._args):
                s += '\t%s\n' % argname
                s += '\t\t%s\n' % description
                s += '\t\tdefault: %s\n' % str(defaultval)
        return s
