# 📢 Photo Watermark v1.4.0 — Release Notes / 更新公告

**EN:** New plugin extension point `api.on_ui_ready(func)` — after the main window is built, plugins receive the `App` instance and can add/change any UI (top banner, buttons on the Export tab, window title, status bar). UI changes take effect after restart; one plugin's error does not block others.

**中文：** 插件系统新增扩展点 `api.on_ui_ready(func)`——主界面构建完成后，插件拿到 App 实例，可以往主界面加/改任意控件（顶部横幅、导出页按钮、窗口标题、状态栏等）。UI 改动需重启生效；单个插件出错不影响其他插件。

## What's New / 新增

- `api.on_ui_ready(func)` — UI-ready hook for plugins / 插件 UI 就绪回调
- Only runs once at startup; UI changes need a restart / 仅启动时调用一次，UI 改动需重启
- Per-hook error isolation + pwm.log / 单插件异常隔离 + 写入 pwm.log
- Example plugin: `plugin-repos/ui-booster/` / 示例插件见 plugin-repos/ui-booster/

See CHANGELOG.md / 详见 CHANGELOG.md。
