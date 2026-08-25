# -*- coding: utf-8 -*-
"""图片水印插件：上传自定义图片作为水印。
- 仅用于普通图片，RAW 自动跳过（避免加载过久）
- 图片大小 / 位置 / 旋转 / 不透明度可自定义（「导出」页 -> 「插件设置」）
"""
import os
from PIL import Image

PLUGIN_NAME = 'image-watermark'


def register(api):
    # 注册插件设置项（「插件设置」窗口里调整，保存到 config.json）
    api.add_setting('image', '水印图片文件 (Image file)', 'file', '')
    api.add_setting('size', '水印大小 % 宽 (Size % width)', 'number', 15)
    api.add_setting('position', '位置 (Position)', 'select', '右下',
                    options=['左上', '上中', '右上', '左中', '中', '右中', '左下', '下中', '右下'])
    api.add_setting('rotation', '旋转角度 (Rotation deg)', 'number', 0)
    api.add_setting('opacity', '不透明度 0-100 (Opacity)', 'number', 100)

    def render(img, settings, values):
        # RAW 不加水印，避免加载过久
        if values.get('raw'):
            return img

        vals = (settings.get('plugin_values') or {}).get(PLUGIN_NAME, {})
        path = str(vals.get('image', '') or '').strip()
        if not path or not os.path.exists(path):
            return img

        try:
            logo = Image.open(path).convert('RGBA')
        except Exception:
            return img

        # 大小：占图片宽度百分比
        try:
            size_pct = float(vals.get('size', 15))
        except (TypeError, ValueError):
            size_pct = 15
        target_w = max(1, int(img.width * size_pct / 100))
        ratio = target_w / float(logo.width)
        logo = logo.resize((target_w, max(1, int(logo.height * ratio))), Image.LANCZOS)

        # 旋转
        try:
            angle = float(vals.get('rotation', 0))
        except (TypeError, ValueError):
            angle = 0
        if angle:
            logo = logo.rotate(angle, expand=True, resample=Image.BICUBIC)

        # 不透明度
        try:
            opacity = float(vals.get('opacity', 100)) / 100.0
        except (TypeError, ValueError):
            opacity = 1.0
        opacity = max(0.0, min(1.0, opacity))
        if opacity < 1.0:
            alpha = logo.split()[3].point(lambda x: int(x * opacity))
            logo.putalpha(alpha)

        # 位置
        pos = str(vals.get('position', '右下'))
        margin = max(8, int(img.width * 0.02))
        w, h = logo.size
        positions = {
            '左上': (margin, margin),
            '上中': ((img.width - w) // 2, margin),
            '右上': (img.width - w - margin, margin),
            '左中': (margin, (img.height - h) // 2),
            '中': ((img.width - w) // 2, (img.height - h) // 2),
            '右中': (img.width - w - margin, (img.height - h) // 2),
            '左下': (margin, img.height - h - margin),
            '下中': ((img.width - w) // 2, img.height - h - margin),
            '右下': (img.width - w - margin, img.height - h - margin),
        }
        x, y = positions.get(pos, positions['右下'])

        img = img.convert('RGB')
        img.paste(logo, (int(x), int(y)), logo)
        return img

    api.add_watermark_style('image_watermark', '图片水印（插件）', render)
