# 📢 Photo Watermark v1.7.2 — Release Notes / 更新公告

**EN:** This is a bug-fix release. (1) Fixed photo-folder drag & drop: the previous windnd backend crashed on 64-bit Python, so dragging did nothing — now it uses tkinterdnd2 (bundles the native tkdnd library, stable on 64-bit); if drag is unavailable, the empty-state hint no longer misleadingly says "drop a folder". (2) Mouse-wheel zoom: you can now scroll back down to "Fit Window" from the minimum zoom (no longer stuck), zoom is centered on the mouse cursor (the image no longer jumps back to the middle), and stepping away from Fit is smoother (nearest 0.25x step instead of jumping straight to 100%).

**中文：** 本次为修复版。（1）修复拖拽照片文件夹失效：之前的 windnd 在 64 位 Python 下回调访问冲突导致拖放无反应，现改用 tkinterdnd2（自带 tkdnd 原生库，64 位稳定）；拖拽不可用时，空状态引导不再误导性提示"拖进来"。（2）滚轮缩放：最小档再往下滚可回到"适应窗口"（不再卡死）；缩放以鼠标为中心（画面不再跳回中间）；离开 fit 时更平滑（就近 0.25 档，不再从 0.3 直接蹦到 100%）。

## What's Fixed / 修复内容
- Drag & drop photo folder now works (tkinterdnd2, 64-bit stable) / 拖拽照片文件夹可用（tkinterdnd2，64 位稳定）
- Wheel zoom can return to Fit Window / 滚轮缩放可回到「适应窗口」
- Mouse-centered zoom (no jump to center) / 以鼠标为中心的缩放（不再跳回画面中心）
- Smoother fit -> zoom transition / fit 到放大的过渡更平滑
- Theme plugin no longer hides gallery preset selection highlight on first open / 主题插件不再覆盖预设缩略图选中高亮

See CHANGELOG.md / 详见 CHANGELOG.md。
