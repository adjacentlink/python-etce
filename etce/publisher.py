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

import os
import re
import shutil
import sys
import traceback

import etce.utils
from etce.chainmap import ChainMap
from etce.testfiledoc import TestFileDoc
from etce.templateutils import format_file
from etce.testdirectory import TestDirectory
from etce.config import ConfigDictionary

from lxml.etree import DocumentInvalid

class Publisher(object):
    def __init__(self, test_directory):
        self._test_directory = test_directory

        test_filename_abs = os.path.join(self._test_directory,
                                         TestDirectory.TESTFILENAME)

        self._testdoc = TestFileDoc(test_filename_abs)

        self._config = ConfigDictionary()


    def merge_with_base(self, mergedir, absbasedir_override=None, extrafiles=[]):
        '''
        Merge the files from the basedirectory (if there is one), the
        test directory and the extrafiles to the merge directory.
        '''
        if not mergedir:
            raise ValueError('A merge directory must be specified in merging ' \
                             'a test directory with its base directory. ' \
                             'Quitting.')

        # Quit if the merge directory already exists. This also handles the case
        # where mergedir is the same as the self._test_directory
        if os.path.exists(mergedir):
            print >>sys.stderr,'Merge directory "%s" already exists, skipping merge.' % mergedir
            return

        srcdirs = [self._test_directory]

        # choose the base directory for the merge
        base_directory = None

        if absbasedir_override:
            base_directory = absbasedir_override
        elif self._testdoc.base_directory():
            base_directory = os.path.join(self._test_directory, self._testdoc.base_directory())
        else:
            # merge devolves to copying the test directory to merge directory
            pass

        # check that the base directory exists
        if base_directory:
            if os.path.isdir(base_directory):
                srcdirs.insert(0, base_directory)
            else:
                errstr = 'In merging test directory "%s", cannot find base directory "%s". Quitting.' % \
                         (self._test_directory, base_directory)
                raise ValueError(errstr)

        # move the files in basedirectory, then test directory
        for srcdir in srcdirs:
            if srcdir[-1] == '/':
                srcdir = srcdir[:-1]

            subfiles = self._get_subfiles(srcdir)

            for subfile in subfiles:
                srcfile = os.path.join(srcdir, subfile)

                dstfile = os.path.join(mergedir, subfile)

                dirname = os.path.dirname(dstfile)

                if not os.path.exists(dirname):
                    os.makedirs(dirname)

                if subfile == TestDirectory.TESTFILENAME:
                    self._testdoc.rewrite_without_basedir(dstfile)
                else:
                    shutil.copyfile(srcfile, dstfile)

        # move the extra files
        for srcfile,dstfile in extrafiles:
            dstfile = os.path.join(mergedir, dstfile)
            
            dirname = os.path.dirname(dstfile)
            
            if not os.path.exists(dirname):
                os.makedirs(dirname)
                
            shutil.copyfile(srcfile, dstfile)

        # check for corner case where a template directory is specified
        # in test file but is empty. Issue a warning, but move
        # it to the mergedirectory anyway.
        self._warn_on_empty_template_directory(srcdirs)


    def _warn_on_empty_template_directory(self, srcdirs):
        template_directory_names = self._testdoc.template_directory_names()
        
        empty_template_directories = set([])

        for template_directory_name in template_directory_names:
            empty = True

            for srcdir in srcdirs:
                dir_to_test = os.path.join(srcdir, template_directory_name)

                if not os.path.exists(dir_to_test):
                    continue

                if os.listdir(dir_to_test):
                    empty = False

            if empty:
                empty_template_directories.update([template_directory_name])

        for  empty_template_directory in empty_template_directories:
            print >>sys.stderr,'Warning: template directory "%s" is empty.' \
                % empty_template_directory
            os.makedirs(os.path.join(mergedir, empty_template_directory))


    def merge_with_base_and_publish(self,
                                    publishdir,
                                    mergedir=None,
                                    logdir=None,
                                    absbasedir_override=None,
                                    runtime_overlays={},
                                    extrafiles=[],
                                    overwrite_existing_publishdir=False,
                                    preserve_temporary_mergedir=False):
        '''Publish the directory described by the testdirectory and
           its test.xml file to the destination directory.

            1. If the test defines a base directory, or if a mergedir
               is specified, merge the basedirectory and test directory
               to the mergedir.
            2. From the mergedirectory, copy all non-template files to
               the publish directory, maintaining the directory structure
               and filling in any template overlays.
            3. Instantiate template directories and files (if any) and
               write them to the publishdir.
        '''
        temporary_merge_location_generated = False

        if self._testdoc.base_directory():
            # If the test has a base directory
            # and no merge directory is specified, choose a temporary
            # location.
            if not mergedir:
                temporary_merge_location_generated = True

                workdir = self._config.get('etce', 'WORK_DIRECTORY')

                mergedir = \
                    etce.utils.generate_tempfile_name(os.path.join(workdir,'tmp'),
                                                      prefix='template_')
        else:
            # otherwise, a merge is not required
            mergedir = self._test_directory


        # merge, if requested
        self.merge_with_base(mergedir, absbasedir_override, extrafiles)

        movefiles,templates = self._get_templates(mergedir)
        
        etce_config_overlays, env_overlays = self._get_host_and_env_overlays()

        testfile_global_overlays = self._testdoc.global_overlays(mergedir)

        print
        print 'Publishing %s to %s' % (self._testdoc.name(), publishdir)

        if os.path.exists(publishdir):
            if overwrite_existing_publishdir:
                shutil.rmtree(publishdir)
            else:
                errstr = 'ERROR: destination dir "%s" already exists.' \
                         % publishdir
                raise ValueError(errstr)


        # move non-template files, filling in overlays
        self._move(movefiles,
                   runtime_overlays,
                   env_overlays,
                   testfile_global_overlays,
                   etce_config_overlays,
                   publishdir,
                   mergedir,
                   logdir)

        self._instantiate_templates(templates,
                                    runtime_overlays,
                                    env_overlays,
                                    etce_config_overlays,
                                    publishdir,
                                    mergedir,
                                    logdir)

        if temporary_merge_location_generated:
            if preserve_temporary_mergedir:
                print 'Preserving temporary merge directory "%s".' % mergedir
            else:
                print 'Removing temporary merge directory "%s".' % mergedir
                shutil.rmtree(mergedir)

        print


    def _get_host_and_env_overlays(self):
        # Assemble overlays from
        # 1. etce.conf
        etce_config_overlays = {}
        
        for k,v in self._config.items('overlays'):
            etce_config_overlays[k] = etce.utils.configstrtoval(v)

        # 3. overlay set by environment variables, identified by
        #    etce.conf ENV_OVERLAYS_ALLOW
        env_overlays = {}

        env_overlays_allow = self._config.get('etce', 'ENV_OVERLAYS_ALLOW', '')

        if len(env_overlays_allow):
            for overlay in env_overlays_allow.split(':'):
                if overlay in os.environ:
                    env_overlays[overlay] = etce.utils.configstrtoval(os.environ[overlay])

        return (etce_config_overlays, env_overlays)
    

    def _get_templates(self, mergedir):
        subfiles = self._get_subfiles(mergedir)

        templates = self._testdoc.templates()

        for template in templates:
            template.prune(subfiles)

        subfiles = self._prune_unused_template_directories(mergedir, subfiles)

        return (subfiles,templates)


    def _prune_unused_template_directories(self, mergedir, subfiles):
        directory_templates_used_by_test = self._testdoc.template_directory_names()
        
        suffix = self._config.get('etce', 'TEMPLATE_SUFFIX')

        all_template_directories = \
            set([ d for d in os.listdir(mergedir) if
                  os.path.isdir(os.path.join(mergedir,d)) and
                  d.split('.')[-1] == suffix ])
        
        directory_templates_not_used_by_test = \
            all_template_directories.difference(directory_templates_used_by_test)
        
        rmfiles = []
        
        for unused in directory_templates_not_used_by_test:
            for subfile in subfiles:
                if subfile.startswith(unused + '/'):
                    rmfiles.append(subfile)

        for rmfile in rmfiles:
            subfiles.pop(subfiles.index(rmfile))

        return subfiles

        
    def _move(self,
              srcfiles,
              runtime_overlays,
              env_overlays,
              testfile_global_overlays,
              etce_config_overlays,
              publishdir,
              mergedir,
              logdir):
        # copy non-template files from testdir to publishdir
        os.makedirs(publishdir)

        skipfiles = (TestDirectory.CONFIGFILENAME,
                     TestDirectory.HOSTFILENAME)

        omitdirs = (TestDirectory.DOCSUBDIRNAME,)

        for relname in srcfiles:
            first_level_entry = relname.split('/')[0]

            if first_level_entry in omitdirs:
                continue

            fullsrcfile = os.path.join(mergedir, relname)

            reserved_overlays = {}

            # first_level_entry is a nodename if it is a directory
            if os.path.isdir(os.path.join(mergedir, first_level_entry)):
                reserved_overlays = { 'etce_log_path':os.path.join(publishdir, first_level_entry),
                                      'etce_hostname':first_level_entry }

            # for non-template file, overlays maps are searched in precedence:
            #
            # 1. reserved overlays
            # 2. runtime overlays (passed in by user or calling function)
            # 3. overlays set by environment variable
            # 4. overlays set in the test.xml file that apply to all files (at
            #    the top level)
            # 5. overlays set in the etce.conf "overlays" section - default
            #    values
            overlays = ChainMap(reserved_overlays,
                                runtime_overlays,
                                env_overlays,
                                testfile_global_overlays,
                                etce_config_overlays)   

            fulldstfile = os.path.join(publishdir, relname)

            dstfiledir = os.path.dirname(fulldstfile)

            if not os.path.exists(dstfiledir):
                os.makedirs(dstfiledir)

            if relname == TestDirectory.TESTFILENAME:
                self._testdoc.rewrite_without_basedir(fulldstfile)
            elif relname in skipfiles:
                shutil.copyfile(fullsrcfile, fulldstfile)
            else:
                format_file(fullsrcfile, fulldstfile, overlays)


    def _instantiate_templates(self,
                               templates,
                               runtime_overlays,
                               env_overlays,
                               etce_config_overlays,
                               publishdir,
                               mergedir,
                               logdir):
        for template in templates:
            template.instantiate(mergedir,
                                 publishdir,
                                 logdir,
                                 runtime_overlays,
                                 env_overlays,
                                 etce_config_overlays)


    def _get_subfiles(self, directory):
        files = []

        for dirname,dirnames,filenames in os.walk(directory):
            for filename in filenames:
                fullpath = os.path.join(dirname, filename)

                relpath = os.path.relpath(fullpath, directory)

                files.append(relpath)

        return files


