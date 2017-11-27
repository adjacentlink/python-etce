#
# Copyright (c) 2017 - Adjacent Link LLC, Bridgewater, New Jersey
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

from mako.template import Template
from mako.runtime import Context
from StringIO import StringIO


class CaptureContext(Context):
    def __init__(self):
        self._keys = set([])
        super(CaptureContext, self).__init__(StringIO())

    def get(self, key, default=None):
        self._keys.update([key])
        return 40.0

    def get_all_keys(self):
        return self._keys


def get_file_params(templatefile):
    t = Template(filename=templatefile)

    ctx = CaptureContext()

    t.render_context(ctx)

    return ctx.get_all_keys()


def format_file(srcfile, dstfile, overlays):
    template = Template(filename=srcfile, strict_undefined=True)

    with open(dstfile, 'w') as outf:
        try:
            outf.write(template.render(**overlays))
        except NameError as ne:
            message = '%s for template file "%s". Quitting.' % \
                      (ne.message, srcfile)
            raise NameError(message)


def format_string(template_string, overlays):
    template = Template(template_string, strict_undefined=True)

    try:
        return template.render(**overlays)
    except NameError as ne:
        message = \
            '%s for template string "%s". Available tags are {%s}. Quitting.' % \
            (ne.message, template_string, ','.join(overlays.keys()))
        raise NameError(message)
