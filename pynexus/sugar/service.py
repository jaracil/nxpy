# -*- coding: utf-8 -*-

import sys
sys.path.insert(0, '..')
import socket
import threading
import pynexus as nxpy
from urlparse import urlparse

class Service:
    def __init__(self, url, path, options = {}):
        self.url  = urlparse(url)
        self.path = path
        self.methods = {}

        self.pulls = 1
        if "pulls" in options and options["pulls"] > 0:
            self.pulls = options["pulls"]

        self.pulltimeout = 3600
        if "pulltimeout" in options and options["pulltimeout"] > 0:
            self.pulltimeout = options["pulltimeout"]

    def add_method(self, name, func):
        self.methods[name] = func

    def get_conn(self):
        return self.nexusConn

    def start(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.url.hostname, self.url.port))
        self.nexusConn = nxpy.NexusConn(s)
        self.nexusConn.login(self.url.username, self.url.password)

        try:
            for i in range(self.pulls):
                worker = threading.Thread(target = self.server, args = (self.nexusConn, self.path))
                worker.daemon = True
                worker.start()
        except:
            self.nexusConn.cancel()

    def wait(self):
        try:
            for worker, _ in self.nexusConn.workers:
                worker.join()
        except:
            self.stop()

    def stop(self):
        self.nexusConn.cancel()

    def server(self, conn, prefix):
        while True:
            task, err = conn.taskPull(prefix, self.pulltimeout)
            if err:
                raise Exception(err)

            if task.method in self.methods.keys():
                try:
                    self.methods[task.method](task)
                except:
                    task.sendError(nxpy.ErrUnknownError, nxpy.ErrStr[nxpy.ErrUnknownError], None)
            else:
                task.sendError(nxpy.ErrMethodNotFound, nxpy.ErrStr[nxpy.ErrMethodNotFound], None)