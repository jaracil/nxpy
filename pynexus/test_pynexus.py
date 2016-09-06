# -*- coding: utf-8 -*-

import pynexus as nxpy
import threading
import unittest
from unittest import TextTestRunner
import os
import sys

class TestPynexus(unittest.TestCase):
    def test_cancel_pull(self):
        def callPull():
            task, err = client.taskPull('test.pull', taskId='private_id')
            self.assertEqual(err['code'], -32001)
        threading.Thread(target=callPull).start()
        client.cancelPull('private_id')

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

    def test_urls(self):
        urls = [
            "tcp://root:root@%s:%s" % (os.environ.get("NEXUS_HOST", "localhost"), os.environ.get("NEXUS_TCP_PORT", "1717")),
            "ssl://root:root@%s:%s" % (os.environ.get("NEXUS_HOST", "localhost"), os.environ.get("NEXUS_SSL_PORT", "1718")),
            "ws://root:root@%s:%s" % (os.environ.get("NEXUS_HOST", "localhost"), os.environ.get("NEXUS_HTTP_PORT", "80")),
            "wss://root:root@%s:%s" % (os.environ.get("NEXUS_HOST", "localhost"), os.environ.get("NEXUS_HTTPS_PORT", "443")),
        ]
        for url in urls:
            cli = nxpy.Client(url)
            self.assertEqual(cli.nexusConn.ping(1), None)
            cli.close()


if __name__ == "__main__":
    client = nxpy.Client("http://root:root@%s:%s" % (os.environ.get("NEXUS_HOST", "localhost"),
                                                     os.environ.get("NEXUS_HTTP_PORT", "80")))
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestPynexus)
    test_result = TextTestRunner().run(test_suite)
    client.close()
    if not test_result.wasSuccessful():
        sys.exit(1)
