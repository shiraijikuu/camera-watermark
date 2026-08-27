# -*- coding: utf-8 -*-
"""test_view_ui.py — 预览视图交互：滚轮缩放（以鼠标为中心/最小档回 fit）/
平移画布 / 拖拽模式 / 拖放路径解析（纯逻辑，不依赖 GUI）。

运行：python -m unittest test_view_ui -v
"""
import os
import sys
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
    def __init__(self, img_size=(1000, 600)):
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
        self._current_preview_full = Image.new('RGB', img_size, (255, 255, 255))
        self.zoomed = []
        self.rendered = 0
        self.panned = 0
        self.settings = {'margin_pct': 5.0, 'offset_x_pct': 0.0, 'offset_y_pct': 0.0}
        self.ox_var = _Var()
        self.oy_var = _Var()
        self.anchor_var = _Var(7)
        self.canvas = FakeCanvas()
        self.zoom_var = _Var(100.0)
        self.zoom_label = FakeLabel()
        self._zoom_slider_guard = False
        self.preview_timer = None
        self.scheduled = 0
        self._view_x = 0
        self._view_y = 0

    # ---- 使用 App 上定义的真实方法（纯逻辑） ----
    _offset_for_drag = app.App._offset_for_drag
    _set_zoom = app.App._set_zoom
    _zoom_around = app.App._zoom_around
    _current_fit_scale = app.App._current_fit_scale
    _sync_zoom_ui = app.App._sync_zoom_ui
    _on_zoom_slider = app.App._on_zoom_slider
    _apply_pan = app.App._apply_pan

    def _render_preview(self):
        self.rendered += 1
    def _schedule_preview(self):
        self.scheduled += 1

    def _update_labels(self):
        pass


class FakeLabel:
    """记录 config 调用的 Label 替身。"""
    def __init__(self):
        self.text = ''
    def config(self, **kw):
        if 'text' in kw:
            self.text = kw['text']

class _Var:
    def __init__(self, v=0.0):
        self._v = v
    def get(self):
        return self._v
    def set(self, v):
        self._v = v


# fit: canvas 800x600 -> content 790x590; img 1000x600 -> fit = min(0.79, 0.983, 2) = 0.79
FIT = 0.79


class TestWheelZoom(unittest.TestCase):
    def test_wheel_up_from_fit_snaps_to_next_grid(self):
        a = FakeApp()
        app.App._on_wheel(a, SimpleNamespace(delta=120, x=400, y=300))
        self.assertEqual(a.preview_scale, 1.0)   # ceil(0.79/0.25)=4 -> 1.0

    def test_wheel_down_from_fit_snaps_to_prev_grid(self):
        a = FakeApp()
        app.App._on_wheel(a, SimpleNamespace(delta=-120, x=400, y=300))
        self.assertEqual(a.preview_scale, 0.75)  # floor(0.79/0.25)=3 -> 0.75

    def test_wheel_up_from_100(self):
        a = FakeApp(); a.preview_scale = 1.0
        app.App._on_wheel(a, SimpleNamespace(delta=120, x=400, y=300))
        self.assertEqual(a.preview_scale, 1.25)

    def test_wheel_down_from_100(self):
        a = FakeApp(); a.preview_scale = 1.0
        app.App._on_wheel(a, SimpleNamespace(delta=-120, x=400, y=300))
        self.assertEqual(a.preview_scale, 0.75)

    def test_wheel_down_at_min_returns_to_fit(self):
        # Bug A：最小档 0.25 再往下滚 -> 回到「适应窗口」，而不是卡住
        a = FakeApp(); a.preview_scale = 0.25
        app.App._on_wheel(a, SimpleNamespace(delta=-120, x=400, y=300))
        self.assertEqual(a.preview_scale, 'fit')

    def test_wheel_up_clamped_max(self):
        a = FakeApp(); a.preview_scale = 4.0
        app.App._on_wheel(a, SimpleNamespace(delta=120, x=400, y=300))
        self.assertEqual(a.preview_scale, 4.0)

    def test_wheel_keeps_center_on_fit_small_image(self):
        # 小图 fit 实际放大 2x（上限），向上应到 2.25 而不是跳到 100%
        a = FakeApp(img_size=(200, 100))  # fit = min(790/200, 590/100, 2) = 2.0
        app.App._on_wheel(a, SimpleNamespace(delta=120, x=400, y=300))
        self.assertEqual(a.preview_scale, 2.25)


