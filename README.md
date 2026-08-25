# Photo Watermark (PWM) — 相机照片水印工具

**EN:** Photo Watermark is a friendly, open-source Windows helper for photographers. Pick a folder of camera photos, and it automatically reads the EXIF and stamps a clean watermark with your camera model, shutter, aperture and ISO. It handles RAW, lets you freely tweak position, size, color and font, exports in a click, supports plugins, and speaks 中文 / English / 繁體中文.

**中文：** 一个给摄影爱好者准备的 Windows 小工具。选中照片文件夹，它自动读出相机参数，帮你把相机型号、快门、光圈、ISO 整整齐齐地印在照片上。支持 RAW，位置、大小、颜色、字体随意调，一键批量导出，还能装插件，界面有中 / 英 / 繁三种语言。

- **Version / 版本：** v1.3.2
- **Author / 作者：** Shiraijikuu (GitHub)
- **AI assistance / AI 协助：** OpenAI Codex
- **License / 许可证：** MIT (LICENSE)

## Features / 特性

**EN**
- Auto-detect camera brand & model (SONY ILCE-7CM2 → "Sony A7C II"), with manual override
- Auto-detect shutter / aperture / ISO / focal length / lens / capture time
- RAW support (ARW/NEF/CR2/DNG…): uses embedded full-size preview, auto-rotates portrait shots
- Watermark position (9-grid + offsets + margin, bottom-aligned by default) / size / color / font / line spacing
- Semi-transparent background bar, text outline, text shadow
- Template presets + saveable custom templates
- Batch export to JPG / PNG / WebP / BMP, EXIF preserved for JPG
- 3 languages: 简体中文 / English / 繁體中文 (switch on the Export tab)
- Custom fonts (fonts/ folder or in-app)
- Plugin system: tokens / camera names / formats / presets / watermark styles / export hooks
- Plugin Manager window (status / add .zip .py / refresh)
- Hot update (configure update_url in config.json)
- Settings auto-saved (config.json)

**中文**
- 自动识别相机品牌型号（SONY ILCE-7CM2 → "Sony A7C II"），可手动覆盖
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

## Quick Start / 快速开始

### Option 1: Run the packaged version (no Python needed) / 方式一：直接运行打包版（无需安装 Python）

Download PhotoWatermark-vX.Y.Z-分发包.zip from Releases, unzip and double-click PhotoWatermark.exe. 从 Releases 下载分发包，解压后双击 PhotoWatermark.exe 即可。

### Option 2: Run from source / 方式二：从源码运行

Requires Python 3.10+. 需要 Python 3.10+：

    pip install -r requirements.txt
    python app.py        # or double-click start.bat / 或双击 start.bat

## Usage / 使用步骤

1. Click "Select Photo Folder" and choose the folder (subfolders are scanned recursively). 点击「选择照片文件夹」，选择照片所在文件夹（递归扫描子文件夹）。
2. Wait for the list to load each photo's info (RAW shows [RAW]). 等待列表读取每张照片参数（RAW 显示 [RAW] 标记）。
3. Click a photo to preview; tweak the watermark on the right (Text / Style / Position / Background). 点击任意照片预览；在右侧「水印文字 / 样式 / 位置 / 背景描边」调整水印。
4. Choose the output folder & format, then click "Export Watermarked Photos". 选择输出文件夹和格式，点击「导出水印照片」。

> Safety / 安全：This app only READS your photos and never modifies or deletes originals; watermarked photos go to the output folder you choose. 本软件只读取原图，绝不修改或删除原图；水印照片全部输出到你选择的输出文件夹。

## Watermark Template Variables / 水印模板变量

| Variable / 变量 | Meaning / 含义 | Example / 示例 |
|------|------|------|
| {make} | Camera brand / 相机厂商 | SONY |
| {model} | Camera model / 相机型号 | ILCE-7CM2 |
| {camera} | Friendly name / override / 友好相机名 / 覆盖名 | Sony A7C II |
| {shutter} | Shutter speed / 快门 | 1/250s |
| {aperture} | Aperture / 光圈 | F5.6 |
| {iso} | ISO / ISO | ISO 100 |
| {focal} | Focal length / 焦距 | 60mm |
| {lens} | Lens / 镜头 | FE 28-60mm F4-5.6 |
| {date} / {time} | Date / Time / 日期 / 时间 | 2026-02-25 / 06:26 |

Default "Camera + Settings" template / 默认「相机 + 参数」模板：{make}  {model}   {focal}  {shutter}  {aperture}  {iso}

## Custom Fonts / 自定义字体

- Put .ttf/.otf/.ttc files into the fonts/ folder (restart to apply). 把 .ttf/.otf/.ttc 字体文件放进 fonts/ 文件夹（重启生效）。
- Or click "Add Font File" on the Style tab (applies immediately). 或「样式」页点「添加字体文件」直接选择（立即生效）。

## Plugin Development / 插件开发

