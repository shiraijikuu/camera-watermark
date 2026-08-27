> **Note / 说明：** A plugin watermark style is drawn **on top of** the text watermark,
> so text and image watermarks can coexist. If you only want the plugin style,
> leave the text template empty. 插件水印样式会**叠加在文字水印之上**（文字+图片可同时显示）；
> 若只想用插件样式，把文字模板清空即可。

> **Note / 说明：** Plugins are maintained in **separate repositories** (see plugins/README.md).
> This document describes the plugin API. 插件在**独立仓库**中单独维护（见 plugins/README.md），本文档介绍插件 API。

# 相机照片水印工具 - 插件开发指南

插件可以让其他人（或你自己）给软件添加新功能，**不需要改软件本身**。

## 插件是什么

- 插件是一个文件夹，放在 `plugins` 目录下（软件启动时自动加载）。
- 文件夹里必须有一个 `plugin.py`，里面实现一个 `register(api)` 函数。
- 加载失败不会影响软件运行（会打印错误日志）。

```
plugins/
└── 我的插件/
    └── plugin.py
```

## 最简单的插件

```python
# plugins/我的插件/plugin.py
def register(api):
    api.add_token('hello', lambda meta, settings: '你好，世界！')
```

保存后启动软件，在水印模板里写 `{hello}` 就能显示"你好，世界！"。

## API 一览

### 1. 自定义水印变量 `api.add_token(name, func)`

`func(meta, settings)` 返回字符串，出现在模板变量 `{name}` 中。

- `meta`：当前照片的元数据字典，常用字段：
  `make`(厂商) `model`(型号) `camera_text`(识别出的相机名) `shutter_text` `aperture_text`
  `iso_text` `focal_text` `lens_text` `date_text` `time_text` `width` `height` `raw`(是否RAW)
- `settings`：当前所有水印设置（字典）。

```python
def register(api):
    def my_shutter(meta, settings):
        return '快门: ' + meta.get('shutter_text', '')
    api.add_token('shutter_cn', my_shutter)
```

### 2. 覆盖相机名 `api.add_camera_name(make, model, friendly)`

把指定厂商+型号的相机显示成自定义名字。

```python
def register(api):
    api.add_camera_name('SONY', 'ILCE-7CM2', '我的索尼 A7C2')
```

### 3. 新增导出格式 `api.add_format(name, ext, label, save_func)`

`save_func(img, target_path, quality, meta, src_path)` 负责把画好水印的 PIL
图像保存到目标路径。

```python
from PIL import Image

def register(api):
    def save_tiff(img, target, quality, meta, src_path):
        img.save(target, 'TIFF')
    api.add_format('tiff', '.tiff', 'TIFF', save_tiff)
```

### 4. 预留：`api.settings_extra`（未来扩展 UI 设置项用）


### 4. 新增模板预设 `api.add_template_preset(name, template)`

给「模板预设」下拉框添加一个预设项。

```python
def register(api):
    api.add_template_preset('日期大图', '{camera}\n{date} {time}\n{make} {model}')
```

### 5. 自定义水印样式 `api.add_watermark_style(name, label, renderer)`

完全自定义水印的绘制方式。`renderer(img, settings, values)` 接收 PIL 图像，
返回绘制后的图像（可直接修改 img 并返回）。

```python
from PIL import ImageDraw, ImageFont
import photo

def register(api):
    def my_style(img, settings, values):
        draw = ImageDraw.Draw(img, 'RGBA')
        W, H = img.size
        text = photo.render_template('{shutter} {aperture} {iso}', values)
        font = ImageFont.truetype(r'C:\Windows\Fonts\msyhbd.ttc', int(W * 0.05))
        w = draw.textlength(text, font=font)
        draw.text(((W - w) / 2, H - int(W * 0.1)), text, font=font, fill=(255, 255, 255, 255))
        return img
    api.add_watermark_style('big', '大号（示例）', my_style)
```

启用后，在「样式」页的「水印样式」下拉框选择即可（可在 config.json 的 `style` 里固定）。

### 6. 导出前处理钩子 `api.on_export(func)`

水印绘制完成后、保存之前调用 `func(img, meta, settings)`，可对图像做任意修改
（例如加版权水印、统一调色），返回修改后的图像（返回 None 表示不改）。

```python
def register(api):
    def add_copyright(img, meta, settings):
        # 示例：右下角加一行小字
        return img
    api.on_export(add_copyright)
```

### 7. 预留：`api.settings_extra`（未来扩展 UI 设置项用）


### 8. 插件设置项 `api.add_setting(key, label, kind, default, options)`

插件可以注册设置项，在「导出」页 ->「插件设置」窗口里调整，自动保存到 config.json，
渲染时通过 `settings['plugin_values'][插件名][key]` 读取。

- `kind`：`text` / `file`（文件选择）/ `number` / `select`（下拉）/ `bool`（勾选）/ `range`（滑块，需传 min/max/step）
- `options`：select 时的选项列表

```python
def register(api):
    api.add_setting('image', '水印图片', 'file', '')
    api.add_setting('size', '大小 %', 'number', 15)
    api.add_setting('pos', '位置', 'select', '右下',
                    options=['左上', '上中', '右上', '左中', '中', '右中', '左下', '下中', '右下'])

    def render(img, settings, values):
        vals = settings['plugin_values']['my-plugin']
        path = vals.get('image', '')
        # ... 用 path / size / pos 绘制
        return img
    api.add_watermark_style('my_style', '我的样式', render)
```

> 插件内可通过 `values['raw']` 判断当前照片是否为 RAW（可据此跳过，避免处理过慢）。

### 9. 主界面就绪回调 `api.on_ui_ready(func)`（需主程序 ≥ 1.4.0）

主程序主界面构建完成后，把 `App` 实例交给回调 `func(app)`，插件可以**向主界面添加/修改任意控件**
（顶部横幅、导出页按钮、改窗口标题、操作状态栏等）。

- 只在启动时调用一次，**UI 改动需重启软件生效**
- 回调内请用 `try/except` 防护：主程序以后改结构时，插件降级而不是崩溃
- 单个插件异常不会阻断其他插件

```python
def register(api):
    def init_ui(app):
        import tkinter as tk
        from tkinter import ttk
        try:
            banner = tk.Label(app.root, text='★ UI 插件已生效 ★', bg='#1e293b', fg='#facc15', pady=4)
            banner.pack(side='top', fill='x')
        except Exception as e:
            print('[my-plugin] banner:', e)
    api.on_ui_ready(init_ui)
```

> 实战示例：**theme-switcher** 插件（主题切换：黑夜 / 白天 / 跟随系统）已发布为独立插件仓库
> [PhotoWatermark-theme-switcher](https://github.com/shiraijikuu/PhotoWatermark-theme-switcher)，可在插件商店安装。

## 全部 API 一览

| 方法 | 作用 |
|------|------|
| add_token(name, func) | 新增水印模板变量 {name} |
| add_camera_name(make, model, friendly) | 覆盖相机显示名 |
| add_format(name, ext, label, save_func) | 新增导出格式 |
| add_template_preset(name, template) | 新增模板预设 |
| add_watermark_style(name, label, renderer) | 新增自定义水印样式 |
| on_export(func) | 导出前处理钩子 |
| on_ui_ready(func) | 主界面构建完成后回调（可向界面加控件，需重启生效） |
| on_ui_ready(func) | 主界面构建完成后回调（可向界面加控件，需重启生效） |
| add_setting(key, label, kind, default, options) | 新增插件设置项（插件设置窗口） |

## 全部 API 一览

| 方法 | 作用 |
|------|------|
| add_token(name, func) | 新增水印模板变量 {name} |
| add_camera_name(make, model, friendly) | 覆盖相机显示名 |
| add_format(name, ext, label, save_func) | 新增导出格式 |
| add_template_preset(name, template) | 新增模板预设 |
| add_watermark_style(name, label, renderer) | 新增自定义水印样式 |
| on_export(func) | 导出前处理钩子 |
| on_ui_ready(func) | 主界面构建完成后回调（可向界面加控件，需重启生效） |

## 调试

- 插件里的 `print()` 会输出到控制台（用 `start-debug.bat` 启动能看到）。
- 插件加载失败时，状态栏和日志会显示"插件加载失败 [名字]: 原因"。

## 注意事项

- 插件运行在软件进程内：**请只处理图片/文字数据，不要做危险操作**。
- 不要修改 `plugins` 以外的文件。
- **插件商店地址（plugin_store_url / install_url）只支持 HTTPS**：插件是本地执行的 Python 代码，
  用明文 HTTP 会允许中间人注入任意代码。请始终使用 `https://`。
- 安装时会校验压缩包内文件路径，**拒绝路径穿越（Zip Slip）**，恶意包无法把文件写到 `plugins/` 之外。
