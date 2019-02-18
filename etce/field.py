#
# Copyright (c) 2013-2018 - Adjacent Link LLC, Bridgewater, New Jersey
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

import os.path
import string
import sys

from collections import OrderedDict

class FieldParseException(Exception):
    pass


class Field(object):
    '''
    '''
    def __init__(self, nodefile):
        if not os.path.exists(nodefile) or not os.path.isfile(nodefile):
            raise ValueError('Nodefile "%s" does not exist or is not a file.' % nodefile)

        self._nodefile = nodefile
        self._validnamechars = tuple(string.ascii_letters + \
                                     string.digits + \
                                     '._-')
        self._tree = OrderedDict()
        self._roots = []
        self._leaves = []

        try:
            self._parse(nodefile)

            self._tree = tuple([ (root,
                                  tuple(self._tree[root])) for root in self._roots ])
            allnodes = []
            for tree in self.tree():
                allnodes.append(tree[0])
                for leaf in tree[1]:
                    if leaf in allnodes:
                        continue
                    allnodes.append(leaf)
            self._allnodes = tuple(allnodes)
        except Exception as e:
            print >>sys.stderr, 'Failed to parse hostfile "%s" with error "%s". Quitting.' % (nodefile, e)
            exit(1)


    def nodefile(self):
        return self._nodefile

        
    def roots(self):
        return tuple(self._roots)


    def leaves(self):
        return tuple(self._leaves)


    def tree(self):
        return self._tree


    def allnodes(self):
        return self._allnodes


    def __str__(self):
        s = ''
        for tree in self.tree():
            s += tree[0] + ' '
            if len(tree[1]) > 0:
                s += '{\n'
                for leaf in tree[1]:
                    s += '  ' + leaf + '\n'
                s += '}\n'
            else:
                s += '\n'
        return s


    def _nexttoken(self, filedescriptor):
        nexttok = ''
        nextchar = None
        newlines = 0

        # read to the next token
        nextchar = filedescriptor.read(1)
        while len(nextchar) > 0:
            if not nextchar in string.whitespace:
                break
            if nextchar == '\n':
                newlines += 1
            nextchar = filedescriptor.read(1)

        # exit if end of file
        if len(nextchar) == 0:
            return newlines,nexttok

        # is the found char valid
        if not nextchar in self._validnamechars + ('{','}'): 
            raise FieldParseException('Impermissable node character %s' %
                                      nextchar)

        nexttok += nextchar
        if nexttok in '{}':
            return newlines,nexttok

        # we have something else
        nextchar = filedescriptor.read(1)
        while len(nextchar) > 0:
            if nextchar in '{}':
                # put the brace back for nexttime
                filedescriptor.seek(-1,1)
                return newlines,nexttok
            elif nextchar in string.whitespace:
                if nextchar == '\n':
                    newlines += 1
                return newlines,nexttok
            elif nextchar in self._validnamechars:
                nexttok += nextchar
            else: 
                raise FieldParseException('Impermissable node character %s' %
                                          nextchar)
            nextchar = filedescriptor.read(1)
            
        return newlines,nexttok
        

    def _parse(self, nodefile):
        with open(nodefile, 'r') as nf:
            currentroot = None
            atroot = True
            allnodes = []
            line = 0
            while True:
                newlines,tok = self._nexttoken(nf)
                line += newlines
                if atroot:
                    if len(tok) == 0:
                        break
                    elif tok == '{':
                        atroot = False
                    elif tok == '}':
                        raise FieldParseException(
                            'Unexpected "}" at line %s, %d' % (nodefile, line))
                    else:
                        if tok in allnodes:
                            raise FieldParseException(
                                'Node %s specified again at line %d' % (tok, line))
                        else:
                            allnodes.append(tok)
                            self._roots.append(tok)
                            currentroot = tok
                            self._tree[tok] = []
                else:
                    if len(tok) == 0:
                        raise FieldParseException(
                            'Unexpected end of file without matching "}"')
                        
                    elif tok == '{':
                        raise FieldParseException(
                            'Unexpected "{" at line %s, %d. Field depth cannot exceed one level' % (nodefile, line))
                    elif tok == '}':
                        currentroot = None
                        atroot = True
                    else:
                        # ok for current root to be a leaf of itself
                        if tok in allnodes:
                            if tok == currentroot:
                                if not tok in self._tree[currentroot]:
                                    self._tree[currentroot].append(tok)
                            else:
                                raise FieldParseException(
                                    'Node %s specified again at line %d' % (tok, line))
                        else:
                            allnodes.append(tok)
                            self._tree[currentroot].append(tok)

            # to get the list of leaf nodes, include root nodes
            # with no subtree
            for root,leaves in self._tree.items():
                if len(leaves) == 0:
                    self._leaves.append(root)
                self._leaves.extend(leaves)


def main():
    usagestr = '''
List the nodes in the ETCE field specified by HOSTFILE. 
An ETCE field consists of a tree of IP resolvable hostnames 
up to 2 levels deep.

Roots are interpreted to be nodes with an independent file
system; during tests, configuration is pushed to each root node.
Leaf nodes run applications during tests. A node may be both
a root and leaf node.

Example:

  server1 {
    node-001
    node-002
  }

  server2
  node-003

  server3 {
    server3
    node-004
  }

In this case there are 4 roots 
{ server1, server2 and node-003, server3 } and 6 leafs 
{ node-001, node-002, server2, node-003, server3, node-004 }.
'''

    import argparse

    parser = argparse.ArgumentParser( \
                prog='etce-list-hosts',
                description=usagestr,
                formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('--position', 
                        default='all',
                        help='''List the nodes at the specified tree,
                        position, one of { leaves, roots, all }.
                        Default: leaves.''')
    parser.add_argument('hostfile',
                        metavar='HOSTFILE',
                        help='''The ETCE Host file containing the 
                        node names from which the remote source 
                        directories are collected.''')

    args = parser.parse_args()

    if not os.path.isfile(args.hostfile):
        print >>sys.stderr,'HOSTFILE "%s" does not exist. Quitting.' % args.hostfile
        exit(1)

    f = Field(args.hostfile)

    if args.position.lower() == 'all':
        for node in f.allnodes():
            print node
    elif args.position.lower() == 'roots':
        for node in f.roots():
            print node
    elif args.position.lower() == 'leaves':
        for node in f.leaves():
            print node
    else:
        print 'Unknown position: %s' % args.position
        exit(1)


if __name__=='__main__':
    main()