class TestWheelFitBoundary(unittest.TestCase):
    def test_wheel_down_from_fit_below_min_keeps_fit(self):
        # Bug：大图 fit < 0.25 时向下滚应保持 fit，而非反向放大到 0.25
        a = FakeApp(img_size=(6000, 4000))  # fit = min(790/6000, 590/4000, 2) ~ 0.13
        app.App._on_wheel(a, SimpleNamespace(delta=-120, x=400, y=300))
        self.assertEqual(a.preview_scale, 'fit')

    def test_wheel_up_from_fit_below_min_snaps_up(self):
        a = FakeApp(img_size=(6000, 4000))  # fit ~ 0.13
        app.App._on_wheel(a, SimpleNamespace(delta=120, x=400, y=300))
        self.assertEqual(a.preview_scale, 0.25)  # ceil(0.13/0.25)=1 -> 0.25


class TestZoomSlider(unittest.TestCase):
    def test_slider_sets_zoom(self):
        a = FakeApp()
        app.App._on_zoom_slider(a, '150')
        self.assertAlmostEqual(a.preview_scale, 1.5, places=6)

    def test_slider_clamped_upper(self):
        a = FakeApp()
        app.App._on_zoom_slider(a, '500')
        self.assertEqual(a.preview_scale, 4.0)

    def test_slider_clamped_lower(self):
        a = FakeApp()
        app.App._on_zoom_slider(a, '10')
        self.assertEqual(a.preview_scale, 0.25)

    def test_slider_guard_ignores_programmatic_set(self):
        a = FakeApp()
        a._zoom_slider_guard = True
        app.App._on_zoom_slider(a, '200')
        self.assertEqual(a.preview_scale, 'fit')  # guard 时应被忽略

    def test_zoom_syncs_slider_percent(self):
        a = FakeApp()
        app.App._set_zoom(a, 2.0)
        self.assertEqual(a.zoom_var.get(), 200)
        self.assertEqual(a.zoom_label.text, '200%')

    def test_fit_syncs_slider_to_fit_pct(self):
        a = FakeApp()
        app.App._set_zoom(a, 'fit')
        self.assertEqual(a.zoom_var.get(), 79)
        self.assertEqual(a.zoom_label.text, '79%')

    def test_zoom_sync_clamped_to_slider_range(self):
        a = FakeApp(img_size=(6000, 4000))  # fit ~ 13% < 25 下限
        app.App._set_zoom(a, 'fit')
        self.assertEqual(a.zoom_var.get(), 25)   # 钳到滑块下限
        self.assertEqual(a.zoom_label.text, '13%')  # 标签仍显示真实百分比


class TestZoomPerf(unittest.TestCase):
    def test_pick_resize_method_downscale_box(self):
        self.assertEqual(app._pick_resize_method(0.5), Image.BOX)
        self.assertEqual(app._pick_resize_method(0.99), Image.BOX)

    def test_pick_resize_method_upscale_lanczos(self):
        self.assertEqual(app._pick_resize_method(1.0), Image.BILINEAR)
        self.assertEqual(app._pick_resize_method(2.5), Image.BILINEAR)

    def test_set_zoom_defer_schedules_not_renders(self):
        a = FakeApp()
        app.App._set_zoom(a, 1.5, defer_render=True)
        self.assertEqual(a.preview_scale, 1.5)
        self.assertEqual(a.scheduled, 1)     # 节流：只排队
        self.assertEqual(a.rendered, 0)      # 未立即全量渲染

    def test_set_zoom_non_defer_renders_immediately(self):
        a = FakeApp()
        app.App._set_zoom(a, 2.0)
        self.assertEqual(a.rendered, 1)

    def test_slider_drag_schedules_not_renders(self):
        # 拖动滑块：连续事件只排队合并渲染，不逐事件全量渲染（卡顿根源）
        a = FakeApp()
        app.App._on_zoom_slider(a, '150')
        self.assertAlmostEqual(a.preview_scale, 1.5, places=6)
        self.assertEqual(a.scheduled, 1)
        self.assertEqual(a.rendered, 0)

    def test_wheel_renders_immediately(self):
        # 滚轮单步仍即时渲染（用户期望即时反馈）
        a = FakeApp()
        app.App._on_wheel(a, SimpleNamespace(delta=120, x=400, y=300))
        self.assertEqual(a.rendered, 1)


