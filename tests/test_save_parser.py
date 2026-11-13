# 文件名: tests/test_save_parser.py
"""Tests for core.save_parser.parse_save."""

import unittest

from core.save_parser import parse_save


class TestParseSave(unittest.TestCase):
    def test_empty_is_usage(self):
        self.assertEqual(parse_save([]).mode, "usage")

    def test_help(self):
        self.assertEqual(parse_save(["-h"]).mode, "help")
        self.assertEqual(parse_save(["--help"]).mode, "help")

    def test_save_profile(self):
        cmd = parse_save(["gd32"])
        self.assertEqual(cmd.mode, "auto")
        self.assertEqual(cmd.profile_name, "gd32")

    def test_save_job_as_profile(self):
        cmd = parse_save(["share-COM5", "as", "gd32"])
        self.assertEqual(cmd.mode, "one")
        self.assertEqual(cmd.job_name, "share-COM5")
        self.assertEqual(cmd.profile_name, "gd32")

    def test_save_latest(self):
        cmd = parse_save(["-l", "gd32"])
        self.assertEqual(cmd.mode, "latest")
        self.assertEqual(cmd.profile_name, "gd32")

    def test_save_latest_missing_profile(self):
        self.assertEqual(parse_save(["-l"]).mode, "error")

    def test_save_all(self):
        self.assertEqual(parse_save(["-a"]).mode, "all")

    def test_save_all_yes(self):
        cmd = parse_save(["-a", "-y"])
        self.assertEqual(cmd.mode, "all")
        self.assertTrue(cmd.auto_yes)

    def test_save_all_unexpected_arg(self):
        self.assertEqual(parse_save(["-a", "x"]).mode, "error")

    def test_save_y_alone(self):
        self.assertEqual(parse_save(["-y"]).mode, "error")

    def test_save_unknown_option(self):
        self.assertEqual(parse_save(["-x"]).mode, "error")

    def test_save_as_keyword_alone(self):
        self.assertEqual(parse_save(["as"]).mode, "error")

    def test_save_profile_starts_with_dash(self):
        self.assertEqual(
            parse_save(["job", "as", "-x"]).mode, "error")

    def test_old_syntax_profile_l(self):
        self.assertEqual(parse_save(["gd32", "-l"]).mode, "error")

    def test_old_syntax_profile_job(self):
        self.assertEqual(
            parse_save(["gd32", "share-COM5"]).mode, "error")

    def test_old_syntax_y(self):
        self.assertEqual(parse_save(["gd32", "-y"]).mode, "error")


if __name__ == "__main__":
    unittest.main()