# -*- coding: utf-8 -*-

import pynexus as nxpy
import unittest

class TestPynexus(unittest.TestCase):
    def test_pipes(self):
        pipe, err = client.nexusConn.pipeCreate()
        pipe.write("hello 0!")
        pipe.write("hello 1!")
        pipe.write("hello 2!")
        self.assertEqual(pipe.read(1, 10)[0].msgs[0].msg, "hello 0!")
        self.assertEqual(pipe.read(1, 10)[0].msgs[0].msg, "hello 1!")
        self.assertEqual(pipe.read(1, 10)[0].msgs[0].msg, "hello 2!")

if __name__ == "__main__":
    client = nxpy.Client("http://test:test@nexus.n4m.zone:1717")
    unittest.main(exit=False)
    client.cancel()
