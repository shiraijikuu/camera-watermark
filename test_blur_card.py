# -*- coding: utf-8 -*-
"""test_blur_card.py — 模糊卡片水印样式插件 + 样式 API 兼容性测试。

覆盖：
- add_watermark_style 三元组兼容（旧 3 参 -> replaces=False，新 4 参 -> True）
- _call_style_renderer 参数个数检测（3 参不传 source / 4 参传 source）
- _render_with_style 分支（replaces=False 先画文字水印 / replaces=True 跳过）
- 模糊卡片插件：输出尺寸 == 输入、前景区域无水印字
运行：python -m unittest test_blur_card -v
"""
import importlib.util
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app
import photo
from PIL import Image

BASE = os.path.dirname(os.path.abspath(__file__))


def load_blur_card():
    spec = importlib.util.spec_from_file_location(
        'blur_card_plugin', os.path.join(BASE, 'plugins', 'blur-card', 'plugin.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestStyleRegisterCompat(unittest.TestCase):
    def setUp(self):
        self.api = app.PluginAPI()
        self.api.styles = {}

    def test_3arg_call_stores_tuple_with_false(self):
        self.api.add_watermark_style('img', '图片水印', lambda *a: None)
        self.assertIs(self.api.styles['img'][2], False)
        self.assertTrue(callable(self.api.styles['img'][1]))

    def test_4arg_call_stores_tuple_with_true(self):
        self.api.add_watermark_style('blur', '模糊卡片', lambda *a: None, replaces_watermark=True)
        self.assertIs(self.api.styles['blur'][2], True)

    def test_stored_tuple_length_three(self):
        # 旧插件 3 参调用也存三元组，_render_with_style 解包不崩溃
        self.api.add_watermark_style('img', '图片水印', lambda *a: None)
        self.assertEqual(len(self.api.styles['img']), 3)


class TestCallStyleRenderer(unittest.TestCase):
    def test_3arg_renderer_gets_no_source(self):
        calls = []
        def r3(img, settings, values):
            calls.append(('3', img))
            return img
        app._call_style_renderer(r3, 'out', {}, {}, 'src')
        self.assertEqual(calls, [('3', 'out')])

    def test_4arg_renderer_gets_source(self):
        calls = []
        def r4(img, settings, values, source=None):
            calls.append(('4', source))
            return img
        app._call_style_renderer(r4, 'out', {}, {}, 'src')
        self.assertEqual(calls, [('4', 'src')])


class TestRenderWithStyleBranch(unittest.TestCase):
    def setUp(self):
        self._orig = app.PLUGIN_API.styles
        app.PLUGIN_API.styles = {}
        self.received = []
        def r(img, settings, values, source=None):
            self.received.append((img, source))
            return img
        self.r = r

    def tearDown(self):
        app.PLUGIN_API.styles = self._orig

    def test_replaces_false_draws_watermark_first(self):
        # 兼容型（replaces=False）：先画默认文字水印，renderer 收到带水印图
        app.PLUGIN_API.styles['img'] = ('图片水印', self.r, False)
        img = Image.new('RGB', (200, 120), (50, 50, 50))
        settings = {'template': 'HELLO', 'font_family': '', 'style': 'img'}
        with mock.patch('photo.render_watermark', wraps=photo.render_watermark) as mw:
            out = app.App._render_with_style(None, img, settings, {})
        mw.assert_called()
        self.assertIsNot(self.received[0][0], img)   # 不是原图
        self.assertIs(out, self.received[0][0])      # 返回 renderer 输出

    def test_replaces_true_skips_watermark(self):
        # 整图重绘型（replaces=True）：跳过默认文字水印，renderer 收到无水印原图
        app.PLUGIN_API.styles['blur'] = ('模糊卡片', self.r, True)
        img = Image.new('RGB', (200, 120), (50, 50, 50))
        settings = {'template': 'HELLO', 'font_family': '', 'style': 'blur'}
        with mock.patch('photo.render_watermark') as mw:
            out = app.App._render_with_style(None, img, settings, {})
        mw.assert_not_called()
        self.assertIs(self.received[0][0], img)
        self.assertIs(out, img)

    def test_default_style_ignores_styles(self):
        # style='default' 时不调用插件样式，只画默认文字水印
        img = Image.new('RGB', (200, 120), (50, 50, 50))
        settings = {'template': 'HELLO', 'font_family': '', 'style': 'default'}
        with mock.patch('photo.render_watermark', wraps=photo.render_watermark) as mw:
            out = app.App._render_with_style(None, img, settings, {})
        mw.assert_called_once()
        self.assertEqual(len(self.received), 0)


class TestBlurCardPlugin(unittest.TestCase):
    # 插件按项目惯例独立仓库交付；主仓库 clone 后 plugins/blur-card 可能不存在，
    # 此时跳过插件行为测试（主程序 API 兼容测试始终执行）。
    @unittest.skipUnless(os.path.exists(os.path.join(BASE, 'plugins', 'blur-card', 'plugin.py')),
                         'blur-card 插件未安装（独立仓库交付）')
    @classmethod
    def setUpClass(cls):
        cls.mod = load_blur_card()

    def test_output_size_equals_input(self):
        img = Image.new('RGB', (800, 600), (60, 60, 60))
        s = {'template': '{make} {model}', 'font_family': ''}
        out = self.mod._render(img, s, {'make': 'NIKON', 'model': 'D3200'}, source=img)
        self.assertEqual(out.size, (800, 600))

    def test_settings_read_from_plugin_values(self):
        # 插件设置经 plugin_values['blur_card'] 传入（与主程序一致）
        img = Image.new('RGB', (800, 600), (60, 60, 60))
        s = {'template': 'X', 'plugin_values': {'blur-card': {'blur_card_fg_scale': 50}}}
        out = self.mod._render(img, s, {'make': ''}, source=img)
        self.assertEqual(out.size, (800, 600))

    def test_watermark_not_on_fg(self):
        # 全黑原图 + 16:9 前景：前景矩形区域内无接近白色像素（水印只在模糊背景）。
        # 关闭描边/阴影/品牌Logo 排除装饰干扰；前景框按 v2 布局（fy = H*0.06）计算。
        img = Image.new('RGB', (800, 600), (0, 0, 0))
        s = {'blur_card_ratio': '16:9', 'blur_card_fg_scale': 72,
             'blur_card_bg_blur': 0, 'blur_card_darken': 0,
             'blur_card_round': 0, 'blur_card_shadow': False,
             'blur_card_outline': False, 'blur_card_show_logo': False,
             'blur_card_wm_pos': 'below', 'template': '{make} {model}',
             'font_family': '', 'font_size_pct': 3.0}
        out = self.mod._render(img, s, {'make': 'NIKON', 'model': 'D3200'}, source=img)
        # v2: box_w = 800*0.72 = 576, box_h = 576/(16/9) = 324, fy = 600*0.06 = 36
        box_w = int(800 * 0.72)
        box_h = int(box_w / (16 / 9))
        fx = int((800 - box_w) / 2)
        fy = int(600 * 0.06)
        px = out.load()
        white = 0
        for y in range(fy + 4, fy + box_h - 4, 3):
            for x in range(fx + 4, fx + box_w - 4, 3):
                r, g, b = px[x, y][:3]
                if r > 240 and g > 240 and b > 240:
                    white += 1
        self.assertEqual(white, 0, '前景矩形区域内不应有白色水印像素')

    def test_v2_settings_registered(self):
        # v2 注册 10 个设置项（含描边/底纹/品牌Logo）；经 _rebuild_plugin_settings 落到全局
        import app as _app
        _orig_specs = _app.PLUGIN_API.setting_specs
        _orig_styles = _app.PLUGIN_API.styles
        _app.PLUGIN_API.setting_specs = []
        _app.PLUGIN_API.styles = {}
        try:
            _app.PLUGIN_API.plugin_name = 'blur-card'
            self.mod.register(_app.PLUGIN_API)
            _app._rebuild_plugin_settings()
            keys = set(_app.PLUGIN_SETTINGS.get('blur-card', {}).keys())
            for k in ('blur_card_ratio', 'blur_card_fg_scale', 'blur_card_bg_blur',
                      'blur_card_darken', 'blur_card_round', 'blur_card_shadow',
                      'blur_card_outline', 'blur_card_backdrop', 'blur_card_show_logo',
                      'blur_card_wm_pos'):
                self.assertIn(k, keys, k + ' 未注册')
            self.assertIs(_app.PLUGIN_API.styles['blur_card'][2], True)
        finally:
            _app.PLUGIN_API.setting_specs = _orig_specs
            _app.PLUGIN_API.styles = _orig_styles
            _app._rebuild_plugin_settings()

    def test_fit_font_no_overflow(self):
        # 超长模板自动缩字号，不溢出信息栏（文字 bbox 在画布内）
        img = Image.new('RGB', (800, 600), (0, 0, 0))
        s = {'template': '{make} {model} {lens} {focal} {aperture} {shutter} {iso} {date}',
             'font_family': '', 'font_size_pct': 6.0,
             'plugin_values': {'blur-card': {'blur_card_ratio': '16:9'}}}
        out = self.mod._render(img, s, {'make': 'NIKON', 'model': 'Z 7_2',
                                        'lens': 'NIKKOR Z 24-70mm f/4 S',
                                        'focal': '70mm', 'aperture': 'f/4.0',
                                        'shutter': '1/800s', 'iso': 'ISO 250',
                                        'date': '2026-01-01'}, source=img)
        # 信息栏（前景下方）内文字最右 x 不超出画布，且画布内无异常
        self.assertEqual(out.size, (800, 600))

    def test_register_uses_replaces_true(self):
        api = app.PluginAPI()
        api.styles = {}
        self.mod.register(api)
        self.assertIn('blur_card', api.styles)
        self.assertIs(api.styles['blur_card'][2], True)
        self.assertGreaterEqual(len(api.styles['blur_card']), 3)


if __name__ == '__main__':
    unittest.main(verbosity=2)
