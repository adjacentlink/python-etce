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

from pkg_resources import resource_filename
from lxml import etree
from lxml.etree import DocumentInvalid, XMLSyntaxError

from etce.xmldocerror import XMLDocError

class XMLDoc(object):
    """
    Base class for parsing and validating ETCE XML
    documents against the associated schema.
    """

    def __init__(self, schemafile, schemamodule='etce'):
        self._schema = etree.XMLSchema(etree.parse(resource_filename(schemamodule, schemafile)))


    def parse(self, xmlfile):
        xml_doc = None

        try:
            xml_doc = etree.parse(xmlfile)
        except XMLSyntaxError as xmle:
            err = '%s failed to parse with error:\n\t%s' %(xmlfile, str(xmle))
            raise XMLDocError(err)

        try:
            self._schema.assertValid(xml_doc)
        except DocumentInvalid as e:
            err = '%s failed to validate with error:\n\t%s' %(xmlfile, str(e))
            raise XMLDocError(err)

        return xml_doc.getroot()
