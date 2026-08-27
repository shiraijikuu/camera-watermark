# Photo Watermark 项目规则

除工作区规则（见 E:\codex\AGENTS.md）外，本项目的额外约定：

- 当前版本：主程序 **v1.7.0**（`app.py` 的 `APP_VERSION`）
- 插件各自带版本号（`PLUGIN_VERSION`），插件在独立仓库维护，不放入本体
- 版本历史见 `CHANGELOG.md`，发布流程见 `RELEASE.md`
- **更新公告只保留当前版本**：`RELEASE_NOTES.md` 每版覆盖，不累积（完整历史在 CHANGELOG.md）
- 发布包按版本放在 `releases/vX.Y.Z/`，包名含版本号；插件安装包在 `releases/plugins/`
- 遵循语义化版本：新增功能→次版本+1；修 bug→修订版本+1；破坏性变更→主版本+1
- 小更新可累积，每 10 次小更新升一次版本号（次版本或修订版本）

## 已知技术债 / Known Tech Debt

- **中期建议拆分 app.py**（当前 ~1800 行单文件承载 UI/插件系统/更新/导出/扫描/渲染六类职责）：
  拆成 `ui.py` / `plugin_store.py` / `updater.py`。改动大、风险高，暂缓，做功能时逐步迁移。
- **可接受（暂不改）**：`PLUGIN_*` 三个并行全局列表（Data Clumps）；meta / 插件用 dict 而非类型
  （Primitive Obsession）——对小型 Tkinter 工具可容忍。
- 错误日志：统一走 `_log()`（写 `pwm.log`）；配置/安装记录读取在"文件不存在"时不视为错误。
- **插件 UI 容器（未来主程序）**：多个 UI 插件若都往主窗口顶部加 bar 会堆叠；可预留固定"插件 UI 容器"位置（不急）。
