# -*- coding: utf-8 -*-
"""test_plugin_store.py — 插件商店逻辑测试（不依赖真实 Tk 窗口，可无头运行）。

覆盖：更新检测（版本+checksum+加载失败）、安全解压（Zip Slip / 大小限制）、
安装流程（checksum 校验 / 原子安装 / 失败恢复 .bak）。
运行：python -m unittest test_plugin_store -v
"""
import hashlib
import io
import os
import shutil
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app


class _FakeResp:
    def __init__(self, data):
        self._d = data
    def read(self):
        return self._d
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False


class _FakeRoot:
    def __init__(self):
        self.calls = []
    def after(self, ms, cb):
        self.calls.append(cb)


class _FakeWin:
    def __init__(self):
        self._installing = False
        self._installing_pid = ""
        self.parent = type("P", (), {"root": _FakeRoot()})()
        self.fail_msg = None
        self.done = False
    def _install_failed(self, msg):
        self.fail_msg = msg
    def _install_done(self):
        self.done = True


def _make_zip(data_map):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in data_map.items():
            z.writestr(name, data)
    return buf.getvalue()


class TestPluginUpdateAvailable(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="pwm_ps_")
        app.INSTALLED_META_PATH = os.path.join(self.tmp, "plugins", ".installed.json")
        os.makedirs(os.path.dirname(app.INSTALLED_META_PATH), exist_ok=True)
        app.PLUGIN_NAMES = ["loaded-a"]
        app.PLUGIN_VERSIONS = {"loaded-a": "1.0.0"}
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_not_installed_returns_false(self):
        self.assertFalse(app._plugin_update_available({"id": "x", "version": "1.0.0"}))

    def test_same_version_same_checksum_no_update(self):
        app._write_installed_meta({"loaded-a": {"version": "1.0.0", "checksum": "aaa"}})
        self.assertFalse(app._plugin_update_available({"id": "loaded-a", "version": "1.0.0", "checksum": "aaa"}))

    def test_same_version_diff_checksum_update(self):
        app._write_installed_meta({"loaded-a": {"version": "1.0.0", "checksum": "old"}})
        self.assertTrue(app._plugin_update_available({"id": "loaded-a", "version": "1.0.0", "checksum": "new"}))

    def test_newer_version_update(self):
        app._write_installed_meta({"loaded-a": {"version": "1.0.0", "checksum": "aaa"}})
        self.assertTrue(app._plugin_update_available({"id": "loaded-a", "version": "1.1.0", "checksum": "aaa"}))

    def test_load_failed_record_only(self):
        app._write_installed_meta({"broken": {"version": "1.0.0", "checksum": "c"}})
        self.assertTrue(app._plugin_update_available({"id": "broken", "version": "1.0.1", "checksum": "c"}))
        self.assertFalse(app._plugin_update_available({"id": "broken", "version": "1.0.0", "checksum": "c"}))

    def test_checksum_case_insensitive(self):
        app._write_installed_meta({"loaded-a": {"version": "1.0.0", "checksum": "ABC"}})
        self.assertFalse(app._plugin_update_available({"id": "loaded-a", "version": "1.0.0", "checksum": "abc"}))


class TestSafeExtract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="pwm_sx_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_legit_extract(self):
        zp = os.path.join(self.tmp, "legit.zip")
        with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("pkg/plugin.py", "x")
        dest = os.path.join(self.tmp, "out")
        app._safe_extract_zip(zp, dest)
        self.assertTrue(os.path.isfile(os.path.join(dest, "pkg", "plugin.py")))

    def test_zip_slip_rejected(self):
        for i, arc in enumerate(["../evil.py", "a/../../evil.py", "/abs.py", "C:/evil.py"]):
            with self.subTest(arc=arc):
                zp = os.path.join(self.tmp, "bad%d.zip" % i)
                with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
                    z.writestr(arc, "x")
                dest = os.path.join(self.tmp, "out%d" % i)
                with self.assertRaises(ValueError):
                    app._safe_extract_zip(zp, dest)
                self.assertFalse(os.path.exists(os.path.join(self.tmp, "evil.py")))

    def test_zip_bomb_total_limit(self):
        old = app.MAX_EXTRACT_TOTAL
        app.MAX_EXTRACT_TOTAL = 1000
        self.addCleanup(setattr, app, "MAX_EXTRACT_TOTAL", old)
        zp = os.path.join(self.tmp, "bomb.zip")
        with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("big.bin", b"x" * 2000)
        with self.assertRaises(ValueError):
            app._safe_extract_zip(zp, os.path.join(self.tmp, "out"))


