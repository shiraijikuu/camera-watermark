# 更新日志 (Changelog)

本项目严格遵循 [语义化版本 SemVer](https://semver.org/lang/zh-CN/)：

- **主版本 X**：破坏性变更，不兼容旧版本（API/架构/配置不兼容）。
- **次版本 Y**：新增功能，向下兼容。
- **修订版本 Z**：只修 bug / 安全修复，无新功能，完全兼容。

---

## [1.1.0] - 2026-08-25（当前）

### 新增
- 插件 API 扩展（更强的可扩展性）：
  - `api.add_template_preset(name, template)` —— 插件可新增模板预设
  - `api.add_watermark_style(name, label, renderer)` —— 插件可自定义水印渲染样式
  - `api.on_export(func)` —— 导出前处理钩子（水印后、保存前可修改图像）
- 「样式」页新增「水印样式」下拉框（默认样式 + 插件样式）
- 示例插件更新：演示全部 6 种插件扩展点

---

## [1.0.0] - 2026-08-25（首个正式发布）
 - 2026-08-25（首个正式发布）

首个公开版本，包含以下全部功能：

### 功能
- 自动识别相机品牌型号（SONY ILCE-7CM2 → Sony A7C II，可手动覆盖）
- 自动检测快门 / 光圈 / ISO / 焦距 / 镜头 / 拍摄时间
- 支持 RAW（ARW/NEF/CR2/DNG 等，内嵌全尺寸预览，竖拍自动转正）
- 水印位置（九宫格 + 偏移 + 边距，默认贴底）/ 字号 / 颜色 / 字体 / 背景条 / 描边 / 阴影
- 模板预设 + 自定义模板（可保存），变量 {make} {model} {shutter} {aperture} {iso} 等
- 批量导出 JPG / PNG / WebP / BMP，JPG 可保留 EXIF
- 三种语言：简体中文 / English / 繁體中文（「导出」页一键切换）
- 自定义字体（fonts/ 文件夹或界面添加）
- 插件系统 + 插件管理窗口（自定义变量 / 相机名 / 导出格式）
- 热更新检查（config.json 配置 update_url）
- 设置自动保存（config.json）

### 其他
- 窗口标题显示版本号（Photo Watermark v1.0.0）
- 开源发布（MIT 许可证；作者 Shiraijikuu · AI 协助 OpenAI Codex）
