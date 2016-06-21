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
import sys
from urlparse import urlparse


if __name__ == '__main__':
    """
    The argument is a standard string connection with the next structure:
        protocol://[user:pass@]host[:port]/path
    For example:
        tcp://test:test@localhost:1717/test.fibonacci
    """

    nexusClient = pynexus.Client(sys.argv[1])
    method = urlparse(sys.argv[1]).path[1:]

    try:
        print(nexusClient.taskPush(method, {'v': sys.argv[2]}))
    finally:
        nexusClient.close()
