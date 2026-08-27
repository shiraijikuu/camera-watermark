# -*- coding: utf-8 -*-
"""test_drag_ui.py — 水印拖拽定位：watermark_rect + offset 换算（纯逻辑，不依赖 GUI）。

运行：python -m unittest test_drag_ui -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app
import photo
from PIL import Image


BASE = {
    'template': 'TEXT',
    'font_family': '',
    'font_size_pct': 2.0,
    'line_spacing': 0.35,
    'bg_padding': 0.6,
    'anchor': 7,
    'margin_pct': 5.0,
    'offset_x_pct': 0.0,
    'offset_y_pct': 0.0,
    'bg_enabled': False,
    'text_opacity': 1.0,
    'shadow_enabled': False,
    'outline_enabled': False,
}


class TestWatermarkRect(unittest.TestCase):
    def test_empty_template_none(self):
        img = Image.new('RGB', (1000, 600), (255, 255, 255))
        s = dict(BASE, template='')
        self.assertIsNone(photo.watermark_rect(img, s, {}))

    def test_rect_within_bounds(self):
        img = Image.new('RGB', (1000, 600), (255, 255, 255))
        r = photo.watermark_rect(img, dict(BASE), {})
        self.assertIsNotNone(r)
        x0, y0, x1, y1 = r
        self.assertGreaterEqual(x0, -10)
        self.assertGreaterEqual(y0, -10)
        self.assertLessEqual(x1, img.size[0] + 10)
        self.assertLessEqual(y1, img.size[1] + 10)
        self.assertLess(x0, x1)
        self.assertLess(y0, y1)

    def test_anchor_bottom_right(self):
        img = Image.new('RGB', (1000, 600), (255, 255, 255))
        r = photo.watermark_rect(img, dict(BASE, anchor=8), {})
        x0, y0, x1, y1 = r
        # anchor=8 右下：中心应偏右下
        self.assertGreater((x0 + x1) / 2, img.size[0] * 0.7)
        self.assertGreater((y0 + y1) / 2, img.size[1] * 0.7)

    def test_anchor_7_bottom_center(self):
        img = Image.new('RGB', (1000, 600), (255, 255, 255))
        r = photo.watermark_rect(img, dict(BASE, anchor=7), {})
        x0, y0, x1, y1 = r
        self.assertAlmostEqual((x0 + x1) / 2, 500.0, delta=40.0)  # 水平居中
        self.assertGreater((y0 + y1) / 2, 400.0)  # 偏下


class TestOffsetForDrag(unittest.TestCase):
    def test_bottom_right_zero_offset_identity(self):
        # 目标中心 = anchor 默认位置 -> 偏移应接近 0
        img = Image.new('RGB', (1000, 600), (255, 255, 255))
        s = dict(BASE, anchor=7, margin_pct=5.0, offset_x_pct=0, offset_y_pct=0)
        r = photo.watermark_rect(img, s, {})
        cx = (r[0] + r[2]) / 2
        cy = (r[1] + r[3]) / 2
        inner_w = r[2] - r[0]
        inner_h = r[3] - r[1]
        ox, oy = app.App._offset_for_drag(None, 7, 5.0, inner_w, inner_h, 1000, 600, cx, cy)
        self.assertAlmostEqual(ox, 0.0, delta=2.0)
        self.assertAlmostEqual(oy, 0.0, delta=2.0)

    def test_roundtrip_center(self):
        img = Image.new('RGB', (1000, 600), (255, 255, 255))
        s = dict(BASE, anchor=7, margin_pct=5.0, offset_x_pct=0, offset_y_pct=0)
        r = photo.watermark_rect(img, s, {})
        inner_w = r[2] - r[0]
        inner_h = r[3] - r[1]
        target = (500, 450)  # 在 anchor=7 偏移 ±20% 可达范围内
        ox, oy = app.App._offset_for_drag(None, 7, 5.0, inner_w, inner_h, 1000, 600, *target)
        s2 = dict(BASE, anchor=7, margin_pct=5.0, offset_x_pct=ox, offset_y_pct=oy)
        r2 = photo.watermark_rect(img, s2, {})
        cx = (r2[0] + r2[2]) / 2
        cy = (r2[1] + r2[3]) / 2
        self.assertAlmostEqual(cx, target[0], delta=6.0)
        self.assertAlmostEqual(cy, target[1], delta=6.0)

    def test_offset_clamped(self):
        ox, oy = app.App._offset_for_drag(None, 7, 5.0, 200, 60, 1000, 600, 99999, -99999)
        self.assertLessEqual(abs(ox), 20.0)
        self.assertLessEqual(abs(oy), 20.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
