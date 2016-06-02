# -*- coding: utf-8 -*-
##############################################################################
#
#    pynexus, a Python library for easy playing with Nexus
#    Copyright (C) 2016 by Javier Sancho Fernandez <jsf at jsancho dot org>
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

import pynexus
import socket
import sys
from urlparse import urlparse


if __name__ == '__main__':
    nexusURL = urlparse(sys.argv[1])

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((nexusURL.hostname, nexusURL.port))
    nexusConn = pynexus.NexusConn(s)
    nexusConn.login(nexusURL.username, nexusURL.password)

    try:
        print(nexusConn.taskPush(nexusURL.path[1:], {'v': sys.argv[2]}))
    finally:
        nexusConn.cancel()
