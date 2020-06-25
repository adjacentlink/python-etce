#
# Copyright (c) 2013-2019 - Adjacent Link LLC, Bridgewater, New Jersey
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
from collections import defaultdict
import os
import re
import shutil
import sys
import traceback

import etce.utils
from etce.chainmap import ChainMap
from etce.testfiledoc import TestFileDoc
from etce.testdirectoryentry import TestDirectoryEntry
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
            print('Merge directory "%s" already exists, skipping merge.' % mergedir,
                  file=sys.stderr)
            return

        srcdirs = [self._test_directory]

        # choose the base directory for the merge
        base_directory = None

        if absbasedir_override:
            base_directory = absbasedir_override
        elif self._testdoc.has_base_directory:
            # test.xml file base directory is permitted to be relative or absolute
            if self._testdoc.base_directory[0] == os.path.sep:
                base_directory = self._testdoc.base_directory
            else:
                base_directory = os.path.join(self._test_directory, self._testdoc.base_directory)
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
                    self._testdoc.rewrite_without_base_directory(dstfile)
                else:
                    shutil.copyfile(srcfile, dstfile)

        self._move_extra_files(extrafiles, mergedir)

        # check for corner case where a template directory is specified
        # in test file but is empty. Issue a warning, but move
        # it to the mergedirectory anyway.
        self._warn_on_empty_template_directory(srcdirs, mergedir)


    def _move_extra_files(self, extrafiles, dstdir):
        for srcfile,dstfile in extrafiles:
            dstfile = os.path.join(dstdir, dstfile)

            dirname = os.path.dirname(dstfile)

            if not os.path.exists(dirname):
                os.makedirs(dirname)

            shutil.copyfile(srcfile, dstfile)


    def _warn_on_empty_template_directory(self, srcdirs, mergedir):
        template_directory_names = self._testdoc.template_directory_names

        nonexistent_template_directories = set([])

        empty_template_directories = set([])

        for template_directory_name in template_directory_names:
            empty = True
            exists = False

            for srcdir in srcdirs:
                dir_to_test = os.path.join(srcdir, template_directory_name)

                if not os.path.exists(dir_to_test):
                    continue

                exists = True

                if os.listdir(dir_to_test):
                    empty = False

            if not exists:
                nonexistent_template_directories.update([template_directory_name])

            if empty:
                empty_template_directories.update([template_directory_name])

        if nonexistent_template_directories:
            errstr = 'Missing template directories {%s}. Quitting.' % \
                     ', '.join(list(nonexistent_template_directories))
            raise ValueError(errstr)

        for  empty_template_directory in empty_template_directories:
            print('Warning: template directory "%s" is empty.' \
                  % empty_template_directory,
                  file=sys.stderr)
            os.makedirs(os.path.join(mergedir, empty_template_directory))


    def publish(self,
                publishdir,
                logdir=None,
                absbasedir_override=None,
                runtime_overlays={},
                extrafiles=[],
                overwrite_existing_publishdir=False):
        '''Publish the directory described by the testdirectory and
           its test.xml file to the destination directory.

            1. First instantiate template directories and files named by test.xml.
            2. Move other files from the test directory to the destination
               (filling in overlays).
            3. Move extra files, specified by the caller, to the destination.

            publish combines the files from the test directory and the (optional)
            base directory to the destination.
        '''
        srcdirs = [ self._test_directory ]

        if absbasedir_override:
            srcdirs.insert(0, absbasedir_override)
        elif self._testdoc.has_base_directory:
            # test.xml file base directory is permitted to be relative or absolute
            if self._testdoc.base_directory[0] == os.path.sep:
                srcdirs.insert(0, self._testdoc.base_directory)
            else:
                srcdirs.insert(0, os.path.join(self._test_directory, self._testdoc.base_directory))
            
        templates = self._testdoc.templates

        subdirectory_map = {}

        for srcdir in srcdirs:
            subdirectory_map.update(self._build_subdirectory_map(srcdir))

        subdirectory_map = self._prune_unused_template_directories(subdirectory_map)
        
        etce_config_overlays, env_overlays = self._get_host_and_env_overlays()

        testfile_global_overlays = self._testdoc.global_overlays(subdirectory_map)

        print()
        print('Publishing %s to %s' % (self._testdoc.name, publishdir))

        if os.path.exists(publishdir):
            if overwrite_existing_publishdir:
                shutil.rmtree(publishdir)
            else:
                errstr = 'ERROR: destination dir "%s" already exists.' \
                         % publishdir
                raise ValueError(errstr)

        os.makedirs(publishdir)

        # move template files
        self._instantiate_templates(templates,
                                    runtime_overlays,
                                    env_overlays,
                                    etce_config_overlays,
                                    publishdir,
                                    subdirectory_map,
                                    logdir)

        # and then the remaining files
        self._move(subdirectory_map,
                   runtime_overlays,
                   env_overlays,
                   testfile_global_overlays,
                   etce_config_overlays,
                   publishdir,
                   logdir)

        self._move_extra_files(extrafiles, publishdir)


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
    

    def _prune_unused_template_directories(self, subdirectory_map):
        directory_templates_used_by_test = self._testdoc.template_directory_names

        all_template_directory_keys = set([ entry.root_sub_entry for entry in subdirectory_map.values()
                                            if entry.template_directory_member ])


        directory_templates_not_used_by_test = \
            all_template_directory_keys.difference(directory_templates_used_by_test)

        rmpaths = []
        
        for unused in directory_templates_not_used_by_test:
            for subpath in subdirectory_map:
                if subpath.startswith(unused + '/'):
                    rmpaths.append(subpath)

        map(subdirectory_map.pop, rmpaths)

        return subdirectory_map


    def _move(self,
              subdirectory_map,
              runtime_overlays,
              env_overlays,
              testfile_global_overlays,
              etce_config_overlays,
              publishdir,
              logdir):
        skipfiles = (TestDirectory.CONFIGFILENAME,
                     TestDirectory.HOSTFILENAME)

        omitdirs = (TestDirectory.DOCSUBDIRNAME,)

        for relname,entry in subdirectory_map.items():
            if entry.root_sub_entry in omitdirs:
                continue

            # full path to the first level entry
            first_level_entry_abs = entry.root_sub_entry_absolute

            reserved_overlays = {}

            # first_level_entry is a nodename if it is a directory
            if entry.root_sub_entry_is_dir:
                reserved_overlays = { 'etce_hostname':entry.root_sub_entry }

                if logdir:
                    reserved_overlays['etce_log_path'] = os.path.join(logdir, entry.root_sub_entry)

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
                self._testdoc.rewrite_without_overlays_and_templates(fulldstfile)
            elif relname in skipfiles:
                shutil.copyfile(entry.full_name, fulldstfile)
            else:
                format_file(entry.full_name, fulldstfile, overlays)


    def _instantiate_templates(self,
                               templates,
                               runtime_overlays,
                               env_overlays,
                               etce_config_overlays,
                               publishdir,
                               subdirectory_map,
                               logdir):
        template_file_keys = defaultdict(lambda: 0)

        for template in templates:
            template_file_keys[template.template_file_key] += 1

        for template in templates:
            template.instantiate(subdirectory_map,
                                 publishdir,
                                 logdir,
                                 runtime_overlays,
                                 env_overlays,
                                 etce_config_overlays)

            # prune template file that have been exhausted
            template_file_keys[template.template_file_key] -= 1

            if not template_file_keys[template.template_file_key]:
                subdirectory_map = template.prune(subdirectory_map)


    def _get_subfiles(self, directory):
        files = []

        for dirname,dirnames,filenames in os.walk(directory):
            for filename in filenames:
                fullpath = os.path.join(dirname, filename)

                relpath = os.path.relpath(fullpath, directory)

                files.append(relpath)

        return files


    def _build_subdirectory_map(self, directory):
        subfiles = {}

        for dirname,dirnames,filenames in os.walk(directory):
            for filename in filenames:
                fullpath = os.path.join(dirname, filename)

                relpath = os.path.relpath(fullpath, directory)

                subfiles[relpath] = TestDirectoryEntry(directory, relpath)

        return subfiles

    
