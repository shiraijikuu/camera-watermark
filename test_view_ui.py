# -*- coding: utf-8 -*-
"""test_view_ui.py — 预览视图交互：滚轮缩放 / 平移画布 / 拖拽模式（纯逻辑，不依赖 GUI）。

运行：python -m unittest test_view_ui -v
"""
import os
import sys
import time
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app
from PIL import Image


class FakeCanvas:
    """记录 coords 调用的画布替身。"""
    def __init__(self):
        self.moved = []
    def coords(self, item, *args):
        self.moved.append((item, args))
    def winfo_width(self):
        return 800
    def winfo_height(self):
        return 600


class FakeApp:
    def __init__(self):
        self.preview_scale = 'fit'
        self._pan_x = 0
        self._pan_y = 0
        self._drag_mode = None
        self._drag_last_render = 0.0
        self._drag_start = (0, 0)
        self._pan_start = (0, 0)
        self._wm_rect = None
        self._wm_rect_img = None
        self._preview_disp = None
        self._preview_origin = None
        self._preview_item = 'ITEM'
        self._current_preview_full = None
        self.zoomed = []
        self.rendered = 0
        self.panned = 0
        self.settings = {'margin_pct': 5.0, 'offset_x_pct': 0.0, 'offset_y_pct': 0.0}
        self.ox_var = _Var()
        self.oy_var = _Var()
        self.anchor_var = _Var(7)
        self.canvas = FakeCanvas()

    # ---- 被测试方法调用的真实方法（App 上定义） ----
    _offset_for_drag = app.App._offset_for_drag

    def _set_zoom(self, v):
        self.preview_scale = v
        self._pan_x = 0
        self._pan_y = 0
        self.zoomed.append(v)

    def _render_preview(self):
        self.rendered += 1

    def _update_labels(self):
        pass

    def _apply_pan(self):
        self.panned += 1


class _Var:
    def __init__(self, v=0.0):
        self._v = v
    def get(self):
        return self._v
    def set(self, v):
        self._v = v


class TestWheelZoom(unittest.TestCase):
    def test_wheel_up_from_fit_goes_100(self):
        a = FakeApp()
        app.App._on_wheel(a, SimpleNamespace(delta=120))
        self.assertEqual(a.preview_scale, 1.0)

    def test_wheel_down_from_fit_goes_075(self):
        a = FakeApp()
        app.App._on_wheel(a, SimpleNamespace(delta=-120))
        self.assertEqual(a.preview_scale, 0.75)

    def test_wheel_up_from_100(self):
        a = FakeApp(); a.preview_scale = 1.0
        app.App._on_wheel(a, SimpleNamespace(delta=120))
        self.assertEqual(a.preview_scale, 1.25)

    def test_wheel_down_from_100(self):
        a = FakeApp(); a.preview_scale = 1.0
        app.App._on_wheel(a, SimpleNamespace(delta=-120))
        self.assertEqual(a.preview_scale, 0.75)

    def test_wheel_clamped_min(self):
        a = FakeApp(); a.preview_scale = 0.25
        app.App._on_wheel(a, SimpleNamespace(delta=-120))
        self.assertEqual(a.preview_scale, 0.25)

    def test_wheel_clamped_max(self):
        a = FakeApp(); a.preview_scale = 4.0
        app.App._on_wheel(a, SimpleNamespace(delta=120))
        self.assertEqual(a.preview_scale, 4.0)

    def test_wheel_resets_pan(self):
        a = FakeApp(); a.preview_scale = 1.0; a._pan_x = 30; a._pan_y = -10
        app.App._on_wheel(a, SimpleNamespace(delta=120))
        self.assertEqual((a._pan_x, a._pan_y), (0, 0))


class TestPressMode(unittest.TestCase):
    def test_press_outside_wm_sets_pan(self):
        a = FakeApp()
        a._wm_rect = (100, 100, 200, 200)
        app.App._wm_press(a, SimpleNamespace(x=50, y=50))
        self.assertEqual(a._drag_mode, 'pan')
        self.assertEqual(a._drag_start, (50, 50))

    def test_press_inside_wm_sets_watermark(self):
        a = FakeApp()
        a._wm_rect = (100, 100, 200, 200)
        app.App._wm_press(a, SimpleNamespace(x=150, y=150))
        self.assertEqual(a._drag_mode, 'watermark')
        self.assertEqual(a._drag_anchor, 7)

    def test_press_no_rect_sets_pan(self):
        a = FakeApp()
        app.App._wm_press(a, SimpleNamespace(x=10, y=10))
        self.assertEqual(a._drag_mode, 'pan')


