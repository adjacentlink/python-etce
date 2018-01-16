#
# Copyright (c) 2014-2018 - Adjacent Link LLC, Bridgewater, New Jersey
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

import copy
import os.path
import socket
import sys
from collections import defaultdict

import etce.utils
import etce.xmldoc
from etce.config import ConfigDictionary
from etce.lxcerror import LXCError
from etce.templateutils import format_string


class Bridge(object):
    def __init__(self, bridgeelem):
        self._parse(bridgeelem)

    @property
    def name(self):
        return self._name

    @property
    def devicename(self):
        return self._name

    @property
    def persistent(self):
        return self._persistent

    @property
    def ipv4(self):
        return self._ipv4

    @property
    def ipv6(self):
        return self._ipv6

    @property
    def addifs(self):
        return copy.copy(self._addifs)

    def _parse(self, bridgeelem):
        self._name = str(bridgeelem.attrib['name'])

        self._persistent = True \
            if str(bridgeelem.attrib['persistent'].upper()) == 'TRUE' \
               else False

        self._ipv4 = None
        for ipv4 in bridgeelem.findall('./ipaddress/ipv4'):
            self._ipv4 = ipv4.text

        self._ipv6 = None
        for ipv6 in bridgeelem.findall('./ipaddress/ipv6'):
            self._ipv6 = ipv6.text

        self._addifs = [ str(addif.text) 
                         for addif in bridgeelem.findall('./addif') ]
        
    def __str__(self):
        s  = 'Bridge:\n'
        s += 'name=%s\n' % self._name
        s += 'persistent=%s\n' % str(self._persistent)
        s += 'ipv4s=%s\n' % self._ipv4
        s += 'ipv6s=%s\n' % self._ipv6
        s += 'addifs=(%s)\n' % ','.join(self._addifs)
        return s


class BridgeImplicit(object):
    def __init__(self, bridgename):
        self._name = bridgename
        self._persistent = False
        self._ipv4 = None
        self._ipv6 = None
        self._addifs = []

    @property
    def name(self):
        return self._name

    @property
    def devicename(self):
        return self._name

    @property
    def persistent(self):
        return self._persistent

    @property
    def ipv4(self):
        return self._ipv4

    @property
    def ipv6(self):
        return self._ipv6

    @property
    def addifs(self):
        return self._addifs
                
    def __str__(self):
        s  = 'Bridge:\n'
        s += 'name=%s\n' % self._name
        s += 'persistent=%s\n' % str(self._persistent)
        s += 'ipv4s=%s\n' % self._ipv4
        s += 'ipv6s=%s\n' % self._ipv6
        s += 'addifs=(%s)\n' % ','.join(self._addifs)
        return s


class ContainerTemplate(object):
    def __init__(self, containertemplateelem, parent=None):
        self._params, \
        self._interfaces, \
        self._initscript, \
        self._hosts_entries_ipv4, \
        self._hosts_entries_ipv6 = self._parse(containertemplateelem, parent)

    @property
    def params(self):
        return copy.copy(self._params)

    @property
    def interfaces(self):
        # interfaces is a map of interface template name  to (name,val)
        # interface params
        return copy.deepcopy(self._interfaces)

    @property
    def initscript(self):
        return copy.copy(self._initscript)

    @property
    def hosts_entries_ipv4(self):
        return copy.copy(self._hosts_entries_ipv4)

    @property
    def hosts_entries_ipv6(self):
        return copy.copy(self._hosts_entries_ipv6)

    def _parse(self, containertemplateelem, parent):
        params = parent.params if parent else []

        interfaces = parent.interfaces if parent else defaultdict(lambda: {})

        initscript = parent.initscript if parent else (None,None)

        hosts_entries_ipv4 = parent.hosts_entries_ipv4 if parent else {}

        hosts_entries_ipv6 = parent.hosts_entries_ipv6 if parent else {}

        for paramelem in containertemplateelem.findall('./parameters/parameter'):
            # lxc.utsname set by container element attribute
            if(str(paramelem.attrib['name']) == 'lxc.utsname'):
                print >>sys.stderr, \
                    'Found lxc.utsname in containertemplate. Ignoring'
                continue

            params.append((paramelem.attrib['name'],
                           paramelem.attrib['value']))

        interfaceelems = \
            containertemplateelem.findall('./interfaces/interface')

        for interfaceelem in interfaceelems:
            bridgename = interfaceelem.attrib['bridge']

            entry_ipv4 = interfaceelem.attrib.get('hosts_entry_ipv4', None)
            if entry_ipv4:
                hosts_entries_ipv4[bridgename] = entry_ipv4

            entry_ipv6 = interfaceelem.attrib.get('hosts_entry_ipv6', None)
            if entry_ipv6:
                hosts_entries_ipv6[bridgename] = entry_ipv6

            iparams = interfaces[bridgename]

            for paramelem in interfaceelem.findall('./parameter'):
                iname = str(paramelem.attrib['name'])

                ival = str(paramelem.attrib['value'])

                iparams[iname] = ival

        for initscriptelem in containertemplateelem.findall('./initscript'):
            initscript = \
                (initscriptelem.attrib['filename'], initscriptelem.text)

        return (params,
                interfaces,
                initscript,
                hosts_entries_ipv4,
                hosts_entries_ipv6)


