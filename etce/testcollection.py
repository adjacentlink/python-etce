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

import os

from etce.testdirectory import TestDirectory
from etce.testcollectionerror import TestCollectionError


class TestCollectionIterator(object):
    def __init__(self, wrapped):
        self.wrapped = wrapped
        self.index = 0
        
    def next(self):
        return self.__next__()

    def __next__(self):
        if self.index >= len(self.wrapped):
            raise StopIteration
        else:
            item = self.wrapped[self.index]
            self.index += 1
            return item


class TestCollection(object):
    '''TestCollection represents a sequence of tests. It is iterable
    and returns an instance of a Test object on each iteration. Test
    collections may be build in different ways. Two ways that are forseen,
    building a TestCollection by parsing a subdirectory tree of test files,
    building a TestCollection by a generator.'''
    
    def __init__(self):
        self._tests = {}


    def adddirectory(self, testroot, basedir_override):
        if not os.path.exists(testroot):
            err = 'specified test directory, %s, does not exist' % \
                                 testroot
            raise ValueError(err)
        if not os.path.isdir(testroot):
            err = 'specified test directory, %s, is not a directory' % testroot
            raise ValueError(err)

        # maintain a mapping of test name to its root location
        self._parsetestroot(testroot, basedir_override)


    def numnodes(self):
        return len(self.nodenames())


    def participant_nodes(self, allocatednodelist):
        allocated = set(allocatednodelist)

        found = self._nodeset()

        missing = sorted(list(found.difference(allocated)))

        if missing:
            message = 'Error: test participant node(s) "%s" not allocated '\
                      'in nodefile. Quitting.' \
                      % (', '.join(sorted(list(missing))))

            raise TestCollectionError(message)

        return sorted(list(found))


    def _nodeset(self):
        nodeset = set([])

        for test in self:
            nodeset.update(test.determine_nodenames())

        return nodeset


    def __iter__(self):
        return TestCollectionIterator([ self._tests[k] for k in sorted(self._tests)])


    def __len__(self):
        return len(self._tests)


    def __str__(self):
        s = 'TestCollection:\n'
        for k in sorted(self._tests):
            s += '\t%s\n' % k
        return s


    def _parsetestroot(self, testroot, basedir_override):
        for dirpath,dirnames,filenames in os.walk(testroot):
            if self._istestdirectory(filenames):
                test = TestDirectory(dirpath, basedir_override)
                if test.name() in self._tests:
                    err = '''ERROR: tests must have unique names. Test at 
                             %s 
                             and 
                             %s 
                             are both named %s''' % (self._tests[test.name()].location(),
                                                     test.location(),
                                                     test.name())
                    raise ValueError(err)
                else:
                    self._tests[test.name()] = test


    def _istestdirectory(self, filenames):
        return TestDirectory.MANIFESTFILENAME in filenames



def add_list_arguments(parser):
    parser.add_argument('-v',
                        '--verbose',
                        action='store_true',
                        default=False,
                        help='Print verbose test information.')
    parser.add_argument('testrootdir',
                        metavar='TESTROOT',
                        help='''The root directory of the tests to print.
                        All test directories contained under the root directory
                        are displayed.''')
    parser.add_argument('prefix',
                        metavar='PREFIX',
                        nargs='?',
                        default='',
                        help='''Limit output to tests that start with the specified
                        prefix.''')


def list_tests(args):
    import sys
    from etce.xmldocerror import XMLDocError

    collection = TestCollection()

    try:
        collection.adddirectory(args.testrootdir, None)
    except XMLDocError as xmle:
        print >>sys.stderr,xmle.message
        exit(1)

    # on an exact match, just print the single test
    if args.prefix in collection:
        if args.verbose:
            print testdir
        else:
            print testdir.name()
    else:
        for testdir in collection:
            if testdir.name().startswith(args.prefix):
                if args.verbose:
                    print testdir
                else:
                    print testdir.name()
