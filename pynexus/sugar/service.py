# -*- coding: utf-8 -*-

from __future__ import print_function
import sys
sys.path.insert(0, '..')
import threading
import pynexus as nxpy
from datetime import datetime

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

class Server(object):
    def __init__(self, url):
        self.url      = url
        self.services = []

    def add_service(self, prefix, options = {}):
        service = Service("", prefix, options)
        self.services.append(service)
        return service

    def start(self):
        eprint("[{t}] Starting nexus server...".format(t=datetime.now()))

        self.nxClient = nxpy.Client(self.url)
        if self.nxClient.is_logged:
            eprint("[{t}] Login to Nexus. Connection ID: {connid}.".format(t=datetime.now(), connid=self.nxClient.connid))
        else:
            eprint("[{t}] Login to Nexus fail: {e}.".format(t=datetime.now(), e=self.nxClient.login_error))

        for service in self.services:
            service.start_with_connection(self.nxClient)

    def wait(self):
        try:
            for worker, _ in self.nxClient.workers:
                worker.join()
        except:
            self.nxClient.close()

    def stop(self):
        self.nxClient.close()


class Service(object):
    def __init__(self, url, path, options = {}):
        self.url  = url
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
        return self.nxClient

    def start_with_connection(self, nxClient):
        self.nxClient = nxClient
        try:
            for i in range(self.pulls):
                worker = threading.Thread(target = self.server, args = (self.nxClient, self.path))
                worker.daemon = True
                worker.start()
        except:
            self.nxClient.close()

    def start(self):
        self.nxClient = nxpy.Client(self.url)

        try:
            for i in range(self.pulls):
                worker = threading.Thread(target = self.server, args = (self.nxClient, self.path))
                worker.daemon = True
                worker.start()
        except:
            self.nxClient.close()

    def wait(self):
        try:
            for worker, _ in self.nxClient.workers:
                worker.join()
        except:
            self.stop()

    def stop(self):
        self.nxClient.close()

    def server(self, nxClient, prefix):
        while True:
            task, err = nxClient.taskPull(prefix, self.pulltimeout)
            if err:
                if self.testing:
                    return
                if err["code"] == nxpy.ErrTimeout:
                    continue
                nxClient.close()
                eprint("[{t}] Error during taskpull: {e}.".format(t=datetime.now(), e = err))
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
                        pipe, _ = nxClient.pipeOpen(reply["path"])
                        try:
                            if err['code'] in nxpy.ErrStr.keys():
                                err['message'] = nxpy.ErrStr[err['code']]
                        except:
                            pass
                        pipe.write({'result': res, 'error': err, 'task': {
                            "path": task.path,
                            "method": task.method,
                            "params": task.params,
                            "tags": task.tags,
                        }})

                    elif reply["type"] == "service":
                        try:
                            if err['code'] in nxpy.ErrStr.keys():
                                err['message'] = nxpy.ErrStr[err['code']]
                        except:
                            pass
                        nxClient.taskPush(reply["path"], {'result': res, 'error': err, 'task': {
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
