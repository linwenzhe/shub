# 文件名: tests/test_profiles.py
"""Tests for profiles.load_profile and helpers."""

import json
import os
import shutil
import tempfile
import unittest

import profiles
from core.errors import ProfileError


class TestProfiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._orig_dir = profiles.profiles_dir
        profiles.profiles_dir = lambda: self.tmp

    def tearDown(self):
        profiles.profiles_dir = self._orig_dir
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, name, data):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return path

    def test_load_valid_serve(self):
        self._write("gd32.json", {
            "type": "serve", "serial_port": "COM5", "tcp_port": 1000,
        })
        data = profiles.load_profile("gd32")
        self.assertEqual(data["type"], "serve")
        self.assertEqual(data["serial_port"], "COM5")

    def test_load_with_extension(self):
        self._write("gd32.json", {
            "type": "serve", "serial_port": "COM5", "tcp_port": 1000,
        })
        data = profiles.load_profile("gd32.json")
        self.assertEqual(data["type"], "serve")

    def test_load_missing_file(self):
        with self.assertRaises(ProfileError):
            profiles.load_profile("nope")

    def test_load_empty_name(self):
        with self.assertRaises(ProfileError):
            profiles.load_profile("")

    def test_load_bad_json(self):
        with open(os.path.join(self.tmp, "bad.json"), "w") as f:
            f.write("{not json")
        with self.assertRaises(ProfileError):
            profiles.load_profile("bad")

    def test_load_missing_type(self):
        self._write("notype.json", {"serial_port": "COM5"})
        with self.assertRaises(ProfileError):
            profiles.load_profile("notype")

    def test_load_unknown_type(self):
        self._write("unknown.json", {"type": "other"})
        with self.assertRaises(ProfileError):
            profiles.load_profile("unknown")

    def test_require_fields_ok(self):
        profiles.require_fields({"a": 1, "b": 2}, "a", "b")

    def test_require_fields_missing(self):
        with self.assertRaises(ProfileError):
            profiles.require_fields({"a": 1}, "a", "b")

    def test_password_from_profile_explicit(self):
        self.assertEqual(
            profiles.password_from_profile({"password": "abc"}), "abc")

    def test_password_from_profile_default(self):
        from config import DEFAULT_PASSWORD
        self.assertEqual(
            profiles.password_from_profile({}), DEFAULT_PASSWORD)

    def test_password_from_profile_no_password(self):
        self.assertIsNone(
            profiles.password_from_profile({"no_password": True}))


if __name__ == "__main__":
    unittest.main()