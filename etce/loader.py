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

import imp
import etce.platform


'''load a the most specialized mode with the given name
from with the etce hierarchy'''
def load_etce_module(modulename, root='etce'):
    for suffix in etce.platform.platform_suffix_list():
        module = None
        try:
            module = load_module(root + '.' + suffix + '.' + modulename)
        except Exception:
            pass

        if module:
            return module

    # look for default - no specialization
    try:
        module = load_module('etce.' + modulename)
    except Exception:
        pass

    if module:
        return module

    return None


'''load a class instance from the etce hierarchy'''
def load_etce_class_instance(modulename, root='etce', args=[], kwargs={}):
    module = load_etce_module(modulename, root)
    return load_class_instance_from_module(module, args, kwargs)


'''Search for a class with the same classname as the module.
Capitalization doesn't matter. If there are more than one class 
definitions with the module name, but differeing only by capitalization,
then not well defined which one will be instantiated'''
def load_class_instance_from_module(module, args=[], kwargs={}):
    basename = module.__name__.split('/')[-1]
    candidateclassname = basename.upper()
    try:
        for key in module.__dict__:
            if key.upper() == candidateclassname:
                candidateclass = module.__dict__[key]
                if callable(candidateclass):
                    o = candidateclass(*args, **kwargs)
                    return o
    except KeyError, e:
        return None
    
    return None


'''
Return the module method based on etce search path. 
'''
def load_etce_method(modulename, methodname):
    mod = load_etce_module(modulename)

    if mod:
        # first try to find a class based on the modulename (modulename)
        # but capitalized
        obj = load_class_instance_from_module(mod)
        try:
            if obj:
                candidatemethod = getattr(obj, methodname)
                if callable(candidatemethod):
                    return candidatemethod
        except AttributeError, e:
            pass

        # then just try a module level function
        try:
            candidatemethod = getattr(mod, methodname)
            if callable(candidatemethod):
                return candidatemethod
        except AttributeError, e:
            pass

    return None


def load_class_instance(modulename, args=[], kwargs={}):
    '''from the passed modulename, return an instance of the class
    (named same as module basename, constructed with the passed args
    and kwargs - it's __init__ method is called with these
    '''
    return load_class_instance_from_module(load_module(modulename),
                                           args,
                                           kwargs)

'''
Load the named python module, None if unsuccessful
'''
def load_module(modulename):
    m = modulename.replace('.', '/')
    fp,pathname,description = imp.find_module(m)
    return imp.load_module(m,fp,pathname,description)