class Container(object):
    def __init__(self, 
                 containerelem,
                 overlays,
                 commonparams, 
                 containertemplate, 
                 bridges,
                 hostname):
        self._lxc_name = overlays['lxc_name']

        self._lxc_directory = overlays['lxc_directory']

        self._bridges = bridges

        self._params, \
        self._interfaces, \
        self._hosts_entries_ipv4, \
        self._hosts_entries_ipv6, \
        self._initscript = self._parse(containerelem, 
                                       overlays, 
                                       commonparams, 
                                       containertemplate, 
                                       bridges,
                                       hostname)


    @property
    def lxc_name(self):
        return self._lxc_name

    @property
    def params(self):
        return self._params

    @property
    def lxc_directory(self):
        return self._lxc_directory

    @property
    def initscript(self):
        return self._initscript

    @property
    def interfaces(self):
        return self._interfaces

    @property
    def hosts_entries_ipv4(self):
        return self._hosts_entries_ipv4

    @property
    def hosts_entries_ipv6(self):
        return self._hosts_entries_ipv6

    def _parse(self, 
               containerelem, 
               overlays, 
               commonparams, 
               containertemplate, 
               bridges,
               hostname):
        # assemble common (non-interface) params in order
        # 1. common template params
        # 2. commonparams passed in 
        # 3. params from containerelem
        #
        # and overwrite all of them with overlays
        containerparams = \
            self._collate_container_params(containertemplate, 
                                           commonparams, 
                                           containerelem, 
                                           overlays)

        # get all interface params and host names
        interfaces,hosts_entries_ipv4,hosts_entries_ipv6 = \
            self._process_interfaces(containertemplate, 
                                     containerelem, 
                                     overlays)

        # get initscript
        initscript = \
            self._get_initscript(containertemplate, containerelem, overlays)

        return (containerparams,
                interfaces,
                hosts_entries_ipv4,
                hosts_entries_ipv6,
                initscript)


    def _prune(self, paramdict):
        names = []

        params = []

        for k,v in paramdict.items():
            if not k in names:
                names.append(k)
                params.append((k,v))

        params.reverse()

        return params


    def _collate_container_params(self, 
                                  containertemplate, 
                                  commonparams, 
                                  containerelem, 
                                  overlays):

        containerparams = [ ('lxc.utsname', self.lxc_name) ]

        if containertemplate:
            containerparams.extend(containertemplate.params)

        for k,v in commonparams:
            containerparams.append((k,v))

        for paramelem in containerelem.findall('./parameters/parameter'):
            if(str(paramelem.attrib['name']) == 'lxc.utsname'):
                # the lxc_name is set by the container element atribute
                print >>sys.stderr, \
                    'Found lxc.utsname in containertemplate. Ignoring'
                continue

            containerparams.append((str(paramelem.attrib['name']),
                                    str(paramelem.attrib['value'])))

        for i,parampair in enumerate(containerparams):
            k,v = parampair

            containerparams[i] = (k,format_string(v, overlays))

        return containerparams


    def _process_interfaces(self, containertemplate, containerelem, overlays):
        interfaces = defaultdict(lambda: {})

        bridge_entry_ipv4 = {}

        bridge_entry_ipv6 = {}

        if containertemplate:
            for bridgename,paramdict in containertemplate.interfaces.items():
                bridgename = format_string(bridgename, overlays)
                for iname,ival in paramdict.items():
                    interfaces[bridgename][format_string(iname, overlays)] = \
                        format_string(ival, overlays)

            for bridgename, entryname in \
                containertemplate.hosts_entries_ipv4.items():
                bridgename = format_string(bridgename, overlays)
                bridge_entry_ipv4[bridgename] = format_string(entryname, overlays)

            for bridgename, entryname in \
                containertemplate.hosts_entries_ipv6.items():
                bridgename = format_string(bridgename, overlays)
                bridge_entry_ipv6[bridgename] = format_string(entryname, overlays)

        # overwrite with local values from container
        for interfaceelem in containerelem.findall('./interfaces/interface'):
            bridgename = format_string(str(interfaceelem.attrib['bridge']), overlays)

            interfaceparams = interfaces[bridgename]

            for iparamelem in interfaceelem.findall('./parameter'):
                iname = format_string(str(iparamelem.attrib['name']), overlays)

                ival = format_string(str(iparamelem.attrib['value']), overlays)

                interfaceparams[iname] =  ival

            entry_name_ipv4 = \
                interfaceelem.attrib.get(
                    'hosts_entry_ipv4', 
                    bridge_entry_ipv4.get(bridgename, None))

            if entry_name_ipv4:
                bridge_entry_ipv4[bridgename] = \
                    format_string(entry_name_ipv4, overlays)

            entry_name_ipv6 = \
                interfaceelem.attrib.get(
                    'hosts_entry_ipv6', 
                    bridge_entry_ipv6.get(bridgename, None))

            if entry_name_ipv6:
                bridge_entry_ipv6[bridgename] = \
                    format_string(entry_name_ipv6, overlays)

        hosts_entries_ipv4 = []

        for bridgename,entry_name_ipv4 in bridge_entry_ipv4.items():
            if not 'lxc.network.ipv4' in interfaces[bridgename]:
                error = 'Found hosts_entry_ipv4 attribute for ' \
                        'bridge "%s" for container "%s" but ' \
                        'no corresponding "lxc.network.ipv4" ' \
                        'value for the interface. Quitting.' \
                        % (bridgename, self.lxc_name)
                raise ValueError(error)
                    
            addr = interfaces[bridgename]['lxc.network.ipv4']

            hosts_entries_ipv4.append((entry_name_ipv4,  addr.split('/')[0]))

        hosts_entries_ipv6 = []

        for bridgename,entry_name_ipv6 in bridge_entry_ipv6.items():
            if not 'lxc.network.ipv6' in interfaces[bridgename]:
                error = 'Found hosts_entry_ipv6 attribute for ' \
                        'bridge "%s" for container "%s" but ' \
                        'no corresponding "lxc.network.ipv6" ' \
                        'value for the interface. Quitting.' \
                        % (bridgename, self.lxc_name)
                raise ValueError(error)
                
            addr = interfaces[bridgename]['lxc.network.ipv6']

            hosts_entries_ipv6.append((entry_name_ipv6,  addr))

        return interfaces,hosts_entries_ipv4,hosts_entries_ipv6



    def _get_initscript(self, containertemplate, containerelem, overlays):
        initscript= ('',None)

        if containertemplate:
            initscript = containertemplate.initscript

        for initscriptelem in containerelem.findall('./initscript'):
            initscript = (initscriptelem.attrib['filename'], 
                          initscriptelem.text)

        if initscript[1]:
            lines = []

            for line in initscript[1].split('\n'):
                line = line.strip()

                if len(line) > 0:
                    lines.append(format_string(line.strip(), overlays))

            initscript = (initscript[0], '\n'.join(lines))

        return initscript



    def __str__(self):
        s = ''
        for k,v in self._params:
            s += '%s=%s\n' % (k,v)
        for bridgename,interfaceparams in self._interfaces.items():
            s += '\n# %s interface\n' % bridgename
            s += 'lxc.network.type=%s\n' % interfaceparams['lxc.network.type']
            for k,v in sorted(interfaceparams.items()):
                if k == 'lxc.network.type':
                    continue
                s += '%s=%s\n' % (k,v)
            s += 'lxc.network.link=%s\n' % self._bridges[bridgename].name
        s += '\n# loopback interface\n'
        s += 'lxc.network.type = empty\n'
        s += 'lxc.network.flags = up\n'

        return s