def add_publish_arguments(parser):
    work_directory = ConfigDictionary().get('etce', 'WORK_DIRECTORY')

    parser.add_argument('--basedir',
                        action='store',
                        default=None,
                        help='''Specify an absolute path to test base 
                        directory, overridding the (optional) base
                        directory defined in the test test.xml file.
                        default: None''')
    parser.add_argument('--nocleanup',
                        action='store_true',
                        default=False,
                        help='''If an intermediate merge step to a temporary directory
                        is performed (see mergedirectory), the preserve the merge directory.
                        The default is to remove it.''')
    parser.add_argument('--mergedirectory',
                        action='store',
                        default=None,
                        help='''An intermediate directory to merge the TESTDIRECTORY
                        with its optional base directory. If the test's test.xml file
                        does not specify a base directory then the merge step is
                        skipped. A temporary directory in the ETCE working directory
                        (%s) is generated if no argument is specified.''' % work_directory)
    parser.add_argument('--overlayfile',
                        action='store',
                        default=None,
                        help='''File name containing NAME=VALUE pairs,
                        one per line, to use as overlays
                        for publishing. These overlay values 
                        override those specified in the local etce.conf file. 
                        default: None''')
    parser.add_argument('--verbose',
                        default=False,
                        action='store_true',
                        help='Print verbose information on error.')
    parser.add_argument('testdirectory',
                        metavar='TESTDIRECTORY',
                        action='store',
                        help='A valid ETCE Test Directory.')
    parser.add_argument('outdirectory',
                        metavar='OUTDIRECTORY',
                        action='store',
                        help='The output directory to place the built Test Directory.')


