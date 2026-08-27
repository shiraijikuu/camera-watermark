# -*- coding: utf-8 -*-
"""test_drop.py — 拖拽文件夹解析（纯逻辑，不依赖 GUI）。

运行：python -m unittest test_drop -v
"""
import os
import sys
import tempfile
import shutil
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app


class TestResolveDropFolder(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="pwm_drop_")
        self.sub = os.path.join(self.tmp, "sub")
        os.makedirs(self.sub)
        self.file = os.path.join(self.tmp, "a.jpg")
        open(self.file, "w").close()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_dir_returns_dir(self):
        self.assertEqual(app.App._resolve_drop_folder(None, [self.sub]), self.sub)

    def test_file_returns_dirname(self):
        self.assertEqual(app.App._resolve_drop_folder(None, [self.file]), self.tmp)

    def test_first_dir_wins(self):
        other = os.path.join(self.tmp, "other")
        os.makedirs(other)
        self.assertEqual(app.App._resolve_drop_folder(None, [self.file, other]), self.tmp)

    def test_empty_returns_none(self):
        self.assertIsNone(app.App._resolve_drop_folder(None, []))
        self.assertIsNone(app.App._resolve_drop_folder(None, ["", None]))

    def test_missing_returns_none(self):
        self.assertIsNone(app.App._resolve_drop_folder(None, [os.path.join(self.tmp, "nope")]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