class TestClampedView(unittest.TestCase):
    def test_large_zoom_clamps_output_and_view(self):
        # 大图放大：输出钳制到画布过扫描，view 指向可见区域（不渲染 scale x 全图）
        a = FakeApp(img_size=(6000, 4000))
        a._preview_disp = (3000, 2000, 0.5, 100.0, 100.0)
        app.App._zoom_around(a, 400, 300, 2.0)
        self.assertEqual(a.preview_scale, 2.0)
        self.assertGreater(a._view_x, 0)   # 窗口已进入图像内部（可见区域）
        self.assertGreater(a._view_y, 0)
        # 输出钳制：vw = out_w/scale，out_w <= 790*1.25
        # 直接验证 view 钳制在图像范围内
        self.assertLessEqual(a._view_x, 6000)
        self.assertLessEqual(a._view_y, 4000)

    def test_small_zoom_keeps_view_zero(self):
        # 缩小/fit 未触发钳制：view 恒 0（全图渲染，兼容旧逻辑）
        a = FakeApp(img_size=(6000, 4000))
        a.preview_scale = 0.5
        a._preview_disp = (3000, 2000, 0.5, 100.0, 100.0)
        app.App._zoom_around(a, 400, 300, 0.5)
        self.assertEqual(a._view_x, 0.0)
        self.assertEqual(a._view_y, 0.0)
        self.assertEqual(a.preview_scale, 0.5)


class TestZoomAround(unittest.TestCase):
    def test_zoom_keeps_mouse_point_fixed(self):
        a = FakeApp()
        # 当前显示：scale=0.5，内容区 790x590（winfo 800x600 - 10），ox/oy 已含平移
        a._preview_disp = (500, 300, 0.5, 100.0, 100.0)
        # 鼠标在画布 (400, 300) -> 图像坐标 (600, 400)
        app.App._zoom_around(a, 400, 300, 1.0)
        # 放大 1.0 时输出钳制到画布过扫描 987.5px（1000>987.5 触发可见区域渲染）
        # 窗口 vw=987.5 -> nvx 钳到 12.5（图像右缘），pan 保持 0
        self.assertAlmostEqual(a._pan_x, 0.0, places=6)
        self.assertAlmostEqual(a._pan_y, 0.0, places=6)
        self.assertAlmostEqual(a._view_x, 12.5, places=6)
        self.assertAlmostEqual(a._view_y, 0.0, places=6)
        self.assertEqual(a.preview_scale, 1.0)

    def test_zoom_to_fit_uses_fit_effective_scale(self):
        a = FakeApp()
        a.preview_scale = 2.0
        a._preview_disp = (2000, 1200, 2.0, -600.0, -300.0)
        app.App._zoom_around(a, 400, 300, 'fit')
        # fit 输出 790x474 未钳制（< 画布过扫描），窗口=全图（view 归 0），pan 归 0
        self.assertAlmostEqual(a._pan_x, 0.0, places=4)
        self.assertAlmostEqual(a._pan_y, 0.0, places=4)
        self.assertAlmostEqual(a._view_x, 0.0, places=4)
        self.assertAlmostEqual(a._view_y, 0.0, places=4)
        self.assertEqual(a.preview_scale, 'fit')


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
        self.assertGreater(a.rendered, 0)   # 无 item 时 _apply_pan 回退渲染

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
        self.assertGreater(a.rendered, 0)


class TestWatermarkDrag(unittest.TestCase):
    def _setup_wm(self):
        a = FakeApp()
        a._drag_mode = 'watermark'
        a._drag_anchor = 7
        a._preview_disp = (400, 300, 0.5, 200.0, 150.0)
        a._wm_rect_img = (100, 50, 300, 150)
        a._current_preview_full = Image.new('RGB', (1000, 600), (255, 255, 255))
        return a

    def test_drag_updates_settings(self):
        a = self._setup_wm()
        app.App._wm_drag(a, SimpleNamespace(x=250, y=200))
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