def publish_test(args):
    import sys

    if not os.path.exists(args.testdirectory):
        print
        print 'testdirectory "%s" does not exist. Quitting.' % args.testdirectory
        print
        exit(1)

    if os.path.exists(args.outdirectory):
        print
        print 'Destination "%s" already exists. Quitting.' % args.outdirectory
        print
        exit(2)

    # make sure a specified basedir is an absolute path
    if not args.basedir is None:
        if not args.basedir[0] == '/':
            message = 'basedir "%s" must be an absolute path. Quitting' % \
                      args.basedir
            print >>sys.stderr,message
            exit(1)
        
    runtime_overlays = {}
    if args.overlayfile is not None:
        if not os.path.isfile(args.overlayfile):
            print >>sys.stderr, 'overlayfile "%s" doesn\'t exist. Quitting' % args.overlayfile
            exit(1)
        for line in open(args.overlayfile,'r'):
            line = line.strip()
            if len(line) > 0:
                n,v = line.split('=')
                runtime_overlays[n] = v

    try:
        publisher = Publisher(args.testdirectory)
        
        publisher.merge_with_base_and_publish(args.outdirectory,
                                              args.mergedirectory,
                                              runtime_overlays=runtime_overlays,
                                              absbasedir_override=args.basedir,
                                              preserve_temporary_mergedir=args.nocleanup)

    except Exception as e:
        print >>sys.stderr, e
        if args.verbose:
            print traceback.format_exc()
