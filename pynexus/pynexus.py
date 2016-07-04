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

from jsocket import JSocketDecoder
import json
from multiprocessing import Queue
import select
import socket
import threading
from urlparse import urlparse
import time

# Constants
ErrParse            = -32700
ErrInvalidRequest   = -32600
ErrMethodNotFound   = -32601
ErrInvalidParams    = -32602
ErrInternal         = -32603
ErrTimeout          = -32000
ErrCancel           = -32001
ErrInvalidTask      = -32002
ErrInvalidPipe      = -32003
ErrInvalidUser      = -32004
ErrUserExists       = -32005
ErrPermissionDenied = -32010
ErrUnknownError     = -32098
ErrNotSupported     = -32099

ErrStr = {
    ErrParse:            "Parse error",
    ErrInvalidRequest:   "Invalid request",
    ErrMethodNotFound:   "Method not found",
    ErrInvalidParams:    "Invalid params",
    ErrInternal:         "Internal error",
    ErrTimeout:          "Timeout",
    ErrCancel:           "Cancel",
    ErrInvalidTask:      "Invalid task",
    ErrInvalidPipe:      "Invalid pipe",
    ErrInvalidUser:      "Invalid user",
    ErrUserExists:       "User already exists",
    ErrPermissionDenied: "Permission denied",
    ErrUnknownError:     "Unknown error",
    ErrNotSupported:     "Not supported",
}

class NexusConn:
    def pushRequest(self, request):
        self.qRequests.put(request)
        return None

    def pullRequest(self):
        return self.qRequests.get(), None

    def registerChannel(self, task_id, channel):
        with self.resTableLock:
            self.resTable[task_id] = channel

    def getChannel(self, task_id):
        res = None
        with self.resTableLock:
            res = self.resTable.get(task_id)
        return res

    def unregisterChannel(self, task_id):
        with self.resTableLock:
            if task_id in self.resTable:
                del self.resTable[task_id]

    def cancelChannels(self):
        with self.resTableLock:
            for channel in self.resTable.itervalues():
                channel.put({u'jsonrpc': u'2.0', u'id': None, u'error': {u'code': ErrCancel, u'message': ErrStr[ErrCancel]}})

    def getTimeToNextPing(self):
        now = time.time()
        return self.lastRead + self.keepAlive - now

    def resetTimeToNextPing(self):
        self.lastRead = time.time()

    def mainWorker(self, pipe):
        try:
            while True:
                delay = self.getTimeToNextPing()
                ready = select.select([pipe._reader], [], [], delay)
                if ready[0] and ready[0][0] == pipe._reader:
                    break
                else:
                    delay = self.getTimeToNextPing()
                    if delay <= 0:
                        error = self.ping(self.keepAlive)
                        if error:
                            raise Exception("Error in ping", error)
                            
        finally:
            self.cancel()

    def sendWorker(self, pipe):
        try:
            while True:
                ready = select.select([self.qRequests._reader, pipe._reader], [], [])
                if ready[0]:
                    if ready[0][0] == pipe._reader:
                        break
                    else:
                        request, error = self.pullRequest()
                        if error:
                            break
                        request['jsonrpc'] = '2.0'
                        with self.connLock:
                            self.conn.send(json.dumps(request))
        finally:
            self.cancel()

    def recvWorker(self, pipe):
        try:
            decoder = JSocketDecoder(self.conn)
            while True:
                ready = select.select([self.conn, pipe._reader], [], [])
                if ready[0]:
                    if ready[0][0] == pipe._reader:
                        break
                    else:
                        message = decoder.getObject()
                        self.resetTimeToNextPing()
                        if message:
                            channel = self.getChannel(message['id'])
                            if channel:
                                channel.put(message)
        finally:
            self.cancel()

    def newId(self):
        self.lastTaskId += 1
        new_id = self.lastTaskId
        new_channel = Queue()
        self.registerChannel(new_id, new_channel)
        return new_id, new_channel

    def delId(self, task_id):
        self.unregisterChannel(task_id)

    def __init__(self, conn, keepAlive=60):
        self.conn = conn
        self.connLock = threading.Lock()
        self.qRequests = Queue()
        self.keepAlive = keepAlive
        self.resTable = {}
        self.resTableLock = threading.Lock()
        self.lastTaskId = 0
        self.stopping = False
        self.workers = []
        self.lastRead = time.time()

        self.startWorker(self.sendWorker)
        self.startWorker(self.recvWorker)
        self.startWorker(self.mainWorker)

    def startWorker(self, target):
        pipe = Queue()
        worker = threading.Thread(target=target, args=(pipe,))
        worker.start()
        self.workers.append((worker, pipe))

    def cancel(self):
        if self.stopping:
            return False

        # Cancel pull requests
        self.cancelChannels()
        
        # Stop workers
        self.stopping = True
        for worker, pipe in self.workers:
            if worker != threading.current_thread():
                pipe.put("exit")
                worker.join()
        self.workers = []

        return True

    def executeNoWait(self, method, params):
        task_id, channel = self.newId()
        req = {
            'id': task_id,
            'method': method,
            'params': params,
        }
        err = self.pushRequest(req)
        if err:
            self.delId(task_id)
            return 0, None, err
        return task_id, channel, None

    def execute(self, method, params):
        task_id, channel, err = self.executeNoWait(method, params)
        if err:
            return None, err
        res = channel.get()
        self.delId(task_id)
        if 'error' in res:
            return None, res['error']
        else:
            return res['result'], None
    
    def ping(self, timeout):
        task_id, channel, err = self.executeNoWait('sys.ping', None)
        if err:
            return err
        try:
            channel.get(True, timeout)
            self.delId(task_id)
            return None
        except Exception as e:
            self.delId(task_id)
            return e
    
    def login(self, username, password):
        return self.execute('sys.login', {'user': username, 'pass': password})
            
    def taskPush(self, method, params, timeout=0, priority=0, detach=False):
        message = {
            'method': method,
            'params': params,
        }

        if priority != 0:
            message['prio'] = priority
        if detach:
            message['detach'] = True
        if timeout > 0:
            message['timeout'] = timeout

        return self.execute('task.push', message)

    def taskPull(self, prefix, timeout=0):
        message = {'prefix': prefix}
        
        if timeout > 0:
            message['timeout'] = timeout

        res, err = self.execute('task.pull', message)
        if err:
            return None, err

        task = Task(self, res['taskid'], res['path'], res['method'], res['params'], res['tags'])
        return task, None

    def pipeOpen(self, pipeid):
        return Pipe(self, pipeid), None

    def pipeCreate(self, length = -1):
        par = {}
        if length > 0:
            par["len"] = length

        res, err = self.execute("pipe.create", par)
        if err:
            return None, err

        return self.pipeOpen(res["pipeid"])

