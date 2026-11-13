# 文件名: tests/test_profiles.py
"""Tests for profiles.load_profile / save_profile / profile_path."""

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

    def test_profile_path_adds_ext(self):
        self.assertTrue(profiles.profile_path("x").endswith("x.json"))
        self.assertTrue(profiles.profile_path("x.json").endswith("x.json"))

    def test_profile_path_empty(self):
        with self.assertRaises(ProfileError):
            profiles.profile_path("")

    def test_profile_path_rejects_forward_slash(self):
        with self.assertRaises(ProfileError):
            profiles.profile_path("../evil")

    def test_profile_path_rejects_backslash(self):
        with self.assertRaises(ProfileError):
            profiles.profile_path("..\\evil")

    def test_profile_path_rejects_parent_dir(self):
        with self.assertRaises(ProfileError):
            profiles.profile_path("..")

    def test_profile_path_rejects_absolute(self):
        with self.assertRaises(ProfileError):
            profiles.profile_path("C:\\Windows\\System32\\evil")

    def test_profile_path_rejects_subdir(self):
        with self.assertRaises(ProfileError):
            profiles.profile_path("sub/gd32")

    def test_profile_path_stays_under_profiles(self):
        p = profiles.profile_path("ok")
        self.assertTrue(
            os.path.realpath(p).startswith(
                os.path.realpath(self.tmp) + os.sep))

    def test_load_valid(self):
        self._write("gd32.json", {
            "serial_port": "COM5", "tcp_port": 1000,
        })
        data = profiles.load_profile("gd32")
        self.assertEqual(data["serial_port"], "COM5")
        self.assertEqual(data["tcp_port"], 1000)

    def test_load_without_tcp_port(self):
        self._write("auto.json", {"serial_port": "COM5"})
        data = profiles.load_profile("auto")
        self.assertNotIn("tcp_port", data)

    def test_load_missing_file(self):
        with self.assertRaises(ProfileError):
            profiles.load_profile("nope")

    def test_load_bad_json(self):
        with open(os.path.join(self.tmp, "bad.json"), "w") as f:
            f.write("{not json")
        with self.assertRaises(ProfileError):
            profiles.load_profile("bad")

    def test_load_non_utf8(self):
        path = os.path.join(self.tmp, "latin1.json")
        with open(path, "wb") as f:
            f.write(b'{"serial_port": "COM5"}\xff')
        with self.assertRaises(ProfileError):
            profiles.load_profile("latin1")

    def test_load_non_object(self):
        self._write("array.json", [1, 2, 3])
        with self.assertRaises(ProfileError):
            profiles.load_profile("array")

    def test_require_fields_ok(self):
        profiles.require_fields({"a": 1, "b": 2}, "a", "b")

    def test_require_fields_missing(self):
        with self.assertRaises(ProfileError):
            profiles.require_fields({"a": 1}, "a", "b")

    def test_save_profile_creates_file(self):
        full, existed = profiles.save_profile("newone", {
            "serial_port": "COM5",
        })
        self.assertFalse(existed)
        self.assertTrue(os.path.exists(full))

    def test_save_profile_overwrites(self):
        profiles.save_profile("dup", {"serial_port": "COM5"})
        full, existed = profiles.save_profile("dup", {"serial_port": "COM7"})
        self.assertTrue(existed)
        loaded = profiles.load_profile("dup")
        self.assertEqual(loaded["serial_port"], "COM7")

    def test_save_profile_empty_name(self):
        with self.assertRaises(ProfileError):
            profiles.save_profile("", {"serial_port": "COM5"})

    def test_save_profile_rejects_traversal(self):
        with self.assertRaises(ProfileError):
            profiles.save_profile("../escape", {"serial_port": "COM5"})


if __name__ == "__main__":
    unittest.main()