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




class TestCroppedWatermark(unittest.TestCase):
    """裁剪预览图（大图放大）模式：render_watermark 按全图坐标定位水印，
    与全图渲染后裁剪对应区域逐像素一致（防止水印位置错乱）。"""
    BASE = {
        'template': '{make}  {model}   {shutter}  {aperture}  {iso}',
        'font_family': '', 'font_size_pct': 2.0, 'line_spacing': 0.35,
        'bg_padding': 0.6, 'anchor': 7, 'margin_pct': 5.0,
        'offset_x_pct': 0.0, 'offset_y_pct': 0.0,
        'bg_enabled': True, 'bg_color': '#000000', 'bg_opacity': 0.5,
        'text_color': '#ffffff', 'text_opacity': 1.0,
        'shadow_enabled': False, 'outline_enabled': False,
    }
    VALUES = {'make': 'SONY', 'model': 'ILCE-7M4', 'shutter': '1/100s',
              'aperture': 'F5', 'iso': 'ISO 100'}

    def _assert_aligns(self, img_size=(1200, 1800)):
        img = Image.new('RGB', img_size, (40, 40, 40))
        full_out = photo.render_watermark(img, dict(self.BASE), dict(self.VALUES))
        r = photo.watermark_rect(img, dict(self.BASE), dict(self.VALUES))
        self.assertIsNotNone(r)
        W, H = img.size
        vcx = (r[0] + r[2]) // 2
        vcy = (r[1] + r[3]) // 2
        vw, vh = 500, 400
        vx = max(0, min(W - vw, vcx - vw // 2))
        vy = max(0, min(H - vh, vcy - vh // 2))
        crop = img.crop((vx, vy, vx + vw, vy + vh))
        crop_out = photo.render_watermark(crop, dict(self.BASE), dict(self.VALUES),
                                          full_size=(W, H), origin=(vx, vy))
        full_patch = full_out.crop((vx, vy, vx + vw, vy + vh))
        self.assertEqual(crop_out.size, full_patch.size)
        p1 = full_patch.load(); p2 = crop_out.load()
        for y in range(0, full_patch.size[1], 3):
            for x in range(0, full_patch.size[0], 3):
                self.assertEqual(p1[x, y], p2[x, y],
                                 '裁剪预览水印与全图渲染不一致 @ (%d,%d)' % (x, y))

    def test_aligns_landscape(self):
        self._assert_aligns((1600, 1000))

    def test_aligns_portrait(self):
        self._assert_aligns((1200, 1800))

    def test_watermark_outside_crop_returns_unchanged(self):
        img = Image.new('RGB', (1000, 800), (40, 40, 40))
        # 窗口选在左上角极小区域，水印（右下角）完全在窗外
        crop = img.crop((0, 0, 100, 80))
        out = photo.render_watermark(crop, dict(self.BASE), dict(self.VALUES),
                                     full_size=img.size, origin=(0, 0))
        px = out.load()
        self.assertEqual(px[50, 40], (40, 40, 40), '水印在窗口外时不应绘制')



class TestWordSpacing(unittest.TestCase):
    """参数间距（word_spacing）：>0 时 block 变宽、按 token 绘制；=0 时与旧版一致。"""
    BASE = {'template': '{make} {model} {focal} {shutter}', 'font_family': '',
            'font_size_pct': 3.0, 'anchor': 7, 'margin_pct': 5.0,
            'offset_x_pct': 0, 'offset_y_pct': 0}
    V = {'make': 'SONY', 'model': 'ILCE-7M4', 'focal': '50mm', 'shutter': '1/800s'}

    def _rect(self, ws):
        img = Image.new('RGB', (800, 600), (0, 0, 0))
        return photo.watermark_rect(img, dict(self.BASE, word_spacing=ws), dict(self.V))

    def test_spacing_widens_block(self):
        r0 = self._rect(0)
        r2 = self._rect(2.0)
        self.assertGreater(r2[2] - r2[0], r0[2] - r0[0])

    def test_zero_unchanged(self):
        # ws=0 渲染像素级与旧版（无 word_spacing 键）一致
        img = Image.new('RGB', (800, 600), (0, 0, 0))
        a = photo.render_watermark(img, dict(self.BASE, word_spacing=0), dict(self.V))
        b = photo.render_watermark(img, dict(self.BASE), dict(self.V))
        self.assertEqual(list(a.getdata()), list(b.getdata()))

    def test_spacing_renders_tokens(self):
        img = Image.new('RGB', (800, 600), (0, 0, 0))
        out = photo.render_watermark(img, dict(self.BASE, word_spacing=2.0), dict(self.V))
        self.assertEqual(out.size, (800, 600))
        px = out.load()
        non_bg = sum(1 for y in range(0, 600, 4) for x in range(0, 800, 4)
                     if px[x, y][:3] != (0, 0, 0))
        self.assertGreater(non_bg, 0)

if __name__ == '__main__':
    unittest.main(verbosity=2)
