# -*- coding: utf-8 -*-

import sys
sys.path.insert(0, '..')
import pynexus as nxpy
import unittest

from service import Service

class ServiceTester(Service):
    def test1(self, task):
        task.sendResult(task.params)

class TestService(unittest.TestCase):
    def test_1(self):
        self.assertEqual(client.taskPush("test.python.sugar.test1", {"test": "hola"})[0]["result"],
                                                                    {"test": "hola"})

if __name__ == "__main__":
    client = nxpy.Client("http://root:root@nexus.n4m.zone:1717")
    server = ServiceTester("http://root:root@nexus.n4m.zone:1717", "test.python.sugar")
    server.add_method("test1", server.test1)
    server.start()
    unittest.main(exit=False)
    server.stop()
    client.cancel()
