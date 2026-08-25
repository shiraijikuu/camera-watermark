# Photo Watermark 项目规则

除工作区规则（见 E:\codex\AGENTS.md）外，本项目的额外约定：

- 当前版本：主程序 **v1.3.2**（`app.py` 的 `APP_VERSION`）
- 插件各自带版本号（`PLUGIN_VERSION`），插件在独立仓库维护，不放入本体
- 版本历史见 `CHANGELOG.md`，发布流程见 `RELEASE.md`
- 发布包按版本放在 `releases/vX.Y.Z/`，包名含版本号；插件安装包在 `releases/plugins/`
- 遵循语义化版本：新增功能→次版本+1；修 bug→修订版本+1；破坏性变更→主版本+1
- 小更新可累积，每 10 次小更新升一次版本号（次版本或修订版本）