class LXCPlanFileDoc(etce.xmldoc.XMLDoc):
    def __init__(self, lxcplanfile):
        etce.xmldoc.XMLDoc.__init__(self, 'lxcplanfile.xsd')

        if not os.path.isfile(lxcplanfile):
            raise LXCError('Cannot find lxcplanfile "%s". Quitting.' % lxcplanfile)
        
        self._lxcplanfile = lxcplanfile

        # just xml parse first
        self._hostnames, \
        self._kernelparameters, \
        self._bridges, \
        self._containers, \
        self._rootdirectories = self._parseplan(lxcplanfile)


    def planfile(self):
        return self._lxcplanfile


    def hostnames(self):
        return copy.copy(self._hostnames)


    def kernelparameters(self, hostname):
        if hostname in self._kernelparameters:
            return self._kernelparameters[hostname]

        return self._kernelparameters.get('localhost',{})


    def bridges(self, hostname):
        if hostname in self._bridges:
            return self._bridges[hostname]

        return self._bridges.get('localhost', {})


    def lxc_root_directory(self, hostname):
        if hostname in self._rootdirectories:
            return self._rootdirectories[hostname]

        return self._rootdirectories.get('localhost', None)


    def containers(self, hostname):
        if hostname in self._containers:
            return self._containers[hostname]

        return self._containers.get('localhost', [])


    def _parseplan(self, lxcplanfile): 
        lxcplanelem = self.parse(lxcplanfile)

        kernelparameters = {}

        containertemplates = {}

        rootdirectories = {}

        lxcplanelems = \
            lxcplanelem.findall('./containertemplates/containertemplate')

        for containertemplateelem in lxcplanelems:
            containertemplate_name = containertemplateelem.attrib['name']

            containertemplate_parent_name = \
                containertemplateelem.attrib.get('parent', None)

            containertemplate_parent = None

            if containertemplate_parent_name:
                if not containertemplate_parent_name in containertemplates:
                    errmsg = 'parent "%s" of containertemplate "%s" not ' \
                             'previously listed. Quitting.' % \
                             (containertemplate_parent_name,
                              containertemplate_name)
                    raise ValueError(errmsg)

                containertemplate_parent = \
                    containertemplates[containertemplate_parent_name]

            containertemplates[containertemplate_name] = \
                ContainerTemplate(containertemplateelem, 
                                  containertemplate_parent)
                                            
        hostelems = lxcplanelem.findall('./hosts/host')

        bridges = {}

        containers = {}

        hostnames = []

        for hostelem in hostelems:
            hostname = hostelem.attrib.get('hostname')

            hostnames.append(hostname)
            
            # 'localhost' is permitted as a catchall hostname to mean the
            # local machine only when one host is specified in the file
            if hostname == 'localhost':
                if len(hostelems) > 1:
                    error = '"localhost" hostname only permitted when one ' \
                            'host is specified. Quitting'
                    raise ValueError(error)

            # kernel params
            kernelparameters[hostname] = {}

            for paramelem in hostelem.findall('./kernelparameters/parameter'):
                kernelparameters[hostname][paramelem.attrib['name']] = \
                    paramelem.attrib['value']

            # bridges (explicit)
            bridges[hostname] = {}

            for bridgeelem in hostelem.findall('./bridges/bridge'):
                bridge = Bridge(bridgeelem)

                bridges[hostname][bridge.name] = bridge

            containers[hostname] = []

            params = []

            root_directory = str(
                hostelem.findall('./containers')[0].attrib['root_directory'])
            rootdirectories[hostname] = root_directory

            # ensure no repeated lxc_indices
            alllxcids = set([])

            for containerelem in hostelem.findall('./containers/container'):
                containerlxcids = etce.utils.nodestr_to_nodelist(
                    str(containerelem.attrib['lxc_indices']))

                repeatedids = alllxcids.intersection(containerlxcids)

                assert len(repeatedids) == 0, \
                    'Found repeated lxcid(s): {%s}. Quitting.' % \
                    ','.join([ str(nid) for nid in list(repeatedids) ])

                alllxcids.update(containerlxcids)

            # Create containers from container elems
            for containerelem in hostelem.findall('./containers/container'):
                templatename = containerelem.attrib.get('template', None)

                template = containertemplates.get(templatename, None)

                lxcids = etce.utils.nodestr_to_nodelist(
                    str(containerelem.attrib['lxc_indices']))

                # fetch the overlays, use etce file values as default
                overlays = ConfigDictionary().asdict()['overlays']

                for overlayelem in containerelem.findall('./overlays/overlay'):
                    oname = overlayelem.attrib['name']

                    ovalue = overlayelem.attrib['value']

                    overlays[oname] = etce.utils.configstrtoval(ovalue)

                # fetch the overlaylists
                overlaylists = {}

                for overlaylistelem in containerelem.findall('./overlays/overlaylist'):
                    oname = overlaylistelem.attrib['name']

                    separator = overlaylistelem.attrib.get('separator',',')

                    ovalues = overlaylistelem.attrib['values'].split(separator)

                    overlaylists[oname] = ovalues

                # treat all values for each name as an int if possible,
                # else all strings
                for oname,ovals in overlaylists.items():
                    converted_vals = []
                    try:
                        converted_vals = [ etce.utils.configstrtoval(oval)
                                           for oval in ovals ]

                        overlaylists[oname] = converted_vals
                    except ValueError:
                        # leave as strings
                        pass

                # Why must a default value be supplied here when
                # schema declares this attribute with a default value?
                for i,lxcid in enumerate(lxcids):
                    # start with overlays
                    lxcoverlays = copy.copy(overlays)

                    # then add list items for this node
                    for oname,ovals in overlaylists.items():
                        lxcoverlays[oname] = ovals[i]

                    # then lxcindex, lxc_name and lxc_directory (cannot be overwritten)
                    lxcoverlays.update(
                        {'lxc_index':lxcid})

                    lxcoverlays.update(
                        {'lxc_name':format_string(containerelem.attrib['lxc_name'], lxcoverlays)})

                    lxcoverlays.update(
                        {'lxc_directory':os.path.join(root_directory, lxcoverlays['lxc_name'])})

                    containers[hostname].append(Container(containerelem,
                                                          lxcoverlays,
                                                          params,
                                                          template,
                                                          bridges[hostname],
                                                          hostname))

            # Roll over containers to get names of implicit bridges added
            # from the container interface bridge names and augment
            # the bridges list
            for container in containers[hostname]:
                for iname,iparams in container.interfaces.items():
                    if not iname in bridges[hostname]:
                        bridges[hostname][iname] = BridgeImplicit(iname)
            
        return hostnames,kernelparameters,bridges,containers,rootdirectories


def main():
    import sys

    if len(sys.argv) != 2:
        print 'usage: lxcplanfiledoc.py lxcplanfile'
        exit(1)

    lxcplanfile = sys.argv[1]

    try:
        plandoc = LXCPlanFileDoc(lxcplanfile)

        # get containers and bridges for this host. Use only
        # machine name
        hostname = socket.gethostname().split('.')[0]
        for kernelparamname,kernelparamval in plandoc.kernelparameters(hostname).items():
            print kernelparamname,kernelparamval
        for bridge in plandoc.bridges(hostname):
            print bridge
        for container in plandoc.containers(hostname):
            print container

    except AssertionError as e:
        print e.message
        exit (1)


if __name__=='__main__':
    main()
