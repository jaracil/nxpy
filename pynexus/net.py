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
import ssl
import websocket

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
        scheme = 'ssl'
    if scheme == 'http':
        scheme = 'ws'
    if scheme == 'https':
        scheme = 'wss'

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
    conn = None
    if scheme in ['tcp', 'ssl']:
        conn = create_tcp_connection(scheme, servers)
    elif scheme in ['ws', 'wss']:
        conn = create_ws_connection(scheme, servers)
    return conn

def create_tcp_connection(scheme, servers):
    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    error = None
    if scheme == "ssl":
        conn = ssl.SSLSocket(conn)
    for hostname, port in servers:
        try:
            conn.connect((hostname, port))
            error = None
            break
        except Exception as e:
            error = e
    if error:
        raise error
    return conn

def create_ws_connection(scheme, servers):
    conn = None
    error = None
    for hostname, port in servers:
        try:
            conn = websocket.create_connection('%s://%s:%s/' % (scheme, hostname, port),
                                               sslopt={"cert_reqs": ssl.CERT_NONE})
            error = None
            break
        except Exception as e:
            error = e
    if error:
        raise error
    return conn
