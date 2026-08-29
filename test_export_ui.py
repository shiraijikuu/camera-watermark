# -*- coding: utf-8 -*-
"""test_export_ui.py — 导出逐文件结果统计（纯逻辑，不依赖 GUI）。

运行：python -m unittest test_export_ui -v
"""
import os
import queue
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app
import photo
from PIL import Image


class FakeWorker:
    def __init__(self, photos):
        self.photos = photos
        self.msg_q = queue.Queue()
        self.cancel = False
        self.settings = {'suffix': '_wm', 'jpeg_quality': 95, 'preserve_exif': True,
                         'template': 'x', 'anchor': 7, 'font_size_pct': 2.0,
                         'line_spacing': 0.35, 'text_opacity': 1.0, 'bg_padding': 0.6,
                         'bg_enabled': False, 'shadow_enabled': False, 'outline_enabled': False,
                         'offset_x_pct': 0.0, 'offset_y_pct': 0.0, 'margin_pct': 0.5,
                         'style': 'default'}

    def _open_oriented(self, path, orientation=None):
        if 'BAD' in path:
            raise ValueError('open failed')
        return Image.new('RGB', (200, 100), (255, 255, 255))

    def _render_with_style(self, img, s, values):
        return img

    def _apply_export_hooks(self, img, meta, s):
        return img

    def _unique_path(self, p):
        return p


def make_photo(name, raw=False):
    return {'path': name, 'name': name, 'raw': raw, 'checked': True,
            'meta': {'orientation': 1, 'width': 200, 'height': 100}}


class TestExportWorkerStats(unittest.TestCase):
    def setUp(self):
        self._orig_save = app.photo.save_watermarked
        app.photo.save_watermarked = lambda *a, **k: None
        self.addCleanup(setattr, app.photo, "save_watermarked", self._orig_save)

    def _run(self, photos, outdir):
        w = FakeWorker(photos)
        app.App._export_worker(w, photos, outdir, 'jpg')
        msgs = []
        while not w.msg_q.empty():
            msgs.append(w.msg_q.get_nowait())
        done = [m for m in msgs if m[0] == 'export_done'][0][1]
        return done, msgs

    def test_all_success(self):
        done, _ = self._run([make_photo('A.JPG'), make_photo('B.JPG')], 'out')
        self.assertEqual(done['success'], 2)
        self.assertEqual(done['fail'], 0)
        self.assertEqual(done['skip'], 0)

    def test_mixed_fail(self):
        done, _ = self._run([make_photo('GOOD.JPG'), make_photo('BAD.JPG')], 'out')
        self.assertEqual(done['success'], 1)
        self.assertEqual(done['fail'], 1)
        self.assertEqual(len(done['errors']), 1)
        self.assertIn('BAD', done['errors'][0][0])

    def test_cancel_skips_remaining(self):
        w = FakeWorker([make_photo('A.JPG'), make_photo('B.JPG'), make_photo('C.JPG')])
        # 让第二次迭代触发 cancel
        orig_open = w._open_oriented
        count = [0]
        def open_w(path, orientation=None):
            count[0] += 1
            if count[0] == 2:
                w.cancel = True
            return orig_open(path, orientation)
        w._open_oriented = open_w
        app.App._export_worker(w, w.photos, 'out', 'jpg')
        done = None
        while not w.msg_q.empty():
            m = w.msg_q.get_nowait()
            if m[0] == 'export_done':
                done = m[1]
        # 取消在“当前文件处理完”后生效：A、B 完成，C 跳过
        self.assertEqual(done['success'], 2)
        self.assertEqual(done['skip'], 1)


class TestCropExportRatio(unittest.TestCase):
    """导出比例居中裁剪纯函数 app.crop_to_export_ratio。"""
    def _img(self, w, h):
        return Image.new('RGB', (w, h))

    def test_original_or_unknown_unchanged(self):
        im = self._img(200, 100)
        for key in ('original', None, '', 'unknown'):
            self.assertIs(app.crop_to_export_ratio(im, key), im)

    def test_landscape_to_square(self):
        self.assertEqual(app.crop_to_export_ratio(self._img(200, 100), '1:1').size, (100, 100))

    def test_portrait_to_square(self):
        self.assertEqual(app.crop_to_export_ratio(self._img(100, 200), '1:1').size, (100, 100))

    def test_landscape_to_4_5_crops_width(self):
        # 200x100，目标 宽/高=0.8 -> 宽裁到 80，高不变
        self.assertEqual(app.crop_to_export_ratio(self._img(200, 100), '4:5').size, (80, 100))

    def test_portrait_to_wide_crops_height(self):
        # 100x200，目标 16:9≈1.778 -> 高裁到 round(100/1.778)=56，宽不变
        self.assertEqual(app.crop_to_export_ratio(self._img(100, 200), '16:9').size, (100, 56))

    def test_already_matching_ratio_unchanged(self):
        im = self._img(100, 100)
        self.assertIs(app.crop_to_export_ratio(im, '1:1'), im)

    def test_center_crop_keeps_middle_band(self):
        # 左 50 列红、中间 100 列绿、右 50 列蓝；裁成 1:1 后应只剩中间绿带
        im = Image.new('RGB', (200, 100), (0, 255, 0))
        px = im.load()
        for x in range(200):
            for y in range(100):
                if x < 50:
                    px[x, y] = (255, 0, 0)
                elif x >= 150:
                    px[x, y] = (0, 0, 255)
        out = app.crop_to_export_ratio(im, '1:1')
        self.assertEqual(out.size, (100, 100))
        op = out.load()
        for xy in ((0, 0), (99, 0), (0, 99), (99, 99), (50, 50)):
            self.assertEqual(op[xy], (0, 255, 0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
