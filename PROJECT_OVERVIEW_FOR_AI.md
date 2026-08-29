# camera-watermark 项目结构说明

> 供 AI 协作/审查用。项目：Windows 桌面相机照片水印软件（Python + Tkinter + Pillow，PyInstaller 打包）。

## 一、项目概览

- **主程序仓库**：`shiraijikuu/camera-watermark`（本地路径 `E:\codex\camera-watermark`）
- **当前版本**：主程序 **v2.0.0**（Latest Release 已发布）；三个插件独立版本
- **定位**：给相机照片自动添加"相机参数水印"（品牌/型号/镜头/焦距/光圈/快门/ISO/日期），支持文字水印 + 图片水印（品牌 logo）+ 模糊卡片样式
- **技术栈**：Python 3.11 + tkinter/ttk + Pillow；打包 PyInstaller onefile；更新/商店走 GitHub Release + jsDelivr CDN（带双源回退）

## 二、主仓库目录结构（E:\codex\camera-watermark）

### 核心代码
| 文件 | 作用 |
|---|---|
| `app.py` | 主程序（~1800 行）：UI 构建、插件系统、更新检测、插件商店、扫描/导出、预览渲染 |
| `photo.py` | 水印渲染核心：EXIF 解析、`render_template`（模板渲染，支持空行/手动空格/word_spacing）、`_watermark_layout`/`render_watermark`（文字水印）、`watermark_rect`（命中矩形）、RAW 解码、导出 |
| `lang.py` | 三语（简体/英文/繁体）翻译表 |
| `make_version_info.py` | 从 `APP_VERSION` 生成 PyInstaller 版本资源（降低杀软误报） |
| `validate_store.py` | 校验 plugins.json 的 checksum/结构 |

### 清单与配置
| 文件 | 作用 |
|---|---|
| `plugins.json` | **插件商店清单**（CDN 读取）：id/name/description/author/repo/license/version/tags/install_url/checksum |
| `update.json` | **热更新清单**：version/url（Release exe）/note/checksum |
| `config.json` | 用户配置（含 `plugin_values` 存插件设置） |

### 测试（python -m unittest discover）
`test_photo.py`（EXIF/水印/word_spacing/空行）、`test_drag_ui.py`、`test_view_ui.py`（预览/缩放/拖拽）、`test_blur_card.py`（模糊卡片+overlay）、`test_image_wm_layout.py`（图片水印对齐）、`test_plugin_store.py`、`test_updater.py`、`test_scale_entry.py`（滑块输入框）、`test_ui_hooks.py`、`test_window_hooks.py`、`test_drop.py`、`test_empty_ui.py`、`test_list_ui.py`、`test_export_ui.py`、`test_preview_ui.py` — **当前 196 项全过**

### 目录
| 目录 | 作用 |
|---|---|
| `plugins/` | 本地插件加载目录（git 忽略 `plugins/*/`，只跟踪 `plugins/README.md`） |
| `plugin-repos/` | 插件独立仓库的工作区（image-watermark / blur-card / theme-switcher） |
| `dist/` | PyInstaller 打包产物（exe + 文档），本地测试环境 |
| `releases/` | 发布包：`releases/vX.Y.Z/`（portable/source/exe）+ `releases/plugins/`（插件 zip） |
| `open-source/` | 开源版打包目录（源码 + dist），发布 source zip 用 |
| `.github/workflows/` | CI（unittest + validate_store） |
| `fonts/` | 用户字体目录 |

## 三、插件系统架构（关键）

### 插件格式
- `plugins/<name>/plugin.py`，实现 `register(api)`；通过 `api.add_*` 注册能力
- 插件**独立仓库**维护 + 商店（plugins.json）分发，发布 zip **不含**在主程序包内

