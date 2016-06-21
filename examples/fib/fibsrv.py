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
import time
from urlparse import urlparse


def fib(n):
    res = []
    i, j = 0, 1
    while j < n:
        res.append(i)
        i, j = i+j, i
    return res


def fibServer(nexusClient, prefix):
    while True:
        task, err = nexusClient.taskPull(prefix)
        if err:
            raise Exception(err)

        print("Task received:", task.method, task.params)
        
        if task.method == "fib":
            try:
                v = int(task.params['v'])

                timeout = task.params.get('timeout', 0)
                if timeout > 0:
                    time.sleep(timeout)

                task.sendResult(fib(v))
                
            except:
                task.sendError(1, "Unknown error", task.params)
                raise

        elif task.method == "exit":
            task.sendResult("ok")
            break

        else:
            task.sendError(-32601, "", None)
            

if __name__ == '__main__':
    """
    The argument is a standard string connection with the next structure:
        protocol://[user:pass@]host[:port]/path
    For example:
        tcp://test:test@localhost:1717/test.fibonacci
    """

    nexusClient = pynexus.Client(sys.argv[1])
    prefix = urlparse(sys.argv[1]).path[1:]

    try:
        fibServer(nexusClient, prefix)
    finally:
        nexusClient.close()

    print("Exit")
