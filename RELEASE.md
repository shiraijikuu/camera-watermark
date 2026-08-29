# Release Guide / 发布流程说明

This document describes how to release a new version of camera-watermark. 本文档说明如何发布 camera-watermark 新版本。


## Version Policy / 版本策略（强制）

- Follow strict SemVer: Major X = breaking, Minor Y = new features, Patch Z = bug fixes only.
  严格语义化版本：主版本=破坏性变更，次版本=新增功能，修订版本=只修 bug。
- Small updates may accumulate: bump once per ~10 small updates.
  小更新可累积：每 10 次小更新升一次版本号。
- Every version bump MUST update / 每次升版本必须更新：
  1. Version constant (APP_VERSION for the app; PLUGIN_VERSION for plugins) / 版本号常量
  2. CHANGELOG.md (new entry at top) / 更新日志顶部新增条目
  3. Release notes & announcement / 发布说明与更新公告
  4. Repackage, put packages in releases/vX.Y.Z/, filename includes version / 重新打包并放入对应版本目录
- Plugins are versioned independently (PLUGIN_VERSION in plugin.py) / 插件独立带版本号。

## 0. Versioning Rules / 版本规则 (SemVer)

Follow strict semantic versioning x.y.z / 严格遵循语义化版本 x.y.z：
- Major X: breaking changes / 主版本 X：破坏性变更，不兼容旧版本
- Minor Y: new features, backward compatible / 次版本 Y：新增功能，向下兼容
- Patch Z: bug fixes only / 修订版本 Z：只修 bug / 安全修复，无新功能

## 1. Update Version & Docs / 更新版本号与文档

Edit these files / 修改以下文件：

1. `app.py` — set `APP_VERSION = "x.y.z"` / 设置版本号
2. `CHANGELOG.md` — add a new entry at the top / 顶部新增一条更新日志
3. `RELEASE_NOTES.md` — update the release notes (bilingual) / 更新发布说明（中英双语）
4. `update.json` — set `version` and `url` (point to the new release exe asset) and `note`
   / 设置 version、url（指向新版 Release 的 exe 附件）和 note

## 2. Rebuild the exe / 重新打包 exe

    pip install -r requirements-dev.txt
    # 生成版本信息（从 app.py 的 APP_VERSION 读取，降低杀软误报）
    python make_version_info.py
    pyinstaller --noconfirm --clean --onefile --windowed --name "camera-watermark" --hidden-import "PIL._tkinter_finder" --hidden-import "windnd" --collect-all "tkinterdnd2" --version-file version_info.txt app.py

Output is in dist/. Then / 产物在 dist/，然后：
- Copy the new exe as the hot-update asset / 复制新版 exe 作为热更新附件：
    copy dist\camera-watermark.exe dist\camera-watermark-x.y.z.exe

## 3. Prepare release packages / 准备发布包

    # portable package / 分发包（普通用户）
    Compress-Archive -Path dist\* -DestinationPath releases\vX.Y.Z\camera-watermark-x.y.z-portable.zip
    # source package / 开源版（源码 + 成品）
    Compress-Archive -Path open-source -DestinationPath releases\vX.Y.Z\camera-watermark-x.y.z-source.zip

Note: keep dist and open-source out of git (see .gitignore). / 注意：dist 和 open-source 不进 Git（见 .gitignore）。

## 4. Commit, tag and push / 提交、打标签、推送

    git add .
    git commit -m "vX.Y.Z: ..."
    git tag vX.Y.Z
    git push
    git push origin vX.Y.Z

## 5. Create the GitHub Release / 在 GitHub 创建 Release

1. Open / 打开：https://github.com/shiraijikuu/camera-watermark/releases/new
2. Choose tag `vX.Y.Z` / 选择标签 vX.Y.Z
3. Title: `camera-watermark vX.Y.Z`
4. Description: paste the content of RELEASE_NOTES.md (bilingual) / 粘贴 RELEASE_NOTES.md 内容（中英双语）

> **更新公告只保留当前版本 / Release notes keep ONLY the current version:**
> `RELEASE_NOTES.md` 每次发布新版时**用新版本内容覆盖**（不累积历史）；完整历史见 `CHANGELOG.md`。
> Overwrite `RELEASE_NOTES.md` with the new version's announcement each release (do not accumulate); full history lives in `CHANGELOG.md`.
5. Attach these 3 files / 附件拖入这 3 个文件：
   - `camera-watermark-x.y.z-portable.zip`
   - `camera-watermark-x.y.z-source.zip`
   - `camera-watermark-x.y.z.exe` (hot-update asset / 热更新下载用)
6. Publish release / 发布

## 5.5 Purge CDN cache / 刷新 CDN 缓存（重要，发布后必做）

The app reads manifests (`update.json` / `plugins.json`) from the jsDelivr CDN by default.
jsDelivr may serve a **stale cached copy** for a while after a push, so the store / hot-update won't see the new version immediately.

应用默认从 jsDelivr CDN 读取清单（update.json / plugins.json）。推送后 jsDelivr 可能仍返回旧缓存，
商店 / 热更新无法立刻看到新版本。发布后请执行一次 purge（几秒生效）：

    curl https://purge.jsdelivr.net/gh/shiraijikuu/camera-watermark@main/plugins.json
    curl https://purge.jsdelivr.net/gh/shiraijikuu/camera-watermark@main/update.json

（返回 `{"status":"finished"}` 即成功；GitHub 上的内容始终是对的，只是 CDN 缓存滞后。）

## 6. Plugin checksum must be in sync / 插件 checksum 必须同步（重要）

When you re-publish a plugin zip (even with the same version), the store verifies the downloaded file against
`plugins.json` -> `checksum` (SHA-256 of the zip). **If you change the zip, you MUST update the checksum**,
otherwise users will get "checksum mismatch" and cannot install/update.

发布/重新发布插件 zip 后，**必须同步更新 `plugins.json` 里的 `checksum`**（zip 的 SHA-256），否则用户会因
"checksum 不匹配" 而无法安装/更新。计算方式：

    sha256sum camera-watermark-image-watermark-vX.Y.Z.zip

（建议后续用 GitHub Actions 在发布时自动计算并写回清单，避免手误。建议后续自动化。）

## 7. Hot update / 热更新

The app checks `update.json` in the repo (default update_url) and downloads the new exe from the Release asset URL, then replaces and restarts itself automatically. / 软件会读取仓库里的 update.json（默认更新地址），从 Release 附件 URL 下载新 exe，自动替换并重启。

No extra steps needed after publishing the Release — the manifest URL already points to the new asset. / 发布 Release 后无需额外操作——清单 URL 已指向新附件。
