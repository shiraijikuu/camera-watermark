# 更新日志 (Changelog)

本项目严格遵循 [语义化版本 SemVer](https://semver.org/lang/zh-CN/)：

- **主版本 X**：破坏性变更，不兼容旧版本（API/架构/配置不兼容）。
- **次版本 Y**：新增功能，向下兼容。
- **修订版本 Z**：只修 bug / 安全修复，无新功能，完全兼容。

---

## [1.2.0] - 2026-08-25（当前）

### 新增
- 插件设置项 API：api.add_setting(key, label, kind, default, options)
  （text / file / number / select / bool / range 滑块）
- 「插件设置」窗口：插件注册的设置项在此调整，保存到 config.json，重启保留
- 插件设置实时预览：滑块 / 文件 / 下拉 / 输入改动即时刷新预览
- 文字水印 + 图片水印可同时存在（插件水印样式叠加在文字水印之上）
- 图片水印插件：自定义图片（PNG/JPG/GIF，动图取第一帧静态）+ 10 张内置预设 GIF 水印
- 预设水印以缩略图画廊显示，点击选择
- 字体：支持子文件夹扫描、「刷新字体」按钮、打开下拉自动刷新、损坏字体自动回退
- 插件独立仓库模式（插件不再随本体发布，自由下载安装）
- 插件版本号机制：插件管理窗口显示每个插件的版本

### 修复
- 预设水印图缩略图点击无效（lambda 闭包变量捕获）
- 字体识别相关优化
- 自动更新替换失败（“Security validation failure”）：改用 VBS + ShellExecute，不再经过 cmd

### 其他
- 发布包 / 插件安装包按版本命名，releases/vX.Y.Z/ 分目录

---

## [1.1.0] - 2026-08-25

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
