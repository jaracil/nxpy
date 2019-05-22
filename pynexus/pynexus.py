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

import atexit
from .jsocket import JSocketDecoder
import json
import multiprocessing
try:
    from queue import Queue
except ImportError:
    from Queue import Queue
from . import net
import select
import threading
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
import time
from .version import __version__

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
ErrTtlExpired       = -32011
ErrUnknownError     = -32098
ErrNotSupported     = -32099
ErrConnClosed       = -32007

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
    ErrTtlExpired:       "TTL expired",
    ErrUnknownError:     "Unknown error",
    ErrNotSupported:     "Not supported",
    ErrConnClosed:       "Connection is closed",
}

class NexusConn(object):
    def pushRequest(self, request):
        self.requests[1].send(request)
        return None

    def pullRequest(self):
        return self.requests[0].recv(), None

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
            for channel in self.resTable.values():
                channel.put({u'jsonrpc': u'2.0', u'id': None, u'error': {u'code': ErrConnClosed, u'message': ErrStr[ErrConnClosed]}})

    def getTimeToNextPing(self):
        now = time.time()
        return self.lastRead + self.keepAlive - now

    def resetTimeToNextPing(self):
        self.lastRead = time.time()

    def mainWorker(self, pipe):
        try:
            while True:
                delay = self.getTimeToNextPing()
                ready = select.select([pipe[0]], [], [], delay)
                if ready[0] and ready[0][0] == pipe[0]:
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
                ready = select.select([self.requests[0], pipe[0]], [], [])
                if ready[0]:
                    if ready[0][0] == pipe[0]:
                        break
                    else:
                        request, error = self.pullRequest()
                        if error:
                            break
                        request['jsonrpc'] = '2.0'
                        with self.connLock:
                            self.conn.send(json.dumps(request).encode())
        finally:
            self.cancel()

    def recvWorker(self, pipe):
        try:
            decoder = JSocketDecoder(self.conn)
            while True:
                ready = select.select([decoder, pipe[0]], [], [])
                if ready[0]:
                    if ready[0][0] == pipe[0]:
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

    def newId(self, taskId=None):
        new_id = taskId
        if not new_id:
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
        self.requests = multiprocessing.Pipe(False)
        self.keepAlive = keepAlive
        self.resTable = {}
        self.resTableLock = threading.Lock()
        self.lastTaskId = 0
        self.workers = []
        self.lastRead = time.time()

        self._stopping = False
        self._stoppingLock = threading.Lock()

        self.startWorker(self.sendWorker)
        self.startWorker(self.recvWorker)
        self.startWorker(self.mainWorker)

        atexit.register(self.cancel)

    def startWorker(self, target):
        pipe = multiprocessing.Pipe(False)
        worker = threading.Thread(target=target, args=(pipe,))
        worker.daemon = True
        worker.start()
        self.workers.append((worker, pipe))

    def cancel(self):
        with self._stoppingLock:
            if self._stopping:
                return False
            self._stopping = True

        # Cancel pull requests
        self.cancelChannels()
        
        # Stop workers
        for worker, pipe in self.workers:
            if worker != threading.current_thread():
                pipe[1].send("exit")
                worker.join()
        self.workers = []

        return True

    def executeNoWait(self, method, params, taskId=None):
        with self._stoppingLock:
            if self._stopping:
                return 0, None, {u'code': ErrConnClosed, u'message': ErrStr[ErrConnClosed]}
            task_id, channel = self.newId(taskId=taskId)
        req = {
            'id':     task_id,
            'method': method,
            'params': params,
        }
        err = self.pushRequest(req)
        if err:
            self.delId(task_id)
            return 0, None, err
        return task_id, channel, None

    def execute(self, method, params, taskId=None):
        task_id, channel, err = self.executeNoWait(method, params, taskId=taskId)
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
            
    def taskPush(self, method, params, timeout=0, priority=0, ttl=0, detach=False):
        message = {
            'method': method,
            'params': params,
        }

        if priority != 0:
            message['prio'] = priority
        if ttl != 0:
            message['ttl'] = ttl
        if detach:
            message['detach'] = True
        if timeout > 0:
            message['timeout'] = timeout

        return self.execute('task.push', message)

    def taskPushCh(self, method, params, timeout=0, priority=0, ttl=0, detach=False):
        resQueue = Queue()
        errQueue = Queue()

        def callTaskPush():
            res, err = self.taskPush(method, params, timeout=timeout, priority=priority, ttl=ttl, detach=detach)
            if err:
                errQueue.put(err)
            else:
                resQueue.put(res)

        threading.Thread(target=callTaskPush).start()
        return resQueue, errQueue

    def taskPull(self, prefix, timeout=0, taskId=None):
        message = {'prefix': prefix}
        
        if timeout > 0:
            message['timeout'] = timeout

        res, err = self.execute('task.pull', message, taskId=taskId)
        if err:
            return None, err

        task = Task(
            self,
            res['taskid'],
            res['path'],
            res['method'],
            res['params'],
            res['tags'],
            res['prio'],
            res['detach'],
            res['user']
        )
        return task, None

    def cancelPull(self, taskId):
        return self.execute('task.cancel', {'id': taskId})

    def taskPullCh(self, prefix, timeout=0):
        resQueue = Queue()
        errQueue = Queue()

        def callTaskPull():
            task, err = self.taskPull(prefix, timeout=timeout)
            if err:
                errQueue.put(err)
            else:
                resQueue.put(res)

        threading.Thread(target=callTaskPull).start()
        return resQueue, errQueue

    def userCreate(self, username, password):
        return self.execute('user.create', {'user': username, 'pass': password})

    def userDelete(self, username):
        return self.execute('user.delete', {'user': username})

    def userSetTags(self, username, prefix, tags):
        return self.execute('user.setTags', {'user': username, 'prefix': prefix, 'tags': tags})

    def userDelTags(self, username, prefix, tags):
        return self.execute('user.delTags', {'user': username, 'prefix': prefix, 'tags': tags})

    def userSetPass(self, username, password):
        return self.execute('user.setPass', {'user': username, 'pass': password})

    def pipeOpen(self, pipeId):
        return Pipe(self, pipeId), None

    def pipeCreate(self, length = -1):
        par = {}
        if length > 0:
            par["len"] = length

        res, err = self.execute("pipe.create", par)
        if err:
            return None, err

        return self.pipeOpen(res["pipeid"])

    def topicSubscribe(self, pipe, topic):
        return self.execute('topic.sub', {'pipeid': pipe.pipeId, 'topic': topic})

    def topicUnsubscribe(self, pipe, topic):
        return self.execute('topic.unsub', {'pipeid': pipe.pipeId, 'topic': topic})

    def topicPublish(self, topic, message):
        return self.execute('topic.pub', {'topic': topic, 'msg': message})

    def lock(self, name):
        res, err = self.execute('sync.lock', {'lock': name})
        if err:
            return None, err
        else:
            return bool(res['ok']), None

    def unlock(self, name):
        res, err = self.execute('sync.unlock', {'lock': name})
        if err:
            return None, err
        else:
            return bool(res['ok']), None

    def _getNexusVersion(self):
        res, err = self.execute("sys.version", None)
        if err == None and isinstance(res, dict) and "version" in res and isinstance(res["version"], str):
            return res["version"]
        return "0.0.0"


