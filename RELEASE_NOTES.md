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
