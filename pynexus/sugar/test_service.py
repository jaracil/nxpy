# -*- coding: utf-8 -*-

import sys
sys.path.insert(0, '..')
import pynexus as nxpy
import unittest

from service import Service

class ServiceTester(Service):
    def test(self, task):
        return task.params, None

class TestService(unittest.TestCase):
    def test_1(self):
        self.assertEqual(client.taskPush("test.python.sugar.test1", {"test": "hola"})[0],
                                                                    {"test": "hola"})
    def test_2(self):
        self.assertEqual(client.taskPush("test.python.sugar.test2", {"test": "hola"})[1],
                {u'message': u'Method not found', u'code': -32601})

    def test_3(self):
        pipe, _ = client.nexusConn.pipeCreate()
        params = {"test": "hola", "replyTo": {"type": "pipe", "path": pipe.id()}}
        client.taskPush("test.python.sugar.test3", params, detach=True)
        res, err = pipe.read(1, 10)
        pipe.close()
        self.assertEqual(res.msgs[0].msg, {'error': None, 'result': params})

    def test_4(self):
        params = {"test": "hola", "replyTo": {"type": "service", "path": "test.python.ssugar.testreplyservice"}}
        client.taskPush("test.python.sugar.test4", params, detach=True)
        task, err = client.taskPull("test.python.ssugar", 2)
        task.accept()
        self.assertEqual(task.params, {'error': None, 'result': params})


if __name__ == "__main__":
    client = nxpy.Client("http://test:test@nexus.n4m.zone:1717")
    server = ServiceTester("http://test:test@nexus.n4m.zone:1717", "test.python.sugar", {"testing": True})
    server.add_method("test1", server.test)
    server.add_method("test3", server.test)
    server.add_method("test4", server.test)
    server.start()
    unittest.main(exit=False)
    server.stop()
    client.cancel()