def add_publish_arguments(parser):
    parser.add_argument('--basedirectory',
                        default=None,
                        help='''Specify a path to a test base 
                        directory, overridding the (optional) value
                        defined in the test test.xml file. The value
                        may be an absolute path or a relative path 
                        to the current working directory. 
                        default: None''')
    parser.add_argument('--logdirectory',
                        default=None,
                        help='''The ETCE reserved overlay 'etce_log_path'
                        names a location for wrappers to write output files. 
                        When running a test, etce_log_path is automatically
                        derived using the etce.conf WORK_DIRECTORY value.
                        Use the logdirectory argument to pass a location
                        for output files when publishing a test outside
                        of running it. Default: None.''')
    parser.add_argument('--overlayfile',
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
        print()
        print('testdirectory "%s" does not exist. Quitting.' % args.testdirectory)
        print()
        exit(1)

    if os.path.exists(args.outdirectory):
        print()
        print('Destination "%s" already exists. Quitting.' % args.outdirectory)
        print()
        exit(2)

    # if basedirectory is a relative path, make it absolute with respect
    # to the current working directory
    if args.basedirectory and not args.basedirectory[0] == os.path.sep:
        args.basedirectory = os.path.join(os.getcwd(), args.basedirectory)
        
    runtime_overlays = {}
    if args.overlayfile is not None:
        if not os.path.isfile(args.overlayfile):
            print('overlayfile "%s" doesn\'t exist. Quitting' % args.overlayfile,
                  file=sys.stderr)
            exit(1)
        for line in open(args.overlayfile,'r'):
            line = line.strip()
            if len(line) > 0:
                n,v = line.split('=')
                runtime_overlays[n] = v

    try:
        publisher = Publisher(args.testdirectory)
        
        publisher.publish(publishdir=args.outdirectory,
                          logdir=args.logdirectory,
                          runtime_overlays=runtime_overlays,
                          absbasedir_override=args.basedirectory)

    except Exception as e:
        print(e, file=sys.stderr)
        if args.verbose:
            print(traceback.format_exc())
