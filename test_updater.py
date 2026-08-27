# -*- coding: utf-8 -*-
"""test_updater.py — 主程序热更新逻辑测试（不依赖真实 Tk 窗口，可无头运行）。

覆盖：_check_update_state（版本 / 同版本 checksum / 更低版本）、_local_exe_checksum、
_download_update 下载后的 checksum 校验。
运行：python -m unittest test_updater -v
"""
import hashlib
import os
import queue
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app


class TestCheckUpdateState(unittest.TestCase):
    def test_empty_latest_none(self):
        self.assertIsNone(app._check_update_state("", "1.4.1"))

    def test_newer(self):
        self.assertEqual(app._check_update_state("1.5.0", "1.4.1"), "newer")

    def test_newer_with_v_prefix(self):
        self.assertEqual(app._check_update_state("v1.5.0", "1.4.1"), "newer")

    def test_same_version_same_checksum_none(self):
        self.assertIsNone(app._check_update_state("1.4.1", "1.4.1", "abc", "abc"))

    def test_same_version_diff_checksum_same_content(self):
        self.assertEqual(app._check_update_state("1.4.1", "1.4.1", "abc", "def"), "same_content")

    def test_same_version_no_checksum_none(self):
        self.assertIsNone(app._check_update_state("1.4.1", "1.4.1"))

    def test_lower_version_none(self):
        self.assertIsNone(app._check_update_state("1.3.0", "1.4.1", "a", "b"))


class TestLocalExeChecksum(unittest.TestCase):
    def test_source_mode_empty(self):
        orig = getattr(sys, "frozen", False)
        sys.frozen = False
        try:
            self.assertEqual(app._local_exe_checksum(), "")
        finally:
            if orig:
                sys.frozen = True
            elif hasattr(sys, "frozen"):
                delattr(sys, "frozen")

    def test_frozen_returns_hex(self):
        orig = getattr(sys, "frozen", False)
        sys.frozen = True
        try:
            chk = app._local_exe_checksum()
            self.assertEqual(len(chk), 64)
            int(chk, 16)
        finally:
            if not orig:
                delattr(sys, "frozen")


class TestDownloadVerify(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="pwm_up_")
        app.APP_DIR = self.tmp
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self._orig = app.urllib.request.urlopen
        self.addCleanup(setattr, app.urllib.request, "urlopen", self._orig)

    def _run(self, data, expected_checksum):
        class Resp:
            def __init__(self, d):
                self._d = d
            def read(self, n=-1):
                # copyfileobj 会按块 read(length)；耗尽后返回 b'' 结束循环
                if n is None or n < 0:
                    n = len(self._d)
                chunk = self._d[:n]
                self._d = self._d[n:]
                return chunk
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False
        app.urllib.request.urlopen = lambda url, timeout: Resp(data)
        q = queue.Queue()
        w = type("W", (), {"msg_q": q})()
        app.App._download_update(w, "https://x/app.exe", "1.4.1", expected_checksum)
        return q.get_nowait()

    def test_match_ok(self):
        data = b"fake-exe-bytes"
        good = hashlib.sha256(data).hexdigest()
        kind, payload = self._run(data, good)
        self.assertEqual(kind, "update_downloaded")
        self.assertTrue(payload[0])  # version set -> success

    def test_mismatch_rejected(self):
        data = b"fake-exe-bytes"
        kind, payload = self._run(data, "0" * 64)
        self.assertEqual(kind, "update_downloaded")
        self.assertIsNone(payload[0])  # version None -> failure

    def test_no_checksum_ok(self):
        kind, payload = self._run(b"whatever", "")
        self.assertEqual(kind, "update_downloaded")
        self.assertTrue(payload[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
