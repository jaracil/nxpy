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

import json
from multiprocessing import Queue
import websocket

class JSocketDecoder:
    def __init__(self, connection, chunk_size=2048):
        self.buf = ''
        self.decoder = json.JSONDecoder()
        self.connection = connection
        self.chunk_size = chunk_size
        self.objects = Queue()

    def getStoredObject(self):
        res = None
        if not self.objects.empty():
            res = self.objects.get()
        return res

    def recv(self):
        chunk = None
        if type(self.connection) is websocket.WebSocket:
            chunk = self.connection.recv()
        else:
            chunk = self.connection.recv(self.chunk_size)
        return chunk

    def readObject(self):
        chunk = self.recv()
        if not chunk:
            raise Exception("Nexus Connection Closed")
        try:
            self.buf += chunk.decode('utf8')
        except:
            self.buf += chunk
        # TODO change so it ends reading an object when it finds an "\r"
        while self.buf:
            try:
                res, index = self.decoder.raw_decode(self.buf)
                self.buf = self.buf[index:].lstrip()
                if res:
                    self.objects.put(res)
            except ValueError:
                break
        return self.getStoredObject()
    
    def getObject(self):
        res = self.getStoredObject()
        if not res:
            res = self.readObject()
        return res

    def fileno(self):
        if self.objects.qsize() == 0:
            return self.connection.fileno()
        else:
            return self.objects._reader.fileno()