class Client(NexusConn):
    def __init__(self, url, keepAlive=60):
        nexusURL = urlparse(url)
        self.hostname = nexusURL.hostname
        self.port = nexusURL.port
        self.scheme = nexusURL.scheme
        self.username = nexusURL.username
        self.password = nexusURL.password
        
        self.is_logged = False
        self.login_error = None
        self.connid = None
        self.nexus_version = "0.0.0"
        self.is_version_compatible = False

        self._closing = False
        self._closingLock = threading.Lock()

        self.socket = net.connect(self.hostname, self.port, self.scheme)
        super(Client, self).__init__(self.socket, keepAlive=keepAlive)
        self.nexusConn = self  # for backward compatibility

        err = self.ping(20)
        if err != None:
            raise Exception(err)

        if self.username != None and self.password != None:
            self.login()

        self.nexus_version = self._getNexusVersion()
        self.is_version_compatible = self.nexus_version.split(".")[0] == __version__.split(".")[0]

        atexit.register(self.close)

    def login(self):
        res, err = super(Client, self).login(self.username, self.password)
        if err:
            self.is_logged = False
            self.login_error = err
            self.connid = None
        else:
            self.is_logged = True
            self.login_error = None
            self.connid = res['connid']

    def close(self):
        with self._closingLock:
            if self._closing:
                return False
            self._closing = True

        self.cancel()
        if self.socket:
            self.socket.close()
            self.socket = None


class Task(object):
    def __init__(self, nexusConn, taskId, path, method, params, tags, priority, detach, user):
        self.nexusConn = nexusConn
        self.taskId = taskId
        self.path = path
        self.method = method
        self.params = params
        self.tags = tags
        self.priority = priority
        self.detach = detach
        self.user = user
        
    def sendResult(self, result):
        params = {
            'taskid': self.taskId,
            'result': result,
        }
        return self.nexusConn.execute('task.result', params)

    def sendError(self, code, message, data):
        if code < 0:
            if code in ErrStr:
                if message != "":
                    message = "%s:[%s]" % (ErrStr[code], message)
                else:
                    message = ErrStr[code]

        params = {
            'taskid':  self.taskId,
            'code':    code,
            'message': message,
            'data':    data,
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

    
class Pipe(object):
    def __init__(self, nexusConn, pipeId):
        self.nexusConn = nexusConn
        self.pipeId = pipeId

    def close(self):
        return self.nexusConn.execute("pipe.close", {"pipeid": self.pipeId})

    def write(self, msg):
        return self.nexusConn.execute("pipe.write", {"pipeid": self.pipeId, "msg": msg})

    def read(self, mx, timeout=0):
        par = {"pipeid": self.pipeId, "max": mx, "timeout": timeout}
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

    def listen(self, channel=None):
        if channel is None:
            channel = Queue()

        def pipeReader():
            try:
                while True:
                    data, err = self.read(100000)
                    if err:
                        break
                    for message in data.msgs:
                        channel.put(message)
            except:
                pass

        threading.Thread(target=pipeReader).start()
        return channel

    def id(self):
        return self.pipeId


class Msg(object):
    def __init__(self, count, msg):
        self.count = count
        self.msg = msg

        
class PipeData(object):
    def __init__(self, msgs, waiting, drops):
        self.msgs = msgs
        self.waiting = waiting
        self.drops = drops

        
class PipeOpts(object):
    def __init__(self, length):
        self.length = length
