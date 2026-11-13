# 文件名: tests/test_save_service.py
"""Tests for core.save_service: Job -> profile JSON, no terminal needed."""

import json
import os
import shutil
import tempfile
import unittest
from types import SimpleNamespace

import profiles
from core import save_service


def _make_job(name="share-COM5", serial="COM5", tcp=1000):
    runner = SimpleNamespace(
        serial_port=serial,
        tcp_port=tcp,
        cfg={
            "baudrate": 115200,
            "bytesize": 8,
            "parity": "N",
            "stopbits": 1,
            "flow": "none",
        },
    )
    return SimpleNamespace(name=name, runner=runner)


class TestSaveService(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._orig_dir = profiles.profiles_dir
        profiles.profiles_dir = lambda: self.tmp

    def tearDown(self):
        profiles.profiles_dir = self._orig_dir
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _confirm_true(self, _p):
        return True

    def _confirm_false(self, _p):
        return False

    def test_save_one_creates(self):
        job = _make_job()
        r = save_service.save_one(job, "gd32", self._confirm_true)
        self.assertEqual(r.status, "saved")
        self.assertFalse(r.existed)
        with open(os.path.join(self.tmp, "gd32.json"), encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["serial_port"], "COM5")
        self.assertEqual(data["tcp_port"], 1000)

    def test_save_one_skips(self):
        path = os.path.join(self.tmp, "gd32.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write('{"serial_port": "OLD"}')
        job = _make_job()
        r = save_service.save_one(job, "gd32", self._confirm_false)
        self.assertEqual(r.status, "skipped")
        with open(path, encoding="utf-8") as f:
            self.assertEqual(f.read(), '{"serial_port": "OLD"}')

    def test_save_one_overwrites(self):
        path = os.path.join(self.tmp, "gd32.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write('{"serial_port": "OLD"}')
        job = _make_job()
        r = save_service.save_one(job, "gd32", self._confirm_true)
        self.assertEqual(r.status, "saved")
        self.assertTrue(r.existed)

    def test_save_all_auto_yes(self):
        jobs = [
            _make_job("share-COM5", "COM5", 1000),
            _make_job("share-COM7", "COM7", 1001),
        ]
        results = save_service.save_all(jobs, True, self._confirm_false)
        self.assertEqual([r.status for r in results], ["saved", "saved"])
        self.assertTrue(os.path.exists(
            os.path.join(self.tmp, "share-COM5.json")))
        self.assertTrue(os.path.exists(
            os.path.join(self.tmp, "share-COM7.json")))

    def test_save_all_respects_confirm(self):
        jobs = [_make_job("share-COM5", "COM5", 1000)]
        with open(os.path.join(self.tmp, "share-COM5.json"), "w") as f:
            f.write("{}")
        results = save_service.save_all(jobs, False, self._confirm_false)
        self.assertEqual(results[0].status, "skipped")


if __name__ == "__main__":
    unittest.main()