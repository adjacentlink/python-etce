#
# Copyright (c) 2022 - Adjacent Link LLC, Bridgewater, New Jersey
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
from etce.config import ConfigDictionary
from etce.overlaylistchainfactory import OverlayListChainFactory
from etce.utils import configstrtoval

class TemplateDirectoryBuilderConfig(object):
    """
    Configuration for TemplateDirectoryBuilder, extraced from
    XML elements.
    """

    def __init__(self, templatedirelem, indices):
        self._name = templatedirelem.attrib['name']

        self._indices = indices

        self._relative_path, \
        self._hostname_format = self._read_attributes(templatedirelem)

        self._template_local_overlays = {}

        for overlayelem in templatedirelem.findall('./overlay'):
            oname = overlayelem.attrib['name']

            oval = overlayelem.attrib['value']

            otype = overlayelem.attrib.get('type', None)

            self._template_local_overlays[oname] = configstrtoval(oval, argtype=otype)

        self._template_local_overlaylists = \
            OverlayListChainFactory().make(templatedirelem.findall('./overlaylist'),
                                           self._indices)


    def _read_attributes(self, templatedirelem):
        template_subdir = \
            '.'.join([self._name,
                      ConfigDictionary().get('etce', 'TEMPLATE_DIRECTORY_SUFFIX')])

        # for template directory foo.tpl default template directory name format and
        # TEMPLATE_HOSTNUMBER_DIGITS value N is
        # foo-${'%0Nd' % etce_index}
        default_hostname_format = \
            templatedirelem.attrib.get('name') + \
            "-${'%0" + \
            str(ConfigDictionary().get('etce', 'TEMPLATE_HOSTNUMBER_DIGITS')) + \
            "d' % etce_index}"

        hostname_format = \
            templatedirelem.attrib.get('hostname_format', default_hostname_format)

        return (template_subdir, hostname_format)


    @property
    def name(self):
        return self._name

    @property
    def indices(self):
        return self._indices

    @property
    def relative_path(self):
        return self._relative_path

    @property
    def hostname_format(self):
        return self._hostname_format

    @property
    def template_local_overlays(self):
        return self._template_local_overlays

    @property
    def template_local_overlaylists(self):
        return self._template_local_overlaylists

