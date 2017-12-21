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
import re
import shutil
import sys
import traceback

import etce.utils
from etce.configfiledoc import ConfigFileDoc
from etce.manifestfiledoc import ManifestFileDoc
from etce.templateutils import format_file
from etce.templatefile import TemplateFile
from etce.templatedirectory import TemplateDirectory
from etce.testdirectory import TestDirectory
from etce.overlaychainfactory import OverlayChainFactory
from etce.overlaylistchainfactory import OverlayListChainFactory
from etce.config import ConfigDictionary

from lxml.etree import _Comment
from lxml.etree import DocumentInvalid

class Publisher(object):
    def __init__(self, test_directory):
        self._test_directory = test_directory

        manifest_filename_abs = os.path.join(self._test_directory,
                                             TestDirectory.MANIFESTFILENAME)

        self._manifestdoc = ManifestFileDoc(manifest_filename_abs)

        self._testname = self._manifestdoc.name()

        
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
        elif self._manifestdoc.base_directory():
            base_directory = os.path.join(self._test_directory, self._manifestdoc.base_directory())
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

                if subfile == TestDirectory.MANIFESTFILENAME:
                    self._manifestdoc.rewrite_without_basedir(dstfile)
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
        # in manifest file but is empty. Issue a warning, but move
        # it to the mergedirectory anyway.
        template_directory_names = self._manifestdoc.template_directory_names()
        
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


    def publish(self,
                publishdir,
                mergedir=None,
                absbasedir_override=None,
                runtimeoverlays={},
                extrafiles=[],
                overwrite_existing_publishdir=False,
                remove_temporary_mergedir=True):
        '''Publish the directory described by the testdirectory and
           its manifest.xml file to the destination directory.

            1. If the test defines a base directory, or if a mergedir
               is specified, merge the basedirectory and test directory
               to the mergedir.
            2. From the mergedirectory, copy all non-template files to
               the publish directory, maintaining the directory structure
               and filling in any template parameters.
            3. Instantiate template directories and files (if any) and
               write them to the publishdir.
        '''
        temporary_merge_location_generated = False
        
        if self._manifestdoc.base_directory():
            # If the test has a base directory
            # and no merge directory is specified, choose a temporary
            # location.
            if not mergedir:
                temporary_merge_location_generated = True

                mergedir = \
                    etce.utils.generate_tempfile_name(\
                        directory=ConfigDictionary().get('etce', 'WORK_DIRECTORY'),
                                                      prefix='template_')
        else:
            # otherwise, a merge is not required
            mergedir = self._test_directory


        # merge, if requested
        self.merge_with_base(mergedir, absbasedir_override, extrafiles)
       
        movefiles,      \
        templates,      \
        overlaydict = self._readmanifest(self._manifestdoc,
                                         publishdir,
                                         mergedir,
                                         runtimeoverlays)

        print
        print 'Publishing %s to %s' % (self._manifestdoc.name(), publishdir)

        if os.path.exists(publishdir):
            if overwrite_existing_publishdir:
                shutil.rmtree(publishdir)
            else:
                errstr = 'ERROR: destination dir "%s" already exists.' \
                         % publishdir
                raise ValueError(errstr)

        self._move(movefiles, overlaydict, mergedir, publishdir)

        self._instantiate_templates(templates, publishdir)

        if remove_temporary_mergedir and temporary_merge_location_generated:
            print 'Removing temporary merge directory "%s".' % mergedir
            shutil.rmtree(mergedir)

        print


    def _readmanifest(self, 
                      manifestdoc,
                      publishdir,
                      mergedir,
                      runtimeoverlays):
        overlaydict = \
            OverlayChainFactory(mergedir).make(
                manifestdoc.findall("./overlays/overlay"),
                manifestdoc.findall("./overlays/overlaycsv"))

        configdict = ConfigDictionary()

        for k,v in configdict.items('overlays'):
            overlaydict.update({ k:etce.utils.configstrtoval(v) })

        # env_overlays_allow names env variables permitted to
        # use as overlays
        env_overlays_allow = configdict.get('etce', 'ENV_OVERLAYS_ALLOW', '')

        env_overlays = {}

        if len(env_overlays_allow):
            for overlay in env_overlays_allow.split(':'):
                if overlay in os.environ:
                    env_overlays[overlay] = os.environ[overlay]

        overlaydict.update(env_overlays)

        for k,v in runtimeoverlays.items():
            overlaydict.update({ k:etce.utils.configstrtoval(v) })

        subfiles = self._get_subfiles(mergedir)

        templates = []

        templateselems = manifestdoc.findall('./templates')

        if len (templateselems) > 0:
            templateselem = templateselems[0]

            overlaylistelems = \
                manifestdoc.findall("./templates/overlaylist")

            nodeoverlaydict = \
                OverlayListChainFactory().make(overlaylistelems,
                                               manifestdoc.indices())

            # iterate over elem's children
            for elem in list(templateselem):
                # ignore comments
                if isinstance(elem, _Comment):
                    continue

                name = elem.attrib['name']

                if elem.tag == 'file':
                    templates.append(TemplateFile(mergedir,
                                                  publishdir,
                                                  elem, 
                                                  manifestdoc.indices(),
                                                  nodeoverlaydict, 
                                                  overlaydict))
                    # same template file might be use multiple times so
                    # check if previously removed
                    if name in subfiles:
                        subfiles.pop(subfiles.index(name))

                elif elem.tag == 'directory':
                    template_directory = TemplateDirectory(mergedir,
                                                           publishdir,
                                                           elem, 
                                                           manifestdoc.indices(),
                                                           nodeoverlaydict,
                                                           overlaydict)
                    
                    templates.append(template_directory)

                    self._prunedir(subfiles, template_directory.template_subdir)
            
        self._manifestdoc = manifestdoc

        return (subfiles,templates,overlaydict)


    def _move(self, srcfiles, overlaydict, mergedir, publishdir):
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

            overlays = {}

            # first_level_entry is a nodename if it is a directory
            if os.path.isdir(os.path.join(mergedir, first_level_entry)):
                overlays = { 'etce_log_path':os.path.join(publishdir, first_level_entry),
                             'etce_hostname':first_level_entry }

            overlays.update(overlaydict)

            fulldstfile = os.path.join(publishdir, relname)

            dstfiledir = os.path.dirname(fulldstfile)

            if not os.path.exists(dstfiledir):
                os.makedirs(dstfiledir)

            if relname == TestDirectory.MANIFESTFILENAME:
                self._manifestdoc.rewrite_without_basedir(fulldstfile)
            elif relname in skipfiles:
                shutil.copyfile(fullsrcfile, fulldstfile)
            else:
                format_file(fullsrcfile, fulldstfile, overlays)


    def _instantiate_templates(self, templates, publishdir):
        for template in templates:
            template.instantiate(publishdir)


    def _get_subfiles(self, directory):
        files = []

        for dirname,dirnames,filenames in os.walk(directory):
            for filename in filenames:
                fullpath = os.path.join(dirname, filename)

                relpath = os.path.relpath(fullpath, directory)

                files.append(relpath)

        return files


    def _prunedir(self, subfiles, subdir):
        # remove any member of subfiles whose key is contained under srcdir
        rmfiles = []

        for subfile in subfiles:
            if subfile.startswith(subdir + '/'):
                rmfiles.append(subfile)

        for rmfile in rmfiles:
            subfiles.pop(subfiles.index(rmfile))