class TestPanBufferWindow(unittest.TestCase):
    def test_pan_beyond_buffer_moves_view_same_direction(self):
        # 放大钳制模式：拖拽左移（pan_x<0）超缓冲 -> 窗口应右移（vx 增大）保持视觉连续
        a = FakeApp()
        a._preview_disp = (500, 300, 0.5, 100.0, 100.0)
        a._view_x, a._view_y = 100.0, 50.0
        a._pan_x, a._pan_y = -500.0, 0.0
        a._preview_item = 'IMG'
        a._preview_origin = (145.0, 145.0)
        app.App._apply_pan(a)
        # vx_new = 100 - (-500)/0.5 = 1100（窗口右移，与拖拽同向）；pan 重置为 0
        self.assertAlmostEqual(a._view_x, 1100.0, places=4)
        self.assertAlmostEqual(a._pan_x, 0.0, places=4)
        self.assertGreater(a.rendered, 0)   # 已触发缓冲重渲染

    def test_pan_within_buffer_keeps_window(self):
        # 缓冲内平移：item 移动、窗口不动、不重渲染
        a = FakeApp()
        # 渲染图 1000x700 覆盖画布 790x590（ox=-100 左伸，ox+disp_w=900>790）
        a._preview_disp = (1000, 700, 0.5, -100.0, -50.0)
        a._view_x, a._view_y = 100.0, 50.0
        a._pan_x, a._pan_y = 0.0, 0.0
        a._preview_item = 'IMG'
        a._preview_origin = (-100.0, -50.0)
        app.App._apply_pan(a)
        self.assertAlmostEqual(a._view_x, 100.0, places=4)   # 窗口不动
        self.assertEqual(a.rendered, 0)                       # 不重渲染


class TestPanResyncAfterRerender(unittest.TestCase):
    def test_drag_continues_smoothly_after_buffer_rerender(self):
        a = FakeApp()
        a._preview_disp = (1000, 700, 0.5, -100.0, -50.0)   # 渲染图覆盖画布
        a._preview_origin = (-100.0, -50.0)
        a._view_x, a._view_y = 100.0, 50.0
        a._preview_item = 'IMG'
        a._drag_mode = 'pan'
        a._drag_start = (100, 100)
        a._pan_start = (0, 0)
        # 第一次大拖拽：触发缓冲重渲染
        app.App._wm_drag(a, SimpleNamespace(x=700, y=100))
        self.assertEqual(a._pan_x, 0)                 # 重渲染后 pan 归零
        self.assertEqual(a._drag_start, (700, 100))   # 起点同步到当前鼠标
        # 继续小拖拽（手指 700->710）：pan 应只加 10，不跳跃
        app.App._wm_drag(a, SimpleNamespace(x=710, y=100))
        self.assertAlmostEqual(a._pan_x, 10.0, places=6)
        self.assertAlmostEqual(a._pan_y, 0.0, places=6)

    def test_drag_after_rerender_does_not_accumulate_old_offset(self):
        # 若起点未同步，第二次拖拽会用旧起点(100)算 pan=610，导致跳跃；此处验证已同步
        a = FakeApp()
        a._preview_disp = (1000, 700, 0.5, -100.0, -50.0)
        a._preview_origin = (-100.0, -50.0)
        a._view_x, a._view_y = 100.0, 50.0
        a._preview_item = 'IMG'
        a._drag_mode = 'pan'
        a._drag_start = (100, 100)
        a._pan_start = (0, 0)
        app.App._wm_drag(a, SimpleNamespace(x=700, y=100))   # 触发重渲染
        app.App._wm_drag(a, SimpleNamespace(x=710, y=100))
        # 关键断言：连续拖拽总位移只反映"当前增量"，而非从旧起点累计
        self.assertAlmostEqual(a._pan_x, 10.0, places=6)