class TestInstallFlow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="pwm_if_")
        app.APP_DIR = self.tmp
        app.PLUGINS_DIR = os.path.join(self.tmp, "plugins")
        app.INSTALLED_META_PATH = os.path.join(self.tmp, "plugins", ".installed.json")
        os.makedirs(app.PLUGINS_DIR, exist_ok=True)
        self._orig_urlopen = app.urllib.request.urlopen
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.addCleanup(setattr, app.urllib.request, "urlopen", self._orig_urlopen)
        self.addCleanup(setattr, app.os, "rename", os.rename)

    def _install(self, plugin_id, zip_bytes, checksum, extra=None):
        app.urllib.request.urlopen = lambda url, timeout: _FakeResp(zip_bytes)
        p = {"id": plugin_id, "version": "1.0.0", "install_url": "https://x/z.zip", "checksum": checksum}
        if extra:
            p.update(extra)
        w = _FakeWin()
        app.PluginStoreWindow._install_worker(w, p)
        for cb in w.parent.root.calls:
            cb()
        return w

    def test_checksum_mismatch_rejected(self):
        zip_bytes = _make_zip({"pkg/plugin.py": "x"})
        w = self._install("p", zip_bytes, "0" * 64)
        self.assertIsNotNone(w.fail_msg)
        self.assertFalse(os.path.exists(os.path.join(app.PLUGINS_DIR, "p")))

    def test_install_success(self):
        zip_bytes = _make_zip({"pkg/plugin.py": "x", "pkg/data.txt": "hi"})
        good = hashlib.sha256(zip_bytes).hexdigest()
        w = self._install("plug", zip_bytes, good)
        self.assertIsNone(w.fail_msg)
        self.assertTrue(os.path.isfile(os.path.join(app.PLUGINS_DIR, "plug", "plugin.py")))
        self.assertFalse(os.path.exists(os.path.join(app.PLUGINS_DIR, "_staging_plug")))
        self.assertFalse(os.path.exists(os.path.join(app.PLUGINS_DIR, "_bak_plug")))
        self.assertEqual(app._read_installed_meta()["plug"]["checksum"], good)

    def test_failed_install_restores_bak(self):
        zip_bytes = _make_zip({"pkg/plugin.py": "# NEW"})
        good = hashlib.sha256(zip_bytes).hexdigest()
        target = os.path.join(app.PLUGINS_DIR, "plug")
        os.makedirs(target)
        with open(os.path.join(target, "plugin.py"), "w", encoding="utf-8") as f:
            f.write("# OLD")
        real_rename = os.rename
        def failing_rename(src, dst):
            if "_staging_plug" in str(src) and str(dst) == target:
                raise OSError("simulated rename failure")
            return real_rename(src, dst)
        app.os.rename = failing_rename
        w = self._install("plug", zip_bytes, good)
        self.assertIsNotNone(w.fail_msg)
        self.assertIn("simulated", w.fail_msg)
        with open(os.path.join(target, "plugin.py"), encoding="utf-8") as f:
            self.assertEqual(f.read().strip(), "# OLD")
        self.assertFalse(os.path.exists(os.path.join(app.PLUGINS_DIR, "_staging_plug")))
        self.assertFalse(os.path.exists(os.path.join(app.PLUGINS_DIR, "_bak_plug")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
