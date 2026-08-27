# 📢 Photo Watermark v1.6.0 — Release Notes / 更新公告

**EN:** Fixed "Failed to start embedded python interpreter!" when switching language (PyInstaller env vars now cleared before relaunch). New plugin extension point `api.on_window_created(func)` — dynamic windows (plugin settings / manager / store) are handed to plugins after creation, so themes adapt new windows automatically.

**中文：** 修复切换语言时重启报错 "Failed to start embedded python interpreter!"（重启前已清除 PyInstaller 环境变量）。新增插件扩展点 `api.on_window_created(func)`——动态窗口（插件设置/管理/商店）创建完成后交给插件，主题可自动适配新窗口。

## What's Fixed / What's New
- Fix language-switch relaunch crash / 修复语言切换重启崩溃
- New plugin extension point: on_window_created / 新增插件扩展点 on_window_created

See CHANGELOG.md / 详见 CHANGELOG.md。
