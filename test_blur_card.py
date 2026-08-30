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
    plugin_py = os.path.join(BASE, 'plugins', 'blur-card', 'plugin.py')
    if not os.path.exists(plugin_py):
        # 插件独立仓库交付，主仓库 clone 后可能不在；CI 由 workflows 先拉取，本地缺失时跳过
        raise unittest.SkipTest('blur-card 插件未安装（独立仓库交付）')
    spec = importlib.util.spec_from_file_location('blur_card_plugin', plugin_py)
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

    def test_rect_func_stored(self):
        # 旧 3 参调用 rect_func=None；新 5 参（rect_func）存储可调用
        self.api.add_watermark_style('img', '图片水印', lambda *a: None)
        self.api.add_watermark_style('blur', '模糊卡片', lambda *a: None,
                                     replaces_watermark=True, rect_func=lambda *a: (0, 0, 10, 10))
        self.assertIsNone(self.api.style_rects['img'])
        self.assertIsNotNone(self.api.style_rects['blur'])
        self.assertTrue(callable(self.api.style_rects['blur']))

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

    def test_replaces_style_plus_overlay_compat_style(self):
        # 整图重绘型主样式（模糊卡片）渲染后，再叠加兼容型叠加样式（图片水印/品牌logo）
        calls = []
        def replace_renderer(img, settings, values, source=None):
            calls.append(('replace', img is source))
            out = img.copy()
            out.paste((255, 0, 0), (0, 0, 50, 50))   # 左上角红块 = 模糊卡片渲染结果
            return out
        def overlay_renderer(img, settings, values, source=None):
            calls.append(('overlay', img))
            out = img.copy()
            out.paste((0, 0, 255), (120, 60, 170, 110))   # 蓝块 = 叠加的品牌logo
            return out
        app.PLUGIN_API.styles['blur'] = ('模糊卡片', replace_renderer, True)
        app.PLUGIN_API.styles['imgwm'] = ('图片水印', overlay_renderer, False)
        img = Image.new('RGB', (200, 120), (50, 50, 50))
        settings = {'template': 'HELLO', 'font_family': '', 'style': 'blur'}
        with mock.patch('photo.render_watermark', wraps=photo.render_watermark) as mw:
            out = app.App._render_with_style(None, img, settings, {})
        # 两种样式都被调用；overlay 收到的是 replace 之后的图（文字水印之上）
        kinds = [c[0] for c in calls]
        self.assertEqual(kinds, ['replace', 'overlay'])
        self.assertIsNot(calls[1][1], img)      # overlay 收到的不是原图
        # 红块 + 蓝块都在最终图里（同时出现）
        px = out.load()
        self.assertEqual(px[10, 10][:3], (255, 0, 0))
        self.assertEqual(px[150, 80][:3], (0, 0, 255))
        mw.assert_not_called()                  # 整图重绘跳过默认文字水印

    def test_default_style_ignores_styles(self):
        # style='default' 时不调用插件样式，只画默认文字水印
        img = Image.new('RGB', (200, 120), (50, 50, 50))
        settings = {'template': 'HELLO', 'font_family': '', 'style': 'default'}
        with mock.patch('photo.render_watermark', wraps=photo.render_watermark) as mw:
            out = app.App._render_with_style(None, img, settings, {})
        mw.assert_called_once()
        self.assertEqual(len(self.received), 0)




