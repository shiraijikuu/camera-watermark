# 📢 Photo Watermark v1.3.1 — Release Notes / 更新公告

**EN:** This is a hot-fix release. Auto-update was failing with "Security validation failure: parent process has different executable" when replacing the app. The auto-updater is now fixed and verified end-to-end (v1.3.1 and later update correctly). ⚠️ Because the updater inside v1.2.0 / v1.3.0 is broken, those users must download v1.3.1 manually once — see the notice below.

**中文：** 本次为热修复版本。此前自动更新在替换程序时报错（Security validation failure: parent process has different executable）。现已修复并端到端验证通过（v1.3.1 及之后版本可正常自动更新）。⚠️ 由于 v1.2.0 / v1.3.0 内置的更新逻辑本身有缺陷，这些版本的用户需手动下载 v1.3.1 一次——详见下方提示。

## What's Fixed / 修复内容

- Fixed auto-update failure: clear PyInstaller runtime env vars (_PYI_*) before launching the new app, so it is no longer mistaken for a child process / 修复自动更新失败：更新时清除 PyInstaller 运行时环境变量（_PYI_*），新程序不再被误判为子进程
- Added update_error.log for easier troubleshooting / 新增更新错误日志 update_error.log，方便排查
- Rebuilt the release binary (the v1.3.0 package binary was accidentally identical to v1.2.0) / 重新打包发布版（修正 v1.3.0 包内程序与 v1.2.0 相同的问题）

## ⚠️ Important for v1.2.0 / v1.3.0 users / 重要提示（v1.2.0 / v1.3.0 用户）

The auto-updater inside v1.2.0 / v1.3.0 has a bug and **cannot auto-upgrade to this version**.
Please **manually download v1.3.1** (portable zip or exe) once. After installing v1.3.1, auto-update works normally again.

v1.2.0 / v1.3.0 自带的自动更新逻辑存在缺陷，**无法自动升级到本版**。请**手动下载 v1.3.1**（分发包或 exe）一次；安装 v1.3.1 后自动更新恢复正常。

See CHANGELOG.md / 详见 CHANGELOG.md。

---
# 📢 Photo Watermark v1.3.0 — Release Notes / 更新公告

**EN:** Now with a built-in **Plugin Store**! Browse and install plugins with one click inside the app.
**中文：** 新增内置**插件商店**！在软件里就能浏览并一键安装插件。

## What's New / 新增

- Plugin Store window: browse catalog, one-click install, auto-refresh / 插件商店：浏览目录、一键安装、自动刷新
- plugins.json catalog + pwm-plugin discovery tag / 插件目录 + 统一发现标签

See CHANGELOG.md / 详见 CHANGELOG.md。

---
---

# 📢 Photo Watermark v1.2.0 — Release Notes / 更新公告

**EN:** Big update! Plugin Settings window with live preview, thumbnail gallery for preset watermarks, text + image watermarks together, and font improvements.
**中文：** 大版本更新！新增插件设置窗口（实时预览）、预设水印缩略图画廊、文字+图片水印同屏，以及字体改进。

## What's New / 新增

- Plugin Settings window + live preview / 插件设置窗口 + 实时预览
- Thumbnail gallery to pick preset watermarks / 预设水印缩略图画廊
- Text + image watermarks can coexist / 文字水印 + 图片水印同时存在
- Image watermark plugin: 10 built-in GIF presets, custom PNG/JPG/GIF / 图片水印插件：10 张预设 + 自定义
- Font scan improvements (subfolders, refresh, fallback) / 字体扫描改进
- Plugin versions shown in Plugin Manager / 插件管理显示版本号

See CHANGELOG.md / 详见 CHANGELOG.md。

---
# 📢 Photo Watermark v1.1.0 — Release Notes / 更新公告

Thank you for using Photo Watermark! This update focuses on making the **plugin system more powerful**, so developers can extend the app in more ways. 感谢使用 Photo Watermark！本次更新重点是**增强插件系统的可扩展性**，让开发者可以做更多事情。

---

## ✨ What's New / 本次更新

### 1. Extended Plugin API (core) / 插件 API 扩展（核心）

Plugins now support **6 extension points** / 插件现在支持 **6 种扩展点**：

| API | What it does / 作用 |
|-----|------|
| add_token(name, func) | Add watermark template variables / 新增水印模板变量 |
| add_camera_name(make, model, friendly) | Override camera display name / 覆盖相机显示名 |
| add_format(name, ext, label, save_func) | Add export formats / 新增导出格式 |
| **add_template_preset(name, template)** 🆕 | Add template presets / 新增模板预设 |
| **add_watermark_style(name, label, renderer)** 🆕 | Custom watermark rendering styles / 自定义水印渲染样式 |
| **on_export(func)** 🆕 | Pre-save processing hook / 导出前处理钩子 |

### 2. UI / 界面

- New "Watermark Style" dropdown on the Style tab (default + plugin styles).
  「样式」页新增「水印样式」下拉框（默认样式 + 插件样式）。

### 3. Example Plugin Updated / 示例插件更新

- The bundled example plugin now demonstrates all 6 extension points. 内置示例插件已演示全部 6 种扩展点。

### 4. Stability / 稳定性

- Fixed several known issues. 修复若干已知问题。

---

## 📥 Download / 下载

- **Portable (no Python needed, unzip & run) / 分发包（解压即用，无需安装 Python）**: PhotoWatermark-v1.1.0-分发包.zip
- **Open Source (full source) / 开源版（含完整源码）**: PhotoWatermark-v1.1.0-开源版.zip

> Unzip and double-click PhotoWatermark.exe. 解压后双击 PhotoWatermark.exe 即可使用。

## 📝 Changelog / 更新日志

See CHANGELOG.md for details. 完整更新日志见 CHANGELOG.md。

## 🙏 Credits / 致谢

- Author / 作者：**Shiraijikuu**
- AI assistance / AI 协助：**OpenAI Codex**
- License / 许可证：MIT

Welcome to submit Issues / PRs / plugins! 欢迎提交 Issue / PR / 插件！
