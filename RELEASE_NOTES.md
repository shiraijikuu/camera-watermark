# 📢 Photo Watermark v1.8.0 — Release Notes / 更新公告

**EN:** New zoom slider in the preview toolbar (25%–400%, continuous) with a live percentage label — it stays in sync with the mouse-wheel and the Fit / 100% / 200% buttons. Fixed a wheel-zoom edge case: for very large photos where Fit is smaller than the 25% minimum, scrolling down no longer zooms back in by mistake — it stays at Fit. Also updated the documented PyInstaller command to bundle the native tkdnd library (tkinterdnd2) so drag & drop works in packaged builds.

**中文：** 预览工具栏新增缩放滑块（25%~400%，连续）+ 实时百分比标签，与滚轮、适应窗口/100%/200% 按钮双向同步。修复滚轮边界问题：超大照片的 fit 比例小于 25% 时，向下滚不再误放大，而是保持「适应窗口」。同时更新了 README 的 PyInstaller 打包命令（补上 --collect-all tkinterdnd2），确保打包版自带 tkdnd 原生库、拖拽可用。

## What's New / What's Fixed
- Zoom slider + percentage label, synced with wheel & buttons / 新增缩放滑块与百分比标签（与滚轮/按钮同步）
- Wheel-zoom fit boundary fix (large photos) / 修复大图 fit 边界（向下滚不再误放大）
- Documented PyInstaller command now bundles tkdnd / 文档打包命令补齐 tkdnd 原生库

See CHANGELOG.md / 详见 CHANGELOG.md。
