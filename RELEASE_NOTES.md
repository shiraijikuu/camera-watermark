# 📢 Photo Watermark v1.9.0 — Release Notes / 更新公告

**EN:** Update check & plugin store now use a dual-source fallback. jsDelivr's `@main` branch cache can lag behind the latest commit (e.g. the CDN still served an older manifest for a while), which made in-app "Check for Updates" miss new releases. Now, when the configured source is jsDelivr `@main`, the app also queries the GitHub raw authoritative source at runtime and uses whichever is newer — this works immediately for existing users without changing any config. Custom (non-jsDelivr) sources are unaffected.

**中文：** 更新检测与插件商店新增「双源回退」。jsDelivr 的 `@main` 分支缓存可能长时间滞后于最新提交（例如这次 CDN 一直返回旧清单），导致应用内「检查更新」看不到新版本。现在当配置源是 jsDelivr `@main` 时，应用会在运行时额外请求 GitHub raw 权威源并采用较新者——对存量用户即时生效，无需改任何配置。自定义源（非 jsDelivr）不受影响。

## What's New / 新增
- Dual-source fallback for update check / 更新检测双源回退（jsDelivr @main + GitHub raw）
- Dual-source fallback for plugin store / 插件商店双源回退
- Works for existing users without config changes / 存量用户无需改配置即时生效

See CHANGELOG.md / 详见 CHANGELOG.md。
