# -*- coding: utf-8 -*-
"""make_version_info.py — 从 app.py 的 APP_VERSION 生成 PyInstaller 版本资源 version_info.txt。

用途：给打包 exe 嵌入公司/产品/版本/描述/版权等元数据，显著降低杀毒软件对
"无签名、无元数据" PyInstaller 单文件程序的启发式误报。
"""
import io
import os
import re

APP_PY = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.py')
src = io.open(APP_PY, encoding='utf-8').read()
m = re.search(r"APP_VERSION\s*=\s*'([^']+)'", src)
if not m:
    raise SystemExit('app.py 中找不到 APP_VERSION')
version = m.group(1)
parts = [int(x) for x in version.split('.')]
while len(parts) < 4:
    parts.append(0)
fvers = tuple(parts[:4])

content = """VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=%s,
    prodvers=%s,
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'Shiraijikuu'),
         StringStruct(u'FileDescription', u'Photo Watermark (PWM) - camera photo watermark tool / 相机照片水印工具'),
         StringStruct(u'FileVersion', u'%s'),
         StringStruct(u'InternalName', u'PhotoWatermark'),
         StringStruct(u'LegalCopyright', u'Copyright (c) 2026 Shiraijikuu, MIT License'),
         StringStruct(u'OriginalFilename', u'PhotoWatermark.exe'),
         StringStruct(u'ProductName', u'Photo Watermark'),
         StringStruct(u'ProductVersion', u'%s')])
    ]),
    VarFileInfo([VarStruct(u'Translation', [2052, 1200])])
  ]
)
""" % (fvers, fvers, version, version)

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'version_info.txt')
io.open(out, 'w', encoding='utf-8', newline='').write(content)
print('version_info.txt written for version', version)