class TestOverlaySwitch(unittest.TestCase):
    """blur_card 叠加图片水印开关（overlay_setting）。"""
    def setUp(self):
        self._orig_styles = app.PLUGIN_API.styles
        self._orig_rects = app.PLUGIN_API.style_rects
        self._orig_plugin = app.PLUGIN_API.style_plugin
        self._orig_overlay = app.PLUGIN_API.style_overlay
        app.PLUGIN_API.styles = {}
        app.PLUGIN_API.style_rects = {}
        app.PLUGIN_API.style_plugin = {}
        app.PLUGIN_API.style_overlay = {}
        self.calls = []
        def replace_r(img, settings, values, source=None):
            out = img.copy()
            out.paste((255, 0, 0), (0, 0, 20, 20))   # 红块 = blur_card 渲染
            return out
        def overlay_r(img, settings, values, source=None):
            self.calls.append('overlay')
            out = img.copy()
            out.paste((0, 0, 255), (100, 100, 120, 120))  # 蓝块 = 图片水印
            return out
        self.replace_r = replace_r
        self.overlay_r = overlay_r

    def tearDown(self):
        app.PLUGIN_API.styles = self._orig_styles
        app.PLUGIN_API.style_rects = self._orig_rects
        app.PLUGIN_API.style_plugin = self._orig_plugin
        app.PLUGIN_API.style_overlay = self._orig_overlay

    def _render(self, ov_on):
        app.PLUGIN_API.plugin_name = 'blur-card'
        app.PLUGIN_API.add_watermark_style('blur_card', '模糊卡片', self.replace_r,
                                           replaces_watermark=True,
                                           overlay_setting='blur_card_overlay_wm')
        app.PLUGIN_API.add_watermark_style('imgwm', '图片水印', self.overlay_r)
        img = Image.new('RGB', (200, 120), (50, 50, 50))
        settings = {'template': 'X', 'font_family': '', 'style': 'blur_card',
                    'plugin_values': {'blur-card': {'blur_card_overlay_wm': ov_on}}}
        return app.App._render_with_style(None, img, settings, {})

    def test_overlay_off_skips(self):
        out = self._render(False)
        self.assertEqual(self.calls, [])
        px = out.load()
        self.assertEqual(px[5, 5][:3], (255, 0, 0))
        self.assertNotEqual(px[110, 110][:3], (0, 0, 255))

    def test_overlay_on_overlays(self):
        out = self._render(True)
        self.assertEqual(self.calls, ['overlay'])
        px = out.load()
        self.assertEqual(px[110, 110][:3], (0, 0, 255))

    def test_overlay_key_missing_default_on(self):
        # 键缺失时默认 True（向后兼容：总是叠加）
        app.PLUGIN_API.plugin_name = 'blur-card'
        app.PLUGIN_API.add_watermark_style('blur_card', '模糊卡片', self.replace_r,
                                           replaces_watermark=True,
                                           overlay_setting='blur_card_overlay_wm')
        app.PLUGIN_API.add_watermark_style('imgwm', '图片水印', self.overlay_r)
        img = Image.new('RGB', (200, 120), (50, 50, 50))
        settings = {'template': 'X', 'font_family': '', 'style': 'blur_card',
                    'plugin_values': {'blur-card': {}}}
        app.App._render_with_style(None, img, settings, {})
        self.assertEqual(self.calls, ['overlay'])

    def test_legacy_plugin_always_overlays(self):
        # 未声明 overlay_setting 的旧插件：replaces 主样式下仍总是叠加
        app.PLUGIN_API.plugin_name = 'legacy'
        app.PLUGIN_API.add_watermark_style('old_style', '旧样式', self.replace_r,
                                           replaces_watermark=True)
        app.PLUGIN_API.add_watermark_style('imgwm', '图片水印', self.overlay_r)
        img = Image.new('RGB', (200, 120), (50, 50, 50))
        settings = {'template': 'X', 'font_family': '', 'style': 'old_style'}
        app.App._render_with_style(None, img, settings, {})
        self.assertEqual(self.calls, ['overlay'])


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
        # 关闭描边/阴影/品牌Logo 排除装饰干扰；前景框取统一几何 _geometry（与渲染同源）。
        img = Image.new('RGB', (800, 600), (0, 0, 0))
        s = {'template': '{make} {model}', 'font_family': '', 'font_size_pct': 3.0,
             'plugin_values': {'blur-card': {'blur_card_ratio': '16:9', 'blur_card_fg_scale': 72,
                                             'blur_card_round': 0, 'blur_card_shadow': False,
                                             'blur_card_outline': False, 'blur_card_bg_blur': 0,
                                             'blur_card_darken': 0}}}
        out = self.mod._render(img, s, {'make': 'NIKON', 'model': 'D3200'}, source=img)
        # 前景框直接取统一几何（与渲染同源），断言其内部无白色水印像素
        fx, fy, fxx, fyy = self.mod._geometry(800, 600, s)[0]
        px = out.load()
        white = 0
        for y in range(fy + 4, fyy - 4, 3):
            for x in range(fx + 4, fxx - 4, 3):
                r, g, b = px[x, y][:3]
                if r > 240 and g > 240 and b > 240:
                    white += 1
        self.assertEqual(white, 0, '前景矩形区域内不应有白色水印像素')

    def test_v2_settings_registered(self):
        # v1.2 注册设置项（五布局/边距/描边/底纹/叠加，含 header 分组）；经 _rebuild_plugin_settings 落到全局
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
            for k in ('blur_card_ratio', 'blur_card_layout', 'blur_card_fg_scale',
                      'blur_card_margin', 'blur_card_bg_blur',
                      'blur_card_darken', 'blur_card_round', 'blur_card_shadow',
                      'blur_card_outline', 'blur_card_backdrop',
                      'blur_card_overlay_wm'):
                self.assertIn(k, keys, k + ' 未注册')
            self.assertIs(_app.PLUGIN_API.styles['blur_card'][2], True)
        finally:
            _app.PLUGIN_API.setting_specs = _orig_specs
            _app.PLUGIN_API.styles = _orig_styles
            _app._rebuild_plugin_settings()

    def test_text_moves_with_offset(self):
        # blur-card 文字信息栏随 offset_x_pct/offset_y_pct 平移（与 _blur_card_rect 一致）
        img = Image.new('RGB', (800, 600), (0, 0, 0))
        base_s = {'template': 'X', 'font_family': '',
                  'plugin_values': {'blur-card': {'blur_card_ratio': '16:9',
                                                  'blur_card_outline': False,
                                                  'blur_card_shadow': False}}}
        r0 = self.mod._blur_card_rect(dict(base_s, offset_x_pct=0, offset_y_pct=0),
                                      {'make': 'S'}, img.size)
        r5 = self.mod._blur_card_rect(dict(base_s, offset_x_pct=5, offset_y_pct=10),
                                      {'make': 'S'}, img.size)
        self.assertIsNotNone(r0)
        self.assertIsNotNone(r5)
        self.assertEqual(r5[0] - r0[0], int(0.05 * 800))
        self.assertEqual(r5[1] - r0[1], int(0.10 * 600))

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


