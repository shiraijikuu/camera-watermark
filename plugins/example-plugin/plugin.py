# -*- coding: utf-8 -*-
"""示例插件：演示插件 API 的 6 种扩展点
1. add_token            —— 新增水印模板变量 {hello}
2. add_camera_name      —— 覆盖某个相机的显示名
3. add_format           —— 新增导出格式 TIFF
4. add_template_preset  —— 新增模板预设（「模板预设」下拉框）
5. add_watermark_style  —— 新增水印样式（完全自定义绘制）
6. on_export            —— 导出前处理钩子（水印后、保存前）
"""
import os
from PIL import Image, ImageDraw, ImageFont
import photo


def register(api):
    # 1) 自定义水印变量：模板里写 {hello} 即可
    api.add_token('hello', lambda meta, settings: '你好，来自插件')

    # 2) 覆盖相机名：把 SONY ILCE-7CM2 显示成"我的索尼相机"
    api.add_camera_name('SONY', 'ILCE-7CM2', '我的索尼相机')

    # 3) 新增导出格式
    def save_tiff(img, target, quality, meta, src_path):
        img.save(target, 'TIFF')
    api.add_format('tiff', '.tiff', 'TIFF（插件示例）', save_tiff)

    # 4) 新增模板预设
    api.add_template_preset('插件预设：日期大图', '{camera}\n{date} {time}\n{make} {model}')

    # 5) 新增水印样式：renderer(img, settings, values) -> 新图像
    def big_bottom_style(img, settings, values):
        draw = ImageDraw.Draw(img, 'RGBA')
        W, H = img.size
        text = photo.render_template('{shutter}  {aperture}  {iso}', values)
        if not text:
            return img
        fs = max(20, int(W * 0.05))
        font = ImageFont.truetype(r'C:\Windows\Fonts\msyhbd.ttc', fs)
        w = draw.textlength(text, font=font)
        x = (W - w) / 2
        y = H - fs * 2
        draw.rounded_rectangle([x - 20, y - 10, x + w + 20, y + fs + 20], radius=12,
                               fill=(0, 0, 0, 150))
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
        return img
    api.add_watermark_style('big_bottom', '大号贴底（插件示例）', big_bottom_style)

    # 6) 导出前处理钩子：可对图像做任意修改（示例为空操作）
    def add_copyright(img, meta, settings):
        return img
    api.on_export(add_copyright)