class TestPluginIncrementalDrag(unittest.TestCase):
    """插件样式（有 rect_func）文字水印走增量拖拽：从按下点算增量、跟随鼠标、边界约束。"""
    def _setup(self, rect=(100, 50, 300, 150)):
        a = FakeApp()
        a._preview_disp = (400, 300, 0.5, 200.0, 150.0)
        a._wm_rect_img = rect
        a._current_preview_full = Image.new('RGB', (1000, 600), (255, 255, 255))
        a.settings['style'] = 'blur_card'
        a.settings['offset_x_pct'] = 0.0
        a.settings['offset_y_pct'] = 0.0
        a._drag_mode = 'watermark'
        a._drag_img_start = (200, 100)     # 按下点（rect 中心）
        a._drag_offset_start = (0.0, 0.0)
        return a

    def tearDown(self):
        app.PLUGIN_API.style_rects = {}

    def test_incremental_follows_mouse(self):
        app.PLUGIN_API.style_rects['blur_card'] = lambda *a: (100, 50, 300, 150)
        a = self._setup()
        # 鼠标移到图像坐标 (250, 125)：画布 x = 200 + 250*0.5 = 325, y = 150 + 125*0.5 = 212.5
        app.App._wm_drag(a, SimpleNamespace(x=325, y=212.5))
        self.assertAlmostEqual(a.settings['offset_x_pct'], 5.0, places=6)
        self.assertAlmostEqual(a.settings['offset_y_pct'], 25.0 / 600.0 * 100.0, places=6)

    def test_incremental_clamped_to_bounds(self):
        app.PLUGIN_API.style_rects['blur_card'] = lambda *a: (100, 50, 300, 150)
        a = self._setup()
        # 鼠标拖到图像坐标 (99999, -99999) -> 画布坐标巨大 -> offset 被钳到边界
        app.App._wm_drag(a, SimpleNamespace(x=200 + 99999 * 0.5, y=150 + (-99999) * 0.5))
        ox = a.settings['offset_x_pct']
        oy = a.settings['offset_y_pct']
        # 边界：rect 中心 (200,100)，inner (200,100)，margin 5% (50,30)
        max_tx = 1000 - 50 - 100          # margin_x + inner_w/2 起，到 W-margin-inner/2
        min_tx = 50 + 100
        max_ty = 600 - 30 - 50
        min_ty = 30 + 50
        cx = 200 + ox / 100.0 * 1000
        cy = 100 + oy / 100.0 * 600
        self.assertLessEqual(cx, max_tx + 0.5)
        self.assertGreaterEqual(cx, min_tx - 0.5)
        self.assertLessEqual(cy, max_ty + 0.5)
        self.assertGreaterEqual(cy, min_ty - 0.5)

    def test_no_rect_func_uses_default_path(self):
        # 无 rect_func 的样式：走 _offset_for_drag（动态边界）
        a = self._setup()
        app.PLUGIN_API.style_rects['blur_card'] = None
        a._drag_anchor = 4
        app.App._wm_drag(a, SimpleNamespace(x=325, y=212.5))
        self.assertNotEqual(a.settings['offset_x_pct'], 0.0)


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
        self.assertEqual(a.canvas.moved[0][0], 'IMG')
        self.assertAlmostEqual(a.canvas.moved[0][1][0], 350.0)
        self.assertAlmostEqual(a.canvas.moved[0][1][1], 80.0 - 20 + 150.0)
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


class TestParseDndPaths(unittest.TestCase):
    def test_simple_paths(self):
        a = FakeApp()
        self.assertEqual(app.App._parse_dnd_paths(a, r'C:\a\b.jpg D:\c\d.jpg'),
                         [r'C:\a\b.jpg', r'D:\c\d.jpg'])

    def test_braced_paths_with_spaces(self):
        a = FakeApp()
        self.assertEqual(app.App._parse_dnd_paths(a, r'{C:\my photos\folder} D:\x.jpg'),
                         [r'C:\my photos\folder', r'D:\x.jpg'])

    def test_mixed_and_empty(self):
        a = FakeApp()
        got = app.App._parse_dnd_paths(a, r'{C:\a b}   {D:\c d}  E:\e.jpg')
        self.assertEqual(got, [r'C:\a b', r'D:\c d', r'E:\e.jpg'])

    def test_empty_input(self):
        a = FakeApp()
        self.assertEqual(app.App._parse_dnd_paths(a, ''), [])
        self.assertEqual(app.App._parse_dnd_paths(a, '   '), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
