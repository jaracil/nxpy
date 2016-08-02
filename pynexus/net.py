# -*- coding: utf-8 -*-
##############################################################################
#
#    pynexus, a Python library for easy playing with Nexus
#    Copyright (C) 2016 by the pynexus team
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import socket
import srvlookup

ports = {
    'tcp': 1717,
    'ssl': 1718,
    'ws' : 80,
    'wss': 443,
}

def lookupSRV(hostname, scheme):
    try:
        return srvlookup.lookup('nexus', scheme, hostname)
    except:
        return []

def connect(hostname, port=None, scheme=None):
    if not scheme:
        scheme = "ssl"

    servers = []

    # SRV DNS Records
    if not port:
        addrs = lookupSRV(hostname, scheme)
        for addr in addrs:
            servers.append([addr.host, addr.port])
        else:
            servers.append([hostname, ports.get(scheme, 0)])
    else:
        servers.append([hostname, port])

    # Open connection
    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    error = None
    for server in servers:
        try:
            conn.connect((server[0], server[1]))
            error = None
            break
        except Exception as e:
            error = e
    if error:
        raise error
    return conn