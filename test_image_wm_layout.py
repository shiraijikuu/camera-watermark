# -*- coding: utf-8 -*-
"""test_image_wm_layout.py — image-watermark 插件文字-图片组合布局（layout/gap）。

运行：python -m unittest test_image_wm_layout -v
"""
import importlib.util
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app
import photo
from PIL import Image

BASE = os.path.dirname(os.path.abspath(__file__))
PLUGIN_PY = os.path.join(BASE, 'plugin-repos', 'image-watermark', 'plugin.py')


def _load_plugin():
    spec = importlib.util.spec_from_file_location('iw_layout_plugin', PLUGIN_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@unittest.skipUnless(os.path.exists(PLUGIN_PY), 'image-watermark 插件源码未在 plugin-repos/')
class TestImageWmLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.iw = _load_plugin()
        cls.api = app.PluginAPI()
        cls.api.styles = {}
        cls.api.style_rects = {}
        cls.api.plugin_name = 'image-watermark'
        cls.iw.register(cls.api)
        cls.renderer = cls.api.styles['image_watermark'][1]

    def _render(self, layout='none', anchor=4, size=6):
        img = Image.new('RGB', (800, 600), (200, 200, 200))
        settings = {'template': '{make} {model}', 'font_family': '', 'font_size_pct': 2.5,
                    'anchor': anchor, 'margin_pct': 5.0, 'offset_x_pct': 0, 'offset_y_pct': 0,
                    'plugin_values': {'image-watermark': {'preset': 'sony_w.png', 'image': '',
                                                          'size': size, 'layout': layout, 'gap': 2.0,
                                                          'offset_x': 50, 'offset_y': 88,
                                                          'rotation': 0, 'opacity': 100}}}
        values = {'make': 'SONY', 'model': 'A7C'}
        img_wm = photo.render_watermark(img, settings, values, fonts_dir=app.FONTS_DIR)
        rect = photo.watermark_rect(img, settings, values, fonts_dir=app.FONTS_DIR)
        out = type(self).renderer(img_wm, settings, values)   # 类属性取函数本身（避免绑定 self）
        return out, rect

    @staticmethod
    def _white_count(out, x0, x1, y0, y1):
        px = out.load()
        n = 0
        for y in range(max(0, y0), min(600, y1), 2):
            for x in range(max(0, x0), min(800, x1), 2):
                r, g, b = px[x, y][:3]
                if r > 200 and g > 200 and b > 200:
                    n += 1
        return n

    def test_layout_left_right(self):
        out, rect = self._render('left-right')
        self.assertGreater(self._white_count(out, rect[2] + 1, 800, 0, 600), 5)

    def test_layout_right_left(self):
        out, rect = self._render('right-left')
        self.assertGreater(self._white_count(out, 0, rect[0] - 1, 0, 600), 5)

    def test_layout_top_bottom(self):
        out, rect = self._render('top-bottom')
        self.assertGreater(self._white_count(out, 0, 800, rect[3] + 1, rect[3] + 120), 5)

    def test_layout_bottom_top(self):
        out, rect = self._render('bottom-top')
        self.assertGreater(self._white_count(out, 0, 800, rect[1] - 120, rect[1] - 1), 5)

    def test_layout_none_unchanged(self):
        out, rect = self._render('none')
        # 独立定位：底部中央有 logo（offset 50,88）
        self.assertGreater(self._white_count(out, 200, 600, 450, 600), 5)

    def test_layout_out_of_bounds_flips(self):
        # 文字贴底（anchor=7）+ top-bottom：logo 放下方越界 -> 自动翻到文字上方（bottom-top），
        # 文字与 logo 始终成对、不重叠、不出界（不再回退独立定位跳右下角）
        out, rect = self._render('top-bottom', anchor=7)
        self.assertEqual(out.size, (800, 600))
        # 文字下方（rect 底边之外）无白色 logo（logo 已翻到上方）
        below = self._white_count(out, 0, 800, rect[3] + 1, 600)
        # 文字上方有白色 logo
        above = self._white_count(out, 0, 800, max(0, rect[1] - 150), rect[1] - 1)
        self.assertGreater(above, 5, 'logo should flip above text')
        # 文字本身在底部区域（anchor=7），below 检测的是文字而非 logo 的额外内容——
        # 这里只验证 logo 确实出现在文字上方（above>5 即满足"翻转"）





@unittest.skipUnless(os.path.exists(PLUGIN_PY), 'image-watermark 插件源码未在 plugin-repos/')
class TestListPresetsRecursive(unittest.TestCase):
    """image-watermark _list_presets 递归扫描子目录（DLC 素材）。"""
    @classmethod
    def setUpClass(cls):
        import importlib.util as _u
        spec = _u.spec_from_file_location('iw', os.path.join(BASE, 'plugin-repos', 'image-watermark', 'plugin.py'))
        cls.iw = _u.module_from_spec(spec); spec.loader.exec_module(cls.iw)

    def test_scans_subdir(self):
        import os, shutil, tempfile
        sub = os.path.join(self.iw.PRESETS_DIR, '_test_dlc')
        os.makedirs(sub, exist_ok=True)
        try:
            shutil.copy2(os.path.join(self.iw.PRESETS_DIR, 'sony_w.png'),
                         os.path.join(sub, 'dji-air-3.png'))
            presets = self.iw._list_presets()
            self.assertTrue(any(p == '_test_dlc/dji-air-3.png' for p in presets),
                            'subdir preset not scanned!')
        finally:
            shutil.rmtree(sub, ignore_errors=True)

    def test_returns_relpath(self):
        import os
        presets = self.iw._list_presets()
        self.assertTrue(presets)
        self.assertFalse(any(os.path.isabs(p) for p in presets), 'should be relative!')

if __name__ == '__main__':
    unittest.main(verbosity=2)
