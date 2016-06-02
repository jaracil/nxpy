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

import json

class JSocketDecoder:
    def __init__(self, connection, chunk_size=2048):
        self.buf = ''
        self.decoder = json.JSONDecoder()
        self.connection = connection
        self.chunk_size = chunk_size
        self.objects = []

    def getStoredObject(self):
        res = None
        if self.objects:
            res = self.objects[0]
            self.objects = self.objects[1:]
        return res

    def readObject(self):
        chunk = self.connection.recv(self.chunk_size)
        if not chunk:
            raise Exception("Nexus Connection Closed")
        self.buf += chunk
        # TODO change so it ends reading an object when it finds an "\r"
        while self.buf:
            try:
                res, index = self.decoder.raw_decode(self.buf)
                self.buf = self.buf[index:].strip() # strip could erase important whitespace from a valid string?
                if res:
                    self.objects.append(res)
            except valueError:
                break
        return self.getStoredObject()
    
    def getObject(self):
        res = self.getStoredObject()
        if not res:
            res = self.readObject()
        return res