class TestBadgeRows(unittest.TestCase):
    """参数标签框：值清洗、字段模板顺序、空值跳过、整管线冒烟。"""
    def setUp(self):
        self.mod = load_blur_card()
        self.values = {'make': 'NIKON', 'model': 'D3200', 'focal': '35mm',
                       'aperture': 'F1.79', 'shutter': '1/2151s', 'iso': 'ISO 222'}

    def _settings(self, order='跟随文字模板', tpl='', badge=True):
        return {'template': tpl,
                'plugin_values': {'blur-card': {
                    'blur_card_badge_order': order, 'blur_card_badge': badge}}}

    def test_clean_helpers(self):
        m = self.mod
        self.assertEqual(m._clean_aperture('F1.79'), '1.79')
        self.assertEqual(m._clean_aperture('f/2.8'), '2.8')
        self.assertEqual(m._clean_shutter('1/2151s'), '1/2151')
        self.assertEqual(m._clean_iso('ISO 222'), '222')
        self.assertEqual(m._clean_focal('35mm'), '35')

    def test_fixed_preset_order_and_labels(self):
        rows = m = self.mod._badge_rows(self.values, self._settings('F / S / ISO'))
        self.assertEqual([k for k, _ in m], ['F', 'S', 'ISO'])
        self.assertEqual([v for _, v in m], ['1.79', '1/2151', '222'])

    def test_preset_with_focal(self):
        rows = self.mod._badge_rows(self.values, self._settings('mm / F / S / ISO'))
        self.assertEqual([k for k, _ in rows], ['mm', 'F', 'S', 'ISO'])
        self.assertEqual(rows[0], ('mm', '35'))

    def test_follow_template_token_order(self):
        s = self._settings('跟随文字模板', '{iso} {aperture} {shutter}')
        rows = self.mod._badge_rows(self.values, s)
        self.assertEqual([k for k, _ in rows], ['ISO', 'F', 'S'])

    def test_template_without_param_tokens_falls_back(self):
        # 模板无任何 badge 字段 token（品牌/参数都没有）才兜底到 F/S/ISO；
        # 含 {make}/{model} 时按新功能正常识别为品牌/型号 badge
        s = self._settings('跟随文字模板', '{date} {time}')
        rows = self.mod._badge_rows(self.values, s)
        self.assertEqual([k for k, _ in rows], ['F', 'S', 'ISO'])
        s2 = self._settings('跟随文字模板', '{make} {model}')
        rows2 = self.mod._badge_rows(self.values, s2)
        self.assertEqual([k for k, _ in rows2], ['F', 'S', 'ISO'])   # 无数值 token 兜底
        self.assertEqual(self.mod._badge_title(self.values, s2), 'NIKON D3200')  # 品牌型号走无框标题

    def test_skip_empty_values(self):
        v = dict(self.values); v['iso'] = ''
        rows = self.mod._badge_rows(v, self._settings('F / S / ISO'))
        self.assertEqual([k for k, _ in rows], ['F', 'S'])

    def test_preset_with_brand(self):
        s = self._settings('品牌 / F / S / ISO')
        rows = self.mod._badge_rows(self.values, s)
        self.assertEqual([k for k, _ in rows], ['F', 'S', 'ISO'])       # 品牌不进框
        self.assertEqual(self.mod._badge_title(self.values, s), 'NIKON')  # 仅作无框标题

    def test_preset_with_brand_model(self):
        s = self._settings('品牌 / 型号 / F / S / ISO')
        rows = self.mod._badge_rows(self.values, s)
        self.assertEqual([k for k, _ in rows], ['F', 'S', 'ISO'])  # 品牌型号不进框
        self.assertEqual(self.mod._badge_title(self.values, s), 'NIKON D3200')  # 无框标题

    def test_brand_title_dedup_prefix(self):
        v = dict(self.values, model='NIKON D3200')      # model 已含 make 前缀
        s = self._settings('品牌 / 型号 / F / S / ISO')
        self.assertEqual(self.mod._badge_title(v, s), 'NIKON D3200')      # 不重复品牌

    def test_brand_title_subbrand_no_dup(self):
        # model 已是市场名且自带子品牌词(Redmi)，不再前置拼 Xiaomi
        v = dict(self.values, make='Xiaomi', model='Redmi Note 12 Turbo')
        s = self._settings('品牌 / 型号 / F / S / ISO')
        self.assertEqual(self.mod._badge_title(v, s), 'Redmi Note 12 Turbo')

    def test_left_brand_strips_param_tokens(self):
        v = dict(self.values, make='Xiaomi', model='Redmi Note 12 Turbo')
        # 默认单行全字段模板：左块只留品牌型号，光圈/快门/ISO/焦距一律剔除归右块
        tpl = '{make}  {model}   {focal}  {shutter}  {aperture}  {iso}'
        left = self.mod._left_brand_text(tpl, v)
        for leaked in ('1.79', '1/2151', '222', '35mm'):
            self.assertNotIn(leaked, left)
        self.assertIn('Xiaomi', left)
        self.assertIn('Redmi Note 12 Turbo', left)

    def test_left_brand_empty_when_only_params(self):
        tpl = '{focal} {shutter} {aperture} {iso}'
        self.assertEqual(self.mod._left_brand_text(tpl, self.values), '')

    def test_left_brand_keeps_camera_token(self):
        v = dict(self.values, camera='Redmi Note 12 Turbo')
        self.assertEqual(self.mod._left_brand_text('{camera}', v), 'Redmi Note 12 Turbo')

    def test_badge_skips_empty_brand(self):
        v = dict(self.values); v['make'] = ''; v['model'] = ''
        s = self._settings('品牌 / 型号 / F / S / ISO')
        rows = self.mod._badge_rows(v, s)
        self.assertEqual([k for k, _ in rows], ['F', 'S', 'ISO'])  # 数值照常出框
        self.assertEqual(self.mod._badge_title(v, s), '')                # 无品牌则无标题

    def test_badge_horizontal_render_smoke(self):
        # 下参数（宽条）横排 badge 渲染：不崩、尺寸不变、无前景白字干扰
        img = Image.new('RGB', (900, 600), (40, 80, 120))
        s = self._settings('品牌 / F / S / ISO', '{make}\n{aperture} {shutter} {iso}')
        s.update(font_family='微软雅黑', font_size_pct=2.2, text_color='#ffffff',
                 text_opacity=1.0, offset_x_pct=0, offset_y_pct=0)
        s['plugin_values']['blur-card'].update(
            blur_card_layout='下参数', blur_card_ratio='16:9', blur_card_fg_scale=72,
            blur_card_margin=4, blur_card_bg_blur=3, blur_card_darken=30,
            blur_card_backdrop=0, blur_card_round=12, blur_card_shadow=True,
            blur_card_outline=True, blur_card_badge=True, blur_card_badge_order='品牌 / F / S / ISO')
        vals = dict(self.values, camera='NIKON', lens='', date='', time='')
        out = self.mod._render(img.copy(), s, vals, source=img)
        self.assertEqual(out.size, img.size)

    def test_render_split_pipeline_smoke(self):
        img = Image.new('RGB', (900, 1200), (40, 80, 120))
        s = self._settings('F / S / ISO', '{make}\n{aperture} {shutter} {iso}')
        s.update(font_family='微软雅黑', font_size_pct=2.2, text_color='#ffffff',
                 text_opacity=1.0, offset_x_pct=0, offset_y_pct=0)
        s['plugin_values']['blur-card'].update(
            blur_card_layout='左右分离', blur_card_ratio='3:4', blur_card_fg_scale=72,
            blur_card_margin=4, blur_card_bg_blur=3, blur_card_darken=30,
            blur_card_backdrop=0, blur_card_round=12, blur_card_shadow=True,
            blur_card_outline=True)
        vals = dict(self.values, make='vivo', model='', camera='vivo',
                    lens='', date='', time='')
        out = self.mod._render(img.copy(), s, vals, source=img)
        self.assertEqual(out.size, img.size)


