# -*- coding: utf-8 -*-

import sys
sys.path.insert(0, '..')
import pynexus as nxpy
import unittest

from service import Service, Server

def test(task):
    return task.params, None

class TestServer(unittest.TestCase):
    def test_1(self):
        self.assertEqual(client.taskPush("test.python.sugar1.test", {"test": "hola"})[0],
                                                                    {"test": "hola"})

    def test_2(self):
        self.assertEqual(client.taskPush("test.python.sugar2.test", {"test": "hola"})[0],
                                                                    {"test": "hola"})

    def test_3(self):
        self.assertEqual(client.taskPush("test.python.sugar3.test", {"test": "hola"})[0],
                                                                    {"test": "hola"})

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
        del(res.msgs[0].msg["task"])
        self.assertEqual(res.msgs[0].msg, {'error': None, 'result': params})

    def test_4(self):
        params = {"test": "hola", "replyTo": {"type": "service", "path": "test.python.ssugar.testreplyservice"}}
        client.taskPush("test.python.sugar.test4", params, detach=True)
        task, err = client.taskPull("test.python.ssugar", 2)
        task.accept()
        del(task.params["task"])
        self.assertEqual(task.params, {'error': None, 'result': params})


if __name__ == "__main__":
    client = nxpy.Client("tcp://root:root@localhost:1717")

    # Standalone services
    service = Service("tcp://root:root@localhost:1717", "test.python.sugar", {"testing": True})
    service.add_method("test1", test)
    service.add_method("test3", test)
    service.add_method("test4", test)
    service.start()

    # Server with services sharing one connection
    server = Server("tcp://root:root@localhost:1717")

    service1 = server.add_service("test.python.sugar1", {"testing": True})
    service1.add_method("test", test)

    service2 = server.add_service("test.python.sugar2", {"testing": True})
    service2.add_method("test", test)

    service3 = server.add_service("test.python.sugar3", {"testing": True})
    service3.add_method("test", test)

    server.start()

    # Run tests and stop everything
    unittest.main(exit=False)
    service.stop()
    server.stop()
    client.cancel()
