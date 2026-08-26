# -*- coding: utf-8 -*-
"""test_ui_hooks.py — on_ui_ready 扩展点测试（直接测试 app.py 真实代码）。

运行：python test_ui_hooks.py  （或 python -m unittest test_ui_hooks -v）
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app


class TestOnUiReadyRegister(unittest.TestCase):
    """PluginAPI.on_ui_ready 注册行为"""

    def setUp(self):
        self.api = app.PluginAPI()

    def test_registers_callable(self):
        f = lambda a: None
        self.api.on_ui_ready(f)
        self.assertEqual(len(self.api.ui_ready_hooks), 1)
        self.assertIs(self.api.ui_ready_hooks[0], f)

    def test_rejects_non_callable(self):
        self.api.on_ui_ready('not callable')
        self.api.on_ui_ready(123)
        self.assertEqual(self.api.ui_ready_hooks, [])

    def test_multiple_hooks_keep_order(self):
        order = []
        self.api.on_ui_ready(lambda a: order.append(1))
        self.api.on_ui_ready(lambda a: order.append(2))
        for hook in self.api.ui_ready_hooks:
            hook(None)
        self.assertEqual(order, [1, 2])


class TestNotifyUiReady(unittest.TestCase):
    """App._notify_ui_ready 回调派发 + 异常兜底（真实方法）"""

    def setUp(self):
        self._orig_hooks = app.PLUGIN_API.ui_ready_hooks
        self._orig_log = app._log
        app.PLUGIN_API.ui_ready_hooks = []
        self.logged = []
        app._log = lambda msg: self.logged.append(str(msg))

    def tearDown(self):
        app.PLUGIN_API.ui_ready_hooks = self._orig_hooks
        app._log = self._orig_log

    def test_hook_receives_app_instance(self):
        received = []
        stub = object()
        app.PLUGIN_API.ui_ready_hooks.append(lambda a: received.append(a))
        app.App._notify_ui_ready(stub)
        self.assertEqual(received, [stub])

    def test_one_hook_exception_does_not_block_others(self):
        seen = []

        def boom(a):
            raise RuntimeError('boom')

        def record(a):
            seen.append('ok')

        stub = object()
        app.PLUGIN_API.ui_ready_hooks.extend([boom, record])
        app.App._notify_ui_ready(stub)
        self.assertEqual(seen, ['ok'], '后续 hook 应继续执行')
        self.assertEqual(len(self.logged), 1, '异常应被记录')
        self.assertIn('boom', self.logged[0])

    def test_no_hooks_no_error(self):
        stub = object()
        app.App._notify_ui_ready(stub)
        self.assertEqual(self.logged, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
