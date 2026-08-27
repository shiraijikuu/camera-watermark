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

    def test_offset_clamped_to_dynamic_boundary(self):
        # 动态边界：极端拖拽被钳到实际可达范围（不再是固定 ±20）
        ox, oy = app.App._offset_for_drag(None, 7, 5.0, 200, 60, 1000, 600, 99999, -99999)
        # anchor=7: bx0=(1000-200)/2=400, by0=600-30-60=510
        # max_ox=(1000-50-200-400)*100/1000=35; min_oy=(30-510)*100/600=-80
        self.assertAlmostEqual(ox, 35.0, places=6)
        self.assertAlmostEqual(oy, -80.0, places=6)

    def test_offset_reaches_boundary_multi_line(self):
        # 多行（两层）水印拖到贴边：offset 不再被 ±20 截断，能到边界
        W, H = 1000, 700
        inner_w, inner_h = 220, 140
        tx = W - W * 0.03 - inner_w / 2      # 贴右下边
        ty = H - H * 0.03 - inner_h / 2
        ox, oy = app.App._offset_for_drag(None, 4, 3.0, inner_w, inner_h, W, H, tx, ty)
        self.assertGreater(ox, 20.0)         # 超过旧 ±20 截断（应 ~36）
        self.assertGreater(oy, 20.0)
        # 反推中心应贴近目标（贴边）
        bx0 = (W - inner_w) / 2
        by0 = (H - inner_h) / 2
        cx = bx0 + inner_w / 2 + ox / 100.0 * W
        cy = by0 + inner_h / 2 + oy / 100.0 * H
        self.assertAlmostEqual(cx, tx, delta=1.0)
        self.assertAlmostEqual(cy, ty, delta=1.0)

    def test_offset_stays_in_bounds(self):
        # 极端拖拽不超界：中心不越过 margin 边界
        W, H = 1000, 700
        inner_w, inner_h = 100, 40
        ox, oy = app.App._offset_for_drag(None, 7, 3.0, inner_w, inner_h, W, H, 99999, -99999)
        bx0 = (W - inner_w) / 2
        by0 = H - 3.0 * H / 100 - inner_h
        cx = bx0 + inner_w / 2 + ox / 100.0 * W
        cy = by0 + inner_h / 2 + oy / 100.0 * H
        self.assertLessEqual(cx, W - W * 0.03 - inner_w / 2 + 0.5)   # 不超右边界
        self.assertGreaterEqual(cy, H * 0.03 + inner_h / 2 - 0.5)    # 不低于上边界


if __name__ == "__main__":
    unittest.main(verbosity=2)