class Client:
    def __init__(self, url):
        nexusURL = urlparse(url)
    
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((nexusURL.hostname, nexusURL.port))

        self.nexusConn = NexusConn(self.socket)
        self.nexusConn.login(nexusURL.username, nexusURL.password)

    def taskPush(self, method, params, timeout=0, priority=0, detach=False):
        return self.nexusConn.taskPush(method, params, timeout=timeout, priority=priority, detach=detach)

    def taskPull(self, prefix, timeout=0):
        return self.nexusConn.taskPull(prefix, timeout=timeout)

    def cancel(self):
        self.nexusConn.cancel()

    def close(self):
        self.cancel()
        self.socket.close()
        self.socket = None

class Task:
    def __init__(self, nexusConn, taskId, path, method, params, tags):
        self.nexusConn = nexusConn
        self.taskId = taskId
        self.path = path
        self.method = method
        self.params = params
        self.tags = tags
        
    def sendResult(self, result):
        params = {
            'taskid': self.taskId,
            'result': result,
        }
        return self.nexusConn.execute('task.result', params)

    def sendError(self, code, message, data):
        if code < 0:
            if message != "":
                message = "%s:[%s]" % (ErrStr[code], message)
            else:
                message = ErrStr[code]

        params = {
            'taskid': self.taskId,
            'code': code,
            'message': message,
            'data': data,
        }
        return self.nexusConn.execute('task.error', params)

    def reject(self):
        """
        Reject the task. Task is returned to Nexus tasks queue.
        """
        params = {
            'taskid': self.taskId,
        }
        return self.nexusConn.execute('task.reject', params)

    def accept(self):
        """
        Accept a detached task.
        """
        return self.sendResult(None)

class Pipe:
    def __init__(self, nexusConn, pipeid):
        self.nexusConn = nexusConn
        self.pipeid = pipeid

    def close(self):
        return self.nexusConn.execute("pipe.close", {"pipeid": self.pipeid})

    def write(self, msg):
        return self.nexusConn.execute("pipe.write", {"pipeid": self.pipeid, "msg": msg})

    def read(self, mx, timeout):
        par = {"pipeid": self.pipeid, "max": mx, "timeout": timeout}
        res, err = self.nexusConn.execute("pipe.read", par)
        if err:
            return None, err

        try:
            msgres = []
            for msg in res["msgs"]:
                msgres.append(Msg(msg["count"], msg["msg"]))
        except:
            return None, {u'code': ErrInternal, u'message': ErrStr[ErrInternal]}

        return PipeData(msgres, res["waiting"], res["drops"]), None

    def id(self):
        return self.pipeid


class Msg:
    def __init__(self, count, msg):
        self.count = count
        self.msg = msg

class PipeData:
    def __init__(self, msgs, waiting, drops):
        self.msgs = msgs
        self.waiting = waiting
        self.drops = drops

class PipeOpts:
    def __init__(self, length):
        self.length = length