class TestBrandLogoPreset(unittest.TestCase):
    """「品牌标 / F / S / ISO」：品牌=image-watermark 白色 logo 图、参数=文字框；五布局通用、左右分离左图右参。"""
    def setUp(self):
        self.mod = load_blur_card()
        self.values = {'make': 'SONY', 'model': 'ILCE-7CM2', 'focal': '35mm',
                       'aperture': 'F1.79', 'shutter': '1/250s', 'iso': 'ISO100'}

    def _settings(self, layout, order='品牌标 / F / S / ISO'):
        return {'template': '{make} {model}\n{aperture} {shutter} {iso}', 'font_family': '',
                'plugin_values': {'blur-card': {'blur_card_layout': layout, 'blur_card_ratio': '3:4',
                    'blur_card_badge': True, 'blur_card_badge_order': order}}}

    def test_is_logo_order(self):
        self.assertTrue(self.mod._is_logo_order(self._settings('下参数')))
        self.assertFalse(self.mod._is_logo_order(
            {'plugin_values': {'blur-card': {'blur_card_badge_order': 'F / S / ISO'}}}))

    def test_brand_logo_path_match(self):
        p = self.mod._brand_logo_path({'make': 'SONY'})
        self.assertTrue(p and p.endswith('sony_w.png'))
        self.assertEqual(os.path.basename(self.mod._brand_logo_path({'make': 'NIKON CORPORATION'}) or ''),
                         'nikon_w.png')
        self.assertIsNone(self.mod._brand_logo_path({'make': 'UNKNOWN-MOBILE'}))
        self.assertIsNone(self.mod._brand_logo_path({'make': ''}))

    def test_logo_order_rows_are_params_only(self):
        st = self._settings('左右分离')
        rows = self.mod._badge_rows(self.values, st)
        self.assertEqual([k for k, _ in rows], ['F', 'S', 'ISO'])      # 品牌不进参数框
        self.assertEqual(self.mod._badge_title(self.values, st), 'SONY')  # 缺 logo 时文字兜底

    @unittest.skipUnless(os.path.exists(os.path.join(
        BASE, 'plugins', 'image-watermark', 'presets', 'sony_w.png')),
        'image-watermark 预设未安装')
    def test_split_left_draws_logo(self):
        # 左右分离：左块出现白色 SONY logo 像素，整体不崩、尺寸不变
        img = Image.new('RGB', (900, 1200), (40, 60, 90))
        st = self._settings('左右分离')
        out = self.mod._render(img.copy(), st, dict(self.values), source=img)
        self.assertEqual(out.size, img.size)
        _, boxes, _ = self.mod._geometry(900, 1200, st)
        x0, y0, x1, y1 = boxes[0]
        px = out.load(); white = 0
        for y in range(y0 + 2, y1 - 2, 4):
            for x in range(x0 + 2, x1 - 2, 4):
                r, g, b = px[x, y][:3]
                if r > 235 and g > 235 and b > 235:
                    white += 1
        self.assertGreater(white, 5, '左右分离左块应出现白色品牌 logo 像素')

    def test_logo_text_order_detected(self):
        m = self.mod
        self.assertTrue(m._is_logo_text_order(self._settings('下参数', '品牌标 + 文字')))
        self.assertFalse(m._is_logo_text_order(self._settings('下参数', '品牌标 / F / S / ISO')))
        self.assertFalse(m._is_logo_text_order(self._settings('下参数', 'F / S / ISO')))

    def test_logo_text_render_smoke_all_layouts(self):
        # 「品牌标 + 文字」：五布局都不崩、尺寸不变（SONY 有 logo，走 logo+文字路径）
        img = Image.new('RGB', (900, 1200), (40, 60, 90))
        for lay in ['下参数', '上参数', '左参数', '右参数', '左右分离']:
            st = self._settings(lay, '品牌标 + 文字')
            st.update(font_family='微软雅黑', font_size_pct=2.2, text_color='#ffffff',
                      text_opacity=1.0, offset_x_pct=0, offset_y_pct=0)
            out = self.mod._render(img.copy(), st, dict(self.values), source=img)
            self.assertEqual(out.size, img.size, lay)

    def test_badge_scale_render_smoke(self):
        # 品牌标/参数框大小 50/200 渲染不崩、尺寸不变
        img = Image.new('RGB', (900, 1200), (40, 60, 90))
        for scale in (50, 100, 200):
            st = self._settings('左右分离', '品牌标 / F / S / ISO')
            st.update(font_family='微软雅黑', font_size_pct=2.2, text_color='#ffffff',
                      text_opacity=1.0, offset_x_pct=0, offset_y_pct=0)
            st['plugin_values']['blur-card']['blur_card_badge_scale'] = scale
            out = self.mod._render(img.copy(), st, dict(self.values), source=img)
            self.assertEqual(out.size, img.size, 'scale=%s' % scale)

    def test_unknown_brand_falls_back_all_layouts(self):
        # 匹配不到 logo 时五种布局都不崩（回退文字品牌/仅参数）
        v = dict(self.values, make='UNKNOWN')
        for lay in ['下参数', '上参数', '左参数', '右参数', '左右分离']:
            img = Image.new('RGB', (900, 1200), (40, 60, 90))
            out = self.mod._render(img.copy(), self._settings(lay), v, source=img)
            self.assertEqual(out.size, img.size, lay)


if __name__ == '__main__':
    unittest.main(verbosity=2)
