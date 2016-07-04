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
        self.preaction = None
        self.postaction = None
        self.testing = False

        self.pulls = 1
        if "pulls" in options and options["pulls"] > 0:
            self.pulls = options["pulls"]

        self.pulltimeout = 3600
        if "pulltimeout" in options and options["pulltimeout"] > 0:
            self.pulltimeout = options["pulltimeout"]

        if "testing" in options and options["testing"]:
            self.testing = True

        if "preaction" in options:
            self.preaction = options["preaction"]

        if "postaction" in options:
            self.postaction = options["postaction"]

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
                if self.testing:
                    return
                raise Exception(err)
            
            if self.preaction:
                self.preaction(task)

            if task.method in self.methods.keys():
                try:
                    res, err = self.methods[task.method](task)
                except:
                    res, err = None, {'code': nxpy.ErrUnknownError, 'message': ''}
            else:
                res, err = None, {'code': nxpy.ErrMethodNotFound, 'message': ''}

            if self.postaction:
                self.postaction(task, res, err)

            try:
                if "replyTo" in task.params.keys():
                    reply = task.params["replyTo"]

                    if reply["type"] == "pipe":
                        pipe, _ = conn.pipeOpen(reply["path"])
                        pipe.write({'result': res, 'error': err, 'task': {
                            "path": task.path,
                            "method": task.method,
                            "params": task.params,
                            "tags": task.tags,
                        }})

                    elif reply["type"] == "service":
                        conn.taskPush(reply["path"], {'result': res, 'error': err, 'task': {
                            "path": task.path,
                            "method": task.method,
                            "params": task.params,
                            "tags": task.tags,
                        }}, detach=True)

                    else:
                        raise Exception('No one to reply to!')

                    # We have already sent the result, continue to next task
                    task.accept()
                    continue
            except:
                pass

            # No reply to, send result or error normally
            if err:
                task.sendError(err['code'], err['message'], None)
                continue

            task.sendResult(res)
