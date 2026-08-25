# -*- coding: utf-8 -*-
"""test_photo.py - 单元测试（python -m unittest test_photo -v）"""
import os
import sys
import unittest
import io

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import photo
from PIL import Image


class TestFormat(unittest.TestCase):
    def test_shutter(self):
        self.assertEqual(photo.format_shutter(0.004), '1/250s')
        self.assertEqual(photo.format_shutter(0.008), '1/125s')
        self.assertEqual(photo.format_shutter(0.5), '1/2s')
        self.assertEqual(photo.format_shutter(0.3), '0.3s')
        self.assertEqual(photo.format_shutter(1), '1s')
        self.assertEqual(photo.format_shutter(1.3), '1.3s')
        self.assertEqual(photo.format_shutter(0), '')
        self.assertEqual(photo.format_shutter(None), '')

    def test_aperture(self):
        self.assertEqual(photo.format_aperture(5.6), 'F5.6')
        self.assertEqual(photo.format_aperture(2.8), 'F2.8')
        self.assertEqual(photo.format_aperture(0), '')

    def test_iso(self):
        self.assertEqual(photo.format_iso(100), 'ISO 100')
        self.assertEqual(photo.format_iso(3200), 'ISO 3200')
        self.assertEqual(photo.format_iso(0), '')

    def test_focal(self):
        self.assertEqual(photo.format_focal(60), '60mm')
        self.assertEqual(photo.format_focal(28.5), '28.5mm')

    def test_camera_name(self):
        self.assertEqual(photo.friendly_camera_name('SONY', 'ILCE-7CM2'), 'Sony A7C II')
        self.assertEqual(photo.friendly_camera_name('SONY', 'ILCE-7M4'), 'Sony A7 IV')
        self.assertEqual(photo.friendly_camera_name('Canon', 'EOS R5'), 'Canon EOS R5')
        self.assertEqual(photo.friendly_camera_name('', ''), '')

    def test_default_template(self):
        # 新默认预设：{make}  {model}   {focal}  {shutter}  {aperture}  {iso}
        self.assertEqual(
            photo.DEFAULT_SETTINGS['template'],
            '{make}  {model}   {focal}  {shutter}  {aperture}  {iso}')
        v = {'make': 'SONY', 'model': 'ILCE-7CM2', 'focal': '60mm',
             'shutter': '1/250s', 'aperture': 'F5.6', 'iso': 'ISO 100'}
        self.assertEqual(photo.render_template(photo.DEFAULT_SETTINGS['template'], v),
                         'SONY  ILCE-7CM2   60mm  1/250s  F5.6  ISO 100')

    def test_template(self):
        v = {'camera': 'Sony A7C II', 'shutter': '1/250s', 'aperture': 'F5.6', 'iso': 'ISO 100', 'focal': '60mm'}
        self.assertEqual(photo.render_template('{camera}\n{focal} {shutter} {aperture} {iso}', v),
                         'Sony A7C II\n60mm 1/250s F5.6 ISO 100')
        self.assertEqual(photo.render_template('{camera}\n{unknown}', v), 'Sony A7C II')
        self.assertEqual(photo.render_template('', v), '')


class TestRaw(unittest.TestCase):
    def test_extract_embedded_jpeg(self):
        arw = r"E:\图片\2.25\raw\_DSC0003.ARW"
        if not os.path.exists(arw):
            self.skipTest('无测试 RAW 文件')
        with open(arw, 'rb') as f:
            buf = f.read()
        jpg = photo.extract_embedded_jpeg(buf)
        self.assertIsNotNone(jpg)
        self.assertTrue(jpg[:2] == b'\xff\xd8')
        im = Image.open(io.BytesIO(jpg))
        self.assertGreater(im.width, 1000)  # 全尺寸预览

    def test_meta_raw(self):
        arw = r"E:\图片\2.25\raw\_DSC0003.ARW"
        if not os.path.exists(arw):
            self.skipTest('无测试 RAW 文件')
        m = photo.read_meta(arw)
        self.assertEqual(m['make'], 'SONY')
        self.assertEqual(m['model'], 'ILCE-7CM2')
        self.assertIn('A7C', m['camera_text'])
        self.assertEqual(m['shutter_text'], '1/250s')
        self.assertEqual(m['iso_text'], 'ISO 100')

    def test_meta_jpg(self):
        jpg = r"E:\图片\2.25\jpg\DSC00001.JPG"
        if not os.path.exists(jpg):
            self.skipTest('无测试 JPG 文件')
        m = photo.read_meta(jpg)
        self.assertEqual(m['make'], 'SONY')
        self.assertGreater(m['width'], 0)
        self.assertNotEqual(m['shutter_text'], '')


class TestOrientation(unittest.TestCase):
    def test_apply_orientation(self):
        img = Image.new('RGB', (800, 600), (255, 0, 0))  # 横向 800x600
        # 方向 8：显示时应为竖图 600x800
        out = photo.apply_orientation(img, 8)
        self.assertEqual(out.size, (600, 800))
        # 方向 1 / None：不变
        self.assertEqual(photo.apply_orientation(img, 1).size, (800, 600))
        self.assertEqual(photo.apply_orientation(img, None).size, (800, 600))
        # 非法值：不变
        self.assertEqual(photo.apply_orientation(img, 'x').size, (800, 600))

    def test_orientation_consistency_jpg(self):
        # 竖拍 JPG（方向8）经 exif_transpose 与 apply_orientation 结果一致
        jpg = r"E:\图片\2.25\jpg\DSC00001.JPG"
        if not os.path.exists(jpg):
            self.skipTest('无测试 JPG')
        from PIL import ImageOps
        a = ImageOps.exif_transpose(Image.open(jpg).convert('RGB'))
        b = photo.apply_orientation(Image.open(jpg).convert('RGB'), 8)
        self.assertEqual(a.size, b.size)


class TestRender(unittest.TestCase):
    def test_render_small(self):
        img = Image.new('RGB', (800, 600), (128, 128, 128))
        s = dict(photo.DEFAULT_SETTINGS)
        v = {'camera': 'Sony A7C II', 'shutter': '1/250s', 'aperture': 'F5.6', 'iso': 'ISO 100', 'focal': '60mm'}
        out = photo.render_watermark(img, s, v)
        self.assertEqual(out.size, (800, 600))
        # 底部中央区域应有白色文字
        px = out.load()
        w, h = out.size
        white = False
        for y in range(h - 140, h - 20, 3):
            for x in range(w // 2 - 300, w // 2 + 300, 3):
                if px[x, y][0] > 240:
                    white = True
                    break
            if white:
                break
        self.assertTrue(white, '水印文字应渲染为白色')


if __name__ == '__main__':
    unittest.main(verbosity=2)
