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

import ctypes
import fcntl
import json
import socket
import struct
import sys


def get_ip_address(ifname):
    # http://code.activestate.com/recipes/439094/
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15].encode() if sys.version_info >= (3,0) else ifname[:15])
    )[20:24])


class StatusPublisher:
    def __init__(self, multicast_group, multicast_device):

        ipv4,group_port = multicast_group.split(':')

        self._group = ipv4

        group_port = int(group_port)

        self._addr_info = socket.getaddrinfo(self._group,group_port,0,0,socket.SOL_UDP)

        libc = ctypes.CDLL(None)

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)

        self._sock.setsockopt(socket.IPPROTO_IP,socket.IP_MULTICAST_TTL, 1)

        self._sock.setsockopt(socket.IPPROTO_IP,socket.IP_MULTICAST_LOOP, 0)

        self._sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR, 1)

        device_index = \
            libc.if_nametoindex(
                ctypes.c_char_p(
                    multicast_device.encode('utf-8')))

        if_index = struct.pack('I', device_index)

        dev_address = socket.inet_aton(get_ip_address(multicast_device))

        mreqn = socket.inet_aton(self._group) + dev_address + if_index

        self._sock.setsockopt(socket.SOL_IP,
                              socket.IP_MULTICAST_IF,
                              mreqn)


    def publish(self, message):
        toks = message.split()

        json_msg = json.dumps({'name':toks[0],
                               'trial':toks[1],
                               'step':toks[2]})

        self._sock.sendto(json_msg.encode('utf-8'),
                          self._addr_info[0][4])


    def close(self):
        self._sock.close()
