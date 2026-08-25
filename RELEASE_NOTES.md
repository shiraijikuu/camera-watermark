# 📢 Photo Watermark v1.3.3 — Release Notes / 更新公告

**EN:** Plugin Store robustness & security fixes. Install now verifies the downloaded zip against the catalog checksum; plugins that fail to load show a red "Failed to Load" state with a one-click **Update/Reinstall**; overwrite install is now atomic (old version auto-restored on failure); zip-bomb size/count limits; double-click install guard.

**中文：** 插件商店健壮性与安全修复。安装现在会校验下载的 zip 是否与目录 checksum 一致；加载失败的插件显示红色「加载失败」并可一键「更新/重装」；覆盖安装改为原子操作（失败自动恢复旧版）；新增 zip 炸弹大小/数量防护；防止重复点击安装。

## What's Fixed / 修复内容

- Verify downloaded plugin zip against catalog checksum (reject mismatch; warn when checksum missing) / 下载插件 zip 按目录 checksum 校验（不一致拒绝；缺失时提示）
- Load-failed plugins: red "Failed to Load" + one-click Update/Reinstall / 加载失败插件：红色「加载失败」+ 一键更新/重装
- Atomic overwrite install with auto-restore on failure / 覆盖安装原子化，失败自动恢复
- Zip-bomb protection (300 MB total / 2000 files) / zip 炸弹防护（总量 300MB / 2000 文件）
- Prevent concurrent installs from double-click / 防止重复点击安装并发冲突

See CHANGELOG.md / 详见 CHANGELOG.md。

---
# 📢 Photo Watermark v1.3.2 — Release Notes / 更新公告

**EN:** Plugin Store now detects updates! When a plugin has a newer version in the store — or its published content changed (checksum) even if the version number is unchanged — the store shows an **Update** button for one-click upgrade. Plugin cards also show the last-updated date.

**中文：** 插件商店现在支持「更新检测」！商店里插件有新版本、或发布内容有变化（校验和不同，即使版本号不变）时，会显示「更新」按钮，一键覆盖升级；插件卡片还会显示更新时间。

## What's New / 新增

- Plugin Store update detection: version comparison + checksum (SHA-256) / 插件商店更新检测：版本号比对 + 校验和（SHA-256）比对
- "Update" button for one-click upgrade (reuses the overwrite-style installer) / 「更新」按钮一键升级（复用现有覆盖式安装）
- Show plugin last-updated date / 显示插件更新时间
- Install record saved to `plugins/.installed.json` / 安装记录保存到 `plugins/.installed.json`
- Full 中文 / English / 繁體中文 translations for the store UI / 商店界面补齐中英繁翻译

## Security Fixes / 安全修复

- **Zip Slip (path traversal) fix** on plugin install (store + manual add) — archives are validated before extraction / 修复插件安装 Zip Slip 路径穿越（商店安装 + 手动添加），解压前校验路径
- **HTTPS-only** for plugin_store_url / install_url / 插件商店与下载地址仅支持 HTTPS
- Checksum comparison is now case-insensitive / 校验和比对忽略大小写
- Version comparison supports `v` prefix / 版本号比较支持 v 前缀
- **App auto-update also uses checksum** (update.json `checksum`) — same-version rebuilds are detected / 主程序热更新同样支持校验和检测（update.json 的 checksum）——同版本号重新发布也能被检测到
- Downloaded update is verified against the manifest checksum before applying / 下载的更新文件会按清单 checksum 校验后再应用

See CHANGELOG.md / 详见 CHANGELOG.md。

---
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
