# -*- coding: utf-8 -*-

import pynexus as nxpy
import unittest

class TestPynexus(unittest.TestCase):
    def test_pipes(self):
        pipe, _ = client.nexusConn.pipeCreate()
        pipe.write("hello 0!")
        pipe.write("hello 1!")
        pipe.write("hello 2!")
        self.assertEqual(pipe.read(1, 10)[0].msgs[0].msg, "hello 0!")
        self.assertEqual(pipe.read(1, 10)[0].msgs[0].msg, "hello 1!")
        self.assertEqual(pipe.read(1, 10)[0].msgs[0].msg, "hello 2!")

        channel = pipe.listen()
        pipe.write("hello 3!")
        pipe.write("hello 4!")
        pipe.write("hello 5!")
        self.assertEqual(channel.get().msg, "hello 3!")
        self.assertEqual(channel.get().msg, "hello 4!")
        self.assertEqual(channel.get().msg, "hello 5!")

        pipe.close()

if __name__ == "__main__":
    nexus_urls = [
        "tcp://root:root@localhost:1717",
        "tcp://root:root@localhost",
    ]
    for nexus_url in nexus_urls:
        client = nxpy.Client(nexus_url)
        unittest.main(exit=False)
        client.close()
