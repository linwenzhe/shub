# 文件名: tests/test_share_args.py
"""Tests for core.share_args.parse_share."""

import json
import os
import shutil
import tempfile
import unittest

import profiles
from core.errors import ShubError
from core.share_args import parse_share


class TestParseShare(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._orig_dir = profiles.profiles_dir
        profiles.profiles_dir = lambda: self.tmp

    def tearDown(self):
        profiles.profiles_dir = self._orig_dir
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, name, data):
        with open(os.path.join(self.tmp, name), "w",
                  encoding="utf-8") as f:
            json.dump(data, f)

    def test_direct_with_tcp(self):
        result = parse_share("COM5 --tcp 1000")
        serial, tcp, cfg = result
        self.assertEqual(serial, "COM5")
        self.assertEqual(tcp, 1000)

    def test_direct_without_tcp(self):
        serial, tcp, _ = parse_share("COM5")
        self.assertEqual(serial, "COM5")
        self.assertIsNone(tcp)

    def test_direct_with_serial_options(self):
        serial, tcp, cfg = parse_share(
            "COM5 --tcp 1000 --baud 9600 --bytesize 7 --parity E")
        self.assertEqual(serial, "COM5")
        self.assertEqual(tcp, 1000)
        self.assertEqual(cfg["baudrate"], 9600)
        self.assertEqual(cfg["bytesize"], 7)
        self.assertEqual(cfg["parity"], "E")

    def test_profile(self):
        self._write("gd32.json", {
            "serial_port": "COM5", "tcp_port": 1000,
        })
        serial, tcp, _ = parse_share("--profile gd32")
        self.assertEqual(serial, "COM5")
        self.assertEqual(tcp, 1000)

    def test_from_is_equivalent(self):
        self._write("gd32.json", {
            "serial_port": "COM5", "tcp_port": 1000,
        })
        serial, tcp, _ = parse_share("--from gd32")
        self.assertEqual(serial, "COM5")
        self.assertEqual(tcp, 1000)

    def test_profile_without_tcp_port(self):
        self._write("auto.json", {"serial_port": "COM5"})
        serial, tcp, _ = parse_share("--profile auto")
        self.assertEqual(serial, "COM5")
        self.assertIsNone(tcp)

    def test_profile_conflict_with_tcp(self):
        self._write("gd32.json", {
            "serial_port": "COM5", "tcp_port": 1000,
        })
        with self.assertRaises(ShubError):
            parse_share("--profile gd32 --tcp 1001")

    def test_tcp_port_zero(self):
        with self.assertRaises(ShubError):
            parse_share("COM5 --tcp 0")

    def test_tcp_port_too_large(self):
        with self.assertRaises(ShubError):
            parse_share("COM5 --tcp 65536")

    def test_missing_serial(self):
        with self.assertRaises(ShubError):
            parse_share("--tcp 1000")

    def test_empty(self):
        with self.assertRaises(ShubError):
            parse_share("")


if __name__ == "__main__":
    unittest.main()