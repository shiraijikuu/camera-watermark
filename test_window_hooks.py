# -*- coding: utf-8 -*-
"""test_window_hooks.py — _clean_pyi_env + on_window_created 扩展点（不依赖 GUI）。

运行：python -m unittest test_window_hooks -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app

KEYS = ('_PYI_PARENT_PROCESS_LEVEL', '_PYI_ARCHIVE_FILE', '_PYI_APPLICATION_HOME_DIR')


class TestCleanPyiEnv(unittest.TestCase):
    def test_clears_pyi_vars(self):
        for k in KEYS:
            os.environ[k] = 'x'
        try:
            app._clean_pyi_env()
            for k in KEYS:
                self.assertNotIn(k, os.environ)
        finally:
            for k in KEYS:
                os.environ.pop(k, None)

    def test_idempotent_when_absent(self):
        for k in KEYS:
            os.environ.pop(k, None)
        app._clean_pyi_env()  # 不应抛异常
        for k in KEYS:
            self.assertNotIn(k, os.environ)


class TestOnWindowCreated(unittest.TestCase):
    def setUp(self):
        self._orig = app.PLUGIN_API.window_created_hooks
        self._orig_log = app._log
        app.PLUGIN_API.window_created_hooks = []
        self.logged = []
        app._log = lambda msg: self.logged.append(str(msg))

    def tearDown(self):
        app.PLUGIN_API.window_created_hooks = self._orig
        app._log = self._orig_log

    def test_registers_callable(self):
        api = app.PluginAPI()
        f = lambda win: None
        api.on_window_created(f)
        self.assertEqual(len(api.window_created_hooks), 1)
        self.assertIs(api.window_created_hooks[0], f)

    def test_rejects_non_callable(self):
        api = app.PluginAPI()
        api.on_window_created('nope')
        self.assertEqual(api.window_created_hooks, [])

    def test_notify_passes_window(self):
        received = []
        app.PLUGIN_API.window_created_hooks.append(lambda win: received.append(win))
        win = object()
        app.App._notify_window_created(object(), win)
        self.assertEqual(received, [win])

    def test_one_exception_does_not_block_others(self):
        seen = []
        def boom(win):
            raise RuntimeError('boom')
        def record(win):
            seen.append('ok')
        app.PLUGIN_API.window_created_hooks.extend([boom, record])
        app.App._notify_window_created(object(), object())
        self.assertEqual(seen, ['ok'])
        self.assertEqual(len(self.logged), 1)
        self.assertIn('boom', self.logged[0])


class TestNotifyDeferred(unittest.TestCase):
    def setUp(self):
        self._orig = app.PLUGIN_API.window_created_hooks
        self._orig_log = app._log
        app.PLUGIN_API.window_created_hooks = []
        self.logged = []
        app._log = lambda msg: self.logged.append(str(msg))
        self.addCleanup(setattr, app.PLUGIN_API, "window_created_hooks", self._orig)
        self.addCleanup(setattr, app, "_log", self._orig_log)

    def test_deferred_until_after(self):
        # 通知不应同步触发，而应等 win.after 回调执行
        received = []
        app.PLUGIN_API.window_created_hooks.append(lambda win: received.append(win))

        class FakeWin:
            def __init__(self):
                self.cbs = []
            def after(self, ms, cb):
                self.cbs.append(cb)

        win = FakeWin()
        app.App._notify_window_created(object(), win)
        self.assertEqual(received, [], "回调不应在 after 前同步执行")
        for cb in win.cbs:
            cb()
        self.assertEqual(received, [win])

    def test_fallback_when_no_after(self):
        received = []
        app.PLUGIN_API.window_created_hooks.append(lambda win: received.append(win))
        win = object()  # 没有 after 方法 -> 走同步兜底
        app.App._notify_window_created(object(), win)
        self.assertEqual(received, [win])

    def test_deferred_exception_still_isolated(self):
        seen = []
        def boom(win):
            raise RuntimeError('boom')
        def record(win):
            seen.append('ok')
        app.PLUGIN_API.window_created_hooks.extend([boom, record])

        class FakeWin:
            def after(self, ms, cb):
                cb()

        app.App._notify_window_created(object(), FakeWin())
        self.assertEqual(seen, ['ok'])
        self.assertEqual(len(self.logged), 1)

if __name__ == "__main__":
    unittest.main(verbosity=2)
