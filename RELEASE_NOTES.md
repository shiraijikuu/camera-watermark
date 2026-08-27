# 📢 Photo Watermark v1.9.0 — Release Notes / 更新公告

**EN:** (1) Preview performance: when zoomed in beyond the canvas, the app now renders only the visible region (capped to 1.25x canvas) — no more lag or memory spikes; faster resize (BOX/BILINEAR); measured on a 46MP photo: 100% preview 447ms→14ms, 200% 1.8s→11ms; watermark stays pixel-exact in zoomed previews. (2) Fixed reversed drag in zoomed preview — the image now follows the cursor. (3) Dual-source fallback: update check & plugin store also query the GitHub raw source when the jsDelivr `@main` cache lags.

**中文：** （1）预览性能优化：大图放大到超出画布时只渲染「可见区域」（上限画布 1.25 倍），不再渲染整张放大图，避免卡顿与内存暴涨；缩放算法提速，实测 46MP 照片 100% 预览 447ms→14ms、200% 1.8s→11ms；放大预览中水印位置严格一致。（2）修复放大预览拖拽反向跳动，画面跟随鼠标。（3）更新检测与插件商店「双源回退」：jsDelivr `@main` 缓存滞后时自动改查 GitHub raw 权威源，对存量用户即时生效、无需改配置。

## What's New / What's Improved
- Capped preview output (visible region only when zoomed) / 预览输出尺寸上限
- Faster resize (BOX/BILINEAR) + slider-drag throttling / 缩放算法提速 + 滑块拖动节流
- Pixel-exact watermark in zoomed previews / 放大预览水印位置严格一致
- Fix reversed drag in zoomed preview / 修复放大预览拖拽反向
- Dual-source fallback for update check & plugin store / 更新检测与插件商店双源回退

See CHANGELOG.md / 详见 CHANGELOG.md。
