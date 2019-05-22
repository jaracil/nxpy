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
from multiprocessing import Pipe
import uuid
import websocket

class JSocketDecoder:
    def __init__(self, connection, chunk_size=2048):
        self.buf = ''
        self.decoder = json.JSONDecoder()
        self.connection = connection
        self.chunk_size = chunk_size
        self.obj_index = Pipe(False)
        self.objects = {}

    def storeObject(self, obj):
        uid = uuid.uuid4()
        self.objects[uid] = obj
        self.obj_index[1].send(uid)

    def getStoredObject(self):
        res = None
        if self.obj_index[0].poll():
            uid = self.obj_index[0].recv()
            res = self.objects[uid]
            del self.objects[uid]
        return res

    def recv(self):
        chunk = b""

        if type(self.connection) is websocket.WebSocket:
            chunk = self.connection.recv()
        else:
            incomplete = True
            while incomplete:
                chunk += self.connection.recv(self.chunk_size)
                try:
                    chunk = chunk.decode('utf8')
                    incomplete = False
                except:
                    pass

        return chunk

    def readObject(self):
        chunk = self.recv()
        if not chunk:
            raise Exception("Nexus Connection Closed")
        self.buf += chunk

        while self.buf:
            try:
                self.buf = self.buf.lstrip() # in case only whitespace was read, raw_decode fails if starting with whitespace
                res, index = self.decoder.raw_decode(self.buf)
                self.buf = self.buf[index:].lstrip()
                if res:
                    self.storeObject(res)
            except ValueError:
                self.buf += self.recv()
        return self.getStoredObject()
    
    def getObject(self):
        res = self.getStoredObject()
        if not res:
            res = self.readObject()
        return res

    def fileno(self):
        if self.obj_index[0].poll():
            return self.obj_index[0].fileno()
        else:
            return self.connection.fileno()