See PLUGINS.md. A plugin is a folder inside plugins/ containing plugin.py with a register(api) function. 6 extension points: 见 PLUGINS.md。插件 = plugins/ 里的一个文件夹，内含 plugin.py，实现 register(api) 即可，共 6 种扩展点：

| API | What it does / 作用 |
|-----|------|
| add_token(name, func) | Add watermark variables / 新增水印模板变量 |
| add_camera_name(make, model, friendly) | Override camera name / 覆盖相机显示名 |
| add_format(name, ext, label, save_func) | Add export formats / 新增导出格式 |
| add_template_preset(name, template) | Add template presets / 新增模板预设 |
| add_watermark_style(name, label, renderer) | Custom watermark styles / 自定义水印样式 |
| on_export(func) | Pre-save hook / 导出前处理钩子 |

The Plugin Manager window (Export tab) shows load status and lets you add (.zip/.py) or refresh. 「导出」页的「插件管理」窗口可查看加载状态 / 添加(.zip/.py) / 刷新。

> 🔒 **Security / 安全：** plugin_store_url / install_url only accept **HTTPS** (plugins are executed locally as Python code; plain HTTP allows code injection). Plugin archives are validated against Zip Slip (path traversal) on install. 插件商店地址仅支持 **HTTPS**（插件是本地执行的 Python 代码，HTTP 可被中间人注入代码）；安装时会校验压缩包路径，拒绝路径穿越（Zip Slip）。

## Hot Update / 热更新

Set update_url in config.json (JSON manifest URL), click "Check for Updates" to compare versions, download and auto-replace. The manifest supports an optional `checksum` (SHA-256 of the exe) so same-version rebuilds are also detected. 在 config.json 设置 update_url（更新清单 JSON 地址），点「检查更新」→ 比对版本 → 下载 → 自动替换并重启。清单支持可选 `checksum`（exe 的 SHA-256），同版本号重新发布也能检测到更新。

## Build from Source / 从源码打包 exe

    pip install -r requirements-dev.txt
    pyinstaller --noconfirm --clean --onefile --windowed --name "PhotoWatermark" --hidden-import "PIL._tkinter_finder" app.py

Put plugins/, fonts/ and USAGE.txt next to the exe in dist/ to distribute. 把 plugins/、fonts/、USAGE.txt 等放在 dist/ 的 exe 旁边即可分发。

## Tests / 测试

    python -m unittest test_photo -v

## Versioning (SemVer) / 版本规范

Strict semantic versioning x.y.z / 严格按照语义化版本 x.y.z 管理：
- Major X: breaking changes / 主版本 X：破坏性变更，不兼容旧版本
- Minor Y: new features, backward compatible / 次版本 Y：新增功能，向下兼容
- Patch Z: bug fixes only / 修订版本 Z：只修 bug / 安全修复，无新功能

See CHANGELOG.md; releases live in releases/vX.Y.Z/. 版本历史见 CHANGELOG.md；发布包按版本放在 releases/vX.Y.Z/ 目录。

## Release Notes / 更新公告（v1.3.2）

**EN: Plugin Store update detection + security fixes.** The store compares the catalog version AND a content checksum (SHA-256) against your installed plugin — an **Update** button appears for one-click upgrade, even when the version number is unchanged. This build also fixes a **Zip Slip (path traversal)** issue on plugin install and requires **HTTPS** for the plugin store/download URLs.

**中文：插件商店更新检测 + 安全修复。** 商店会比对目录版本号 + 内容校验和（SHA-256）与本地已装插件，任一不同即显示「更新」按钮一键升级（即使版本号没变也能检测到）。本版同时修复插件安装的 **Zip Slip（路径穿越）** 漏洞，并强制插件商店/下载地址使用 **HTTPS**。

- Plugin Store: version + checksum update detection / 插件商店：版本号 + 校验和双重更新检测
- App auto-update: version + checksum detection (same-version rebuilds detected) / 主程序热更新：版本号 + 校验和检测（同版本号重新发布也能收到更新）
- Security: Zip Slip fix on plugin install / 安全：修复插件安装 Zip Slip 路径穿越
- Security: HTTPS-only plugin store & download / 安全：插件商店与下载仅支持 HTTPS
- Install record: plugins/.installed.json / 安装记录：plugins/.installed.json

> 🔒 **Security / 安全：** plugin_store_url / install_url only accept **HTTPS** (plugins are executed locally as Python code; plain HTTP allows code injection). Plugin archives are validated against Zip Slip (path traversal) on install. 插件商店地址仅支持 **HTTPS**（插件是本地执行的 Python 代码，HTTP 可被中间人注入代码）；安装时会校验压缩包路径，拒绝路径穿越（Zip Slip）。

> ⚠️ **v1.2.0 / v1.3.0 users: please manually download v1.3.2 once** — the old auto-updater cannot upgrade to this version; after installing v1.3.2, auto-update works again.
> ⚠️ **v1.2.0 / v1.3.0 用户：请手动下载 v1.3.2 一次** — 旧版自动更新无法升级到本版；安装 v1.3.2 后自动更新恢复正常。

详见 / See CHANGELOG.md。