class TestPanDrag(unittest.TestCase):
    def test_pan_drag_updates_offset_and_applies(self):
        a = FakeApp()
        a._drag_mode = 'pan'
        a._drag_start = (100, 100)
        a._pan_start = (0, 0)
        app.App._wm_drag(a, SimpleNamespace(x=150, y=130))
        self.assertEqual((a._pan_x, a._pan_y), (50, 30))
        self.assertEqual(a.panned, 1)

    def test_pan_drag_relative_to_start(self):
        a = FakeApp()
        a._drag_mode = 'pan'
        a._drag_start = (100, 100)
        a._pan_start = (20, -5)
        app.App._wm_drag(a, SimpleNamespace(x=90, y=120))
        self.assertEqual((a._pan_x, a._pan_y), (10, 15))

    def test_release_pan_keeps_apply(self):
        a = FakeApp()
        a._drag_mode = 'pan'
        app.App._wm_release(a)
        self.assertIsNone(a._drag_mode)
        self.assertEqual(a.panned, 1)


class TestWatermarkDrag(unittest.TestCase):
    def _setup_wm(self):
        a = FakeApp()
        a._drag_mode = 'watermark'
        a._drag_anchor = 7
        a._preview_disp = (400, 300, 0.5, 200.0, 150.0)   # disp_w, disp_h, scale, ox, oy
        a._wm_rect_img = (100, 50, 300, 150)             # 图像坐标水印矩形
        a._current_preview_full = Image.new('RGB', (1000, 600), (255, 255, 255))
        return a

    def test_drag_updates_settings(self):
        a = self._setup_wm()
        app.App._wm_drag(a, SimpleNamespace(x=250, y=200))  # 画布坐标 -> 图像坐标 (100, 100)
        self.assertNotEqual(a.settings['offset_x_pct'], 0.0)
        self.assertNotEqual(a.settings['offset_y_pct'], 0.0)
        self.assertEqual(a.ox_var.get(), a.settings['offset_x_pct'])
        self.assertEqual(a.oy_var.get(), a.settings['offset_y_pct'])
        self.assertGreater(a.rendered, 0)

    def test_release_watermark_resets_mode(self):
        a = self._setup_wm()
        app.App._wm_release(a)
        self.assertIsNone(a._drag_mode)

    def test_no_drag_when_mode_none(self):
        a = self._setup_wm()
        a._drag_mode = None
        app.App._wm_drag(a, SimpleNamespace(x=250, y=200))
        self.assertEqual(a.settings['offset_x_pct'], 0.0)


class TestApplyPan(unittest.TestCase):
    def test_apply_pan_moves_item_and_rect(self):
        a = FakeApp()
        a._preview_disp = (400, 300, 0.5, 100.0, 80.0)
        a._preview_origin = (100.0, 80.0)
        a._preview_item = 'IMG'
        a._wm_rect_img = (10, 20, 210, 120)
        a._pan_x = 50
        a._pan_y = -20
        app.App._apply_pan(a)
        # 新 ox = 100 + 50 = 150；中心 x = 150 + 200 = 350
        self.assertEqual(a.canvas.moved[0][0], 'IMG')
        self.assertAlmostEqual(a.canvas.moved[0][1][0], 350.0)
        self.assertAlmostEqual(a.canvas.moved[0][1][1], 80.0 - 20 + 150.0)
        # _wm_rect 平移后 = (150+10*0.5, 60+20*0.5, ...)
        self.assertAlmostEqual(a._wm_rect[0], 155.0)
        self.assertAlmostEqual(a._wm_rect[1], 70.0)
        self.assertAlmostEqual(a._wm_rect[2], 255.0)
        self.assertAlmostEqual(a._wm_rect[3], 120.0)

    def test_apply_pan_without_item_falls_back_to_render(self):
        a = FakeApp()
        a._preview_item = None
        a._preview_disp = (400, 300, 0.5, 100.0, 80.0)
        a._preview_origin = (100.0, 80.0)
        app.App._apply_pan(a)
        self.assertGreater(a.rendered, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
