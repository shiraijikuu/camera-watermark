# -*- coding: utf-8 -*-
"""test_preview_ui.py — 预览缩放计算 纯逻辑测试（不依赖 GUI）。

运行：python -m unittest test_preview_ui -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app


class FakeApp:
    def __init__(self, preview_scale):
        self.preview_scale = preview_scale


class TestComputePreviewScale(unittest.TestCase):
    def test_fit_downscale(self):
        a = FakeApp('fit')
        # 2000x1000 图放进 1000x600 画布 -> 宽 0.5, 高 0.6, 取小 0.5
        self.assertAlmostEqual(app.App._compute_preview_scale(a, 1000, 600, 2000, 1000), 0.5)

    def test_fit_cap_2x(self):
        a = FakeApp('fit')
        # 400x200 图放进 1000x600 画布 -> 宽 2.5, 高 3.0, 但上限 2.0
        self.assertAlmostEqual(app.App._compute_preview_scale(a, 1000, 600, 400, 200), 2.0)

    def test_fit_height_bound(self):
        a = FakeApp('fit')
        # 1000x2000 竖图放进 1000x600 -> 宽 1.0, 高 0.3 -> 0.3
        self.assertAlmostEqual(app.App._compute_preview_scale(a, 1000, 600, 1000, 2000), 0.3)

    def test_zoom_100(self):
        a = FakeApp(1.0)
        self.assertEqual(app.App._compute_preview_scale(a, 1000, 600, 2000, 1000), 1.0)

    def test_zoom_200(self):
        a = FakeApp(2.0)
        self.assertEqual(app.App._compute_preview_scale(a, 1000, 600, 2000, 1000), 2.0)

    def test_fit_zero_guard(self):
        a = FakeApp('fit')
        self.assertAlmostEqual(app.App._compute_preview_scale(a, 120, 120, 0, 0), 2.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
