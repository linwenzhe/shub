# 文件名: tests/test_handshake.py
"""Round-trip tests for core.handshake using socketpair."""

import socket
import threading
import unittest

from core.handshake import server_handshake, client_handshake


class TestHandshake(unittest.TestCase):
    def _pair(self):
        return socket.socketpair()

    def test_no_password(self):
        a, b = self._pair()
        try:
            self.assertTrue(server_handshake(a, None))
            self.assertTrue(client_handshake(b, None))
        finally:
            a.close()
            b.close()

    def test_correct_password(self):
        a, b = self._pair()
        result = {}

        def srv():
            result["ok"] = server_handshake(a, "abc")

        t = threading.Thread(target=srv)
        t.start()
        try:
            ok = client_handshake(b, "abc")
            t.join(timeout=3)
            self.assertTrue(ok)
            self.assertTrue(result.get("ok"))
        finally:
            a.close()
            b.close()

    def test_wrong_password(self):
        a, b = self._pair()
        result = {}

        def srv():
            result["ok"] = server_handshake(a, "abc")

        t = threading.Thread(target=srv)
        t.start()
        try:
            ok = client_handshake(b, "wrong")
            t.join(timeout=3)
            self.assertFalse(ok)
            self.assertFalse(result.get("ok"))
        finally:
            a.close()
            b.close()

    def test_server_closes_before_password(self):
        a, b = self._pair()
        b.close()
        try:
            self.assertFalse(server_handshake(a, "abc"))
        finally:
            a.close()


if __name__ == "__main__":
    unittest.main()