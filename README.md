# Photo Watermark (PWM) — 相机照片水印工具

**EN:** Photo Watermark is a friendly, open-source Windows helper for photographers.
Pick a folder of camera photos, and it automatically reads the EXIF and stamps a
clean watermark with your camera model, shutter, aperture and ISO. It handles RAW,
lets you freely tweak position, size, color and font, exports in a click, supports
plugins, and speaks 中文 / English / 繁體中文.

**中文：** 一个给摄影爱好者准备的 Windows 小工具。选中照片文件夹，它自动读出相机
参数，帮你把相机型号、快门、光圈、ISO 整整齐齐地印在照片上。支持 RAW，位置、
大小、颜色、字体随意调，一键批量导出，还能装插件，界面有中 / 英 / 繁三种语言。

- **当前版本：** v1.1.0
- **作者：** Shiraijikuu (GitHub)
- **AI 协助：** OpenAI Codex
- **许可证：** MIT (LICENSE)

## 特性

- 自动识别相机品牌型号（SONY ILCE-7CM2 -> "Sony A7C II"），可手动覆盖
- 自动检测快门 / 光圈 / ISO / 焦距 / 镜头 / 拍摄时间
- 支持 RAW（ARW/NEF/CR2/DNG 等，内嵌全尺寸预览，竖拍自动转正）
- 水印位置（九宫格 + 横/纵偏移 + 边距，默认贴底）/ 字号 / 颜色 / 字体 / 行距
- 半透明背景条、文字描边、文字阴影
- 模板预设 + 自定义模板（可保存）
- 批量导出 JPG / PNG / WebP / BMP，JPG 可保留 EXIF
- 三种语言：简体中文 / English / 繁體中文（「导出」页一键切换）
- 自定义字体（fonts/ 文件夹或界面添加）
- 插件系统：自定义变量 / 相机名 / 导出格式 / 模板预设 / 水印样式 / 导出钩子
- 插件管理窗口（查看状态 / 添加 .zip .py / 刷新）
- 热更新（config.json 配置 update_url）
- 设置自动保存（config.json）

## 快速开始

### 方式一：直接运行打包版（无需安装 Python）

下载 Releases 里的 PhotoWatermark-vX.Y.Z-分发包.zip，解压后双击 PhotoWatermark.exe 即可。

### 方式二：从源码运行

需要 Python 3.10+：

    pip install -r requirements.txt
    python app.py        # 或双击 start.bat

## 使用步骤

1. 点击「选择照片文件夹」，选择照片所在文件夹（递归扫描子文件夹）。
2. 等待列表读取每张照片参数（RAW 显示 [RAW] 标记）。
3. 点击任意照片预览；在右侧「水印文字 / 样式 / 位置 / 背景描边」调整水印。
4. 选择输出文件夹和格式，点击「导出水印照片」。

> 安全：本软件只读取原图，绝不修改或删除原图；水印照片全部输出到你选择的输出文件夹。

## 水印模板变量

| 变量 | 含义 | 示例 |
|------|------|------|
| {make} | 相机厂商 | SONY |
| {model} | 相机型号 | ILCE-7CM2 |
| {camera} | 友好相机名 / 手动覆盖名 | Sony A7C II |
| {shutter} | 快门 | 1/250s |
| {aperture} | 光圈 | F5.6 |
| {iso} | ISO | ISO 100 |
| {focal} | 焦距 | 60mm |
| {lens} | 镜头 | FE 28-60mm F4-5.6 |
| {date} / {time} | 拍摄日期 / 时间 | 2026-02-25 / 06:26 |

默认「相机 + 参数」模板：{make}  {model}   {focal}  {shutter}  {aperture}  {iso}

## 自定义字体

- 把 .ttf/.otf/.ttc 字体文件放进 fonts/ 文件夹（重启生效）；
- 或「样式」页点「添加字体文件」直接选择（立即生效）。

## 插件开发

见 PLUGINS.md。插件 = plugins/ 里的一个文件夹，内含 plugin.py，实现 register(api) 即可，共 6 种扩展点：

| API | 作用 |
|-----|------|
| add_token(name, func) | 新增水印模板变量 {name} |
| add_camera_name(make, model, friendly) | 覆盖相机显示名 |
| add_format(name, ext, label, save_func) | 新增导出格式 |
| add_template_preset(name, template) | 新增模板预设 |
| add_watermark_style(name, label, renderer) | 自定义水印渲染样式 |
| on_export(func) | 导出前处理钩子 |

「导出」页的「插件管理」窗口可查看加载状态 / 添加(.zip/.py) / 刷新。

## 热更新

在 config.json 设置 update_url（更新清单 JSON 地址），点「检查更新」→ 比对版本 → 下载 → 自动替换并重启。

## 从源码打包 exe

    pip install -r requirements-dev.txt
    pyinstaller --noconfirm --clean --onefile --windowed --name "PhotoWatermark" --hidden-import "PIL._tkinter_finder" app.py

产物在 dist/，把 plugins/、fonts/、使用说明.txt 等放在 exe 旁边即可分发。

## 测试

    python -m unittest test_photo -v

## 版本规范（SemVer）

严格按照语义化版本 x.y.z 管理：

- 主版本 X：破坏性变更，不兼容旧版本（API / 架构 / 配置不兼容）
- 次版本 Y：新增功能，向下兼容
- 修订版本 Z：只修 bug / 安全修复，无新功能

版本历史见 CHANGELOG.md；发布包按版本放在 releases/vX.Y.Z/ 目录。

## Release Notes / 更新公告（v1.1.0）

**EN: Extended plugin API (more extensible)**
- Plugins can now add template presets, custom watermark rendering styles, and pre-save processing hooks
- New "Watermark Style" dropdown on the Style tab
- Example plugin updated to demonstrate all 6 extension points
- Several stability fixes

**中文：新增插件 API（更强的可扩展性）**
- 插件现在可以新增模板预设、自定义水印渲染样式、注册导出前处理钩子
- 「样式」页新增「水印样式」下拉框
- 示例插件更新：演示全部 6 种插件扩展点
- 修复若干稳定性问题

详见 / See CHANGELOG.md。

## 致谢

- 作者：**Shiraijikuu**
- AI 编程协助：**OpenAI Codex**
- 基于 Python + Tkinter + Pillow + piexif 构建

## 许可证

MIT (LICENSE) © 2026 Shiraijikuu and OpenAI Codex