def add_publish_arguments(parser):
    work_directory = ConfigDictionary().get('etce', 'WORK_DIRECTORY')

    parser.add_argument('--basedir',
                        action='store',
                        default=None,
                        help='''Specify an absolute path to test base 
                        directory, overridding the (optional) base
                        directory defined in the test manifest.xml file.
                        default: None''')
    parser.add_argument('--mergedirectory',
                        action='store',
                        default=None,
                        help='''An intermediate directory to store a version 
                        of the test directory merged with its base. If not
                        specified, a directory name is generated and placed in
                        the ETCE working directory (%s).''' % work_directory)
    parser.add_argument('--overlayfile',
                        action='store',
                        default=None,
                        help='''File name containing TAG=VALUE pairs,
                        one per line, to use as tag overlays
                        to use for publishing. These tag values 
                        override those specified in the local etce.conf file. 
                        default: None''')
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
        
    runtimeoverlays = {}
    if args.overlayfile is not None:
        if not os.path.isfile(args.overlayfile):
            print >>sys.stderr, 'overlayfile "%s" doesn\'t exist. Quitting' % args.overlayfile
            exit(1)
        for line in open(args.overlayfile,'r'):
            line = line.strip()
            if len(line) > 0:
                n,v = line.split('=')
                runtimeoverlays[n] = v

    try:
        merge_directory = args.mergedirectory

        if not merge_directory:
            tmp_directory = os.path.join(ConfigDictionary().get('etce', 'WORK_DIRECTORY'),
                                         'tmp')

            if not os.path.exists(tmp_directory):
                os.makedirs(tmp_directory)

            merge_directory = \
                etce.utils.generate_tempfile_name(directory=tmp_directory,
                                                  prefix='template_')

        publisher = Publisher(args.testdirectory)
        
        publisher.publish(args.outdirectory,
                          mergedir=merge_directory,
                          runtimeoverlays=runtimeoverlays,
                          absbasedir_override=args.basedir)

    except DocumentInvalid as ie:
        print >>sys.stderr, ie
    except KeyError as ke:
        print >>sys.stderr, 'No value specified for key %s. Quitting. ' % ke
    except ValueError as ve:
        print >>sys.stderr, ve
