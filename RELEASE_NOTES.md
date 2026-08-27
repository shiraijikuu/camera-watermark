# 📢 Photo Watermark v1.9.0 — Release Notes / 更新公告

**EN:** (1) Preview performance: when you zoom in on a large photo beyond the canvas, the app now renders only the visible region (capped to 1.25x canvas) instead of the whole image at full zoom — no more lag or memory spikes. Resize is faster (BOX when shrinking, BILINEAR when enlarging); measured on a 46MP photo: 100% preview 447ms→14ms, 200% 1.8s→11ms. The watermark stays pixel-exact in zoomed previews. (2) Dual-source fallback: update check & plugin store now also query the GitHub raw authoritative source when the jsDelivr `@main` cache lags — works immediately for existing users without changing config.

**中文：** （1）预览性能优化：大图放大到超出画布时只渲染「可见区域」（上限画布 1.25 倍），不再渲染整张放大图，避免卡顿与内存暴涨；缩放算法提速（缩小 BOX、放大 BILINEAR），实测 46MP 照片 100% 预览 447ms→14ms、200% 1.8s→11ms；放大预览中水印按全图坐标定位、位置严格一致。（2）更新检测与插件商店「双源回退」：jsDelivr `@main` 缓存滞后时自动改查 GitHub raw 权威源，对存量用户即时生效、无需改配置。

## What's New / What's Improved
- Capped preview output: render only the visible region when zoomed in / 预览输出尺寸上限（放大只渲染可见区域）
- Faster resize (BOX/BILINEAR) + slider-drag throttling / 缩放算法提速 + 滑块拖动节流
- Pixel-exact watermark in zoomed previews / 放大预览水印位置严格一致
- Dual-source fallback for update check & plugin store / 更新检测与插件商店双源回退

See CHANGELOG.md / 详见 CHANGELOG.md。