### 插件 API（PluginAPI，app.py）
| 方法 | 说明 |
|---|---|
| `add_watermark_style(name, label, renderer, replaces_watermark=False, rect_func=None, overlay_setting=None)` | 注册水印样式。styles 存三元组 `(label, renderer, replaces)` |
| `add_setting(key, label, kind, ...)` | 注册设置项；kind 支持 text/file/number/select/bool/range/**header**（分组标题，v2.0.0 新增） |
| `add_token` / `add_format` / `add_camera_name` / `add_template_preset` | 模板变量 / 导出格式 / 相机名 / 模板预设 |
| `on_export` / `on_ui_ready` / `on_window_created` | 导出钩子 / UI 就绪回调 / 动态窗口回调 |

### 样式渲染管线（`_render_with_style`，预览和导出共用）
1. **默认文字水印**：`photo.render_watermark`（支持 `word_spacing` 参数间距、空行、手动空格）
2. **插件样式**：
   - `replaces_watermark=False`（兼容型，如图片水印）：先画文字水印 → renderer 在带水印图上叠加（文字+图片共存）
   - `replaces_watermark=True`（整图重绘型，如模糊卡片）：跳过默认文字水印 → renderer 拿无水印原图全权绘制
3. **整图重绘 + 兼容叠加**：整图重绘型渲染后，若 `overlay_setting` 允许，再叠加兼容型样式（图片水印/logo）——`blur-card` 默认关闭，可勾选开启
4. **插件崩溃回退**：renderer 抛异常 → 打印错误、不拖垮预览
5. **命中矩形**：插件可传 `rect_func` 声明文字矩形（含 offset），主程序用它做拖拽命中

### 插件设置存储
- 存于 `config.json` → `plugin_values[插件目录名][key]`（目录名如 `image-watermark`、`blur-card`，**连字符**）

## 四、插件（独立仓库，商店分发）

| 插件 | 仓库 | 版本 | 功能 |
|---|---|---|---|
| **image-watermark** | `shiraijikuu/camera-watermark-image-watermark` | v1.3.0 | 1~5 个图片水印叠加（独立大小/位置/旋转/透明度）、10 相机品牌 logo 预设（白/透明 2048px）、水印 1 可与文字对齐（左/右/上/下+间距，透明 logo 用 getbbox、越界自动翻转）、图片缓存、汉化 |
| **blur-card** | `shiraijikuu/camera-watermark-blur-card` | v1.1.0 | 模糊卡片样式：模糊背景（相对 vh 尺寸）+ 清晰前景（圆角/阴影/描边 %）+ 底部相机信息栏（文字可拖拽、word_spacing、非法值防御）；需主程序 >= 2.0.0 |
| **theme-switcher** | `shiraijikuu/camera-watermark-theme-switcher` | v1.0.4 | 黑夜/白天/跟随系统主题，适配动态窗口 |

## 五、版本与发布流程（严格 SemVer）

- **语义化版本 x.y.z**：主=破坏性变更 / 次=新增功能 / 修订=纯修复
- 每次升版本同步：`APP_VERSION`、`CHANGELOG.md`（顶部）、`RELEASE_NOTES.md`（只保留当前版）、`README.md`、`AGENTS.md`、`update.json`（checksum）
- 主程序：PyInstaller 打包（`--collect-all tkinterdnd2`）→ releases/vX.Y.Z/（portable/source/exe 三件）→ GitHub Release（Latest）→ **purge jsDelivr**（`update.json` + `plugins.json`）
- 插件：独立仓库发版 → zip（**不含 fonts、不含插件本体于主包**）→ 更新 `plugins.json` 的 version/install_url/checksum
- **热更新**：应用读 CDN `update.json`，版本号或 checksum 变化即提示更新（自动下载替换重启）
- **双源回退**：jsDelivr `@main` 缓存滞后时，更新检测/商店自动改查 GitHub raw 权威源（v1.9.0 起）

## 六、已知技术债（AGENTS.md 记录）
- `app.py` 单文件 ~1800 行承载六类职责（UI/插件/更新/导出/扫描/渲染），中期建议拆 `ui.py`/`plugin_store.py`/`updater.py`
- `PLUGIN_*` 全局列表并行存在（Data Clumps）；meta/插件用 dict 而非类型
