# Learn OpenCode · Jupyter 学习册

本册面向已经了解 Agent 基础概念、想读懂原版 OpenCode 设计的人。教学基准为 [原版提交 ee5fe34e13](https://github.com/anomalyco/opencode/tree/ee5fe34e136488a1839ac73bcca8321c51a31b75)。

| 顺序 | Jupyter 样章 | 观察重点 |
|---|---|---|
| 1 | [架构总览](notebooks/01-architecture.ipynb) | 接入方式和 Server、Core、模型服务的边界 |
| 2 | [内置工具目录](notebooks/02-tools.ipynb) | 注册、可见性、权限、Code Mode |
| 3 | [内置提示词清单](notebooks/03-prompts.ipynb) | 角色、默认模板、附加指令和专用请求 |
| 4 | [单条消息闭环](notebooks/04-message.ipynb) | Inbox、模型 Step、工具回传、空闲 |
| 5 | [子 Agent 与任务分派](notebooks/05-subagent-dispatch.ipynb) | 模型工具与用户命令两条派发入口 |
| 6 | [后台 Job 与结果回传](notebooks/06-background-jobs.ipynb) | 事务提交、父 Inbox、取消与恢复 |
| 7 | [/goal 与目标复核](notebooks/07-goal.ipynb) | 评审、继续、等待、停滞与暂停 |
| 8 | [事件与 Bus](notebooks/08-events-and-bus.ipynb) | 事务提交、投影、序号、历史载荷与实时通知 |
| 9 | [投影与 SQLite 持久化](notebooks/09-projections-storage.ipynb) | 同一个消息 ID 从 Inbox 进入会话历史 |
| 10 | [重启恢复与崩溃边界](notebooks/10-restart-recovery.ipynb) | 运行认领、待投递 Job、恢复次数与父 Inbox |
| 11 | [上下文管理与历史选择](notebooks/11-context-history.ipynb) | 指令基线、历史切点、keepID 与模型兼容性 |
| 12 | [Token 预算与压缩触发](notebooks/12-token-budget.ipynb) | 输入窗口、估算、缓冲、输出上限和后台摘要 |
| 13 | [压缩与接续请求](notebooks/13-compaction.ipynb) | 长会话、长采购材料、溢出恢复和原生协议 |
| 14 | [配置、Skills 与插件加载](notebooks/14-extensions.ipynb) | 配置来源、按需注入 Skill、激活与重载 |
| 15 | [Hooks 与 MCP](notebooks/15-hooks-mcp.ipynb) | 调用阶段、工具目录、权限与结果回传 |
| 16 | [CLI、客户端、SDK 与事件流](notebooks/16-clients-protocol.ipynb) | 命令分派、共享 API、SSE 与断线恢复 |
| 17 | [CI、构建与发布](notebooks/17-ci-release.ipynb) | 19 个工作流、发布门禁、产物与生成物校验 |
| 18 | [综合实验与设计取舍](notebooks/18-capstone.ipynb) | 两条端到端案例，派发、重启、报告、压缩与验收 |
| 附录 | [LangChain 对照阅读](appendix/langchain.md) | 用轻量任务对照原版机制 |

[带图 Markdown 阅读版](阅读版.md) · [Mermaid 源文件与 SVG](diagrams/) · [原版实验文件与归属](fixtures/upstream/README.md)

## 打开与运行

在学习目录中执行下面命令启动 JupyterLab。Notebook 使用 Python 3 内核。提示词章会在 Bun 可用时调用随附的原版 TypeScript，各章均包含离线观察材料。

```bash
uv run --with jupyterlab --with ipykernel jupyter lab
```

默认观察实验读取随附资料。查看工具时，可以按关键字筛选静态清单。消息实验并列展示上游预期事件、上游实录 HTTP 响应，以及单独标记的 ISO 9001 教学轨迹。

源图以 `.mmd` 保存。SVG 与阅读版一同上传时，保留 `diagrams/` 相对路径。Notebook 的图已内嵌。

## 重跑子 Agent 与 /goal 案例

默认运行会显示本册逐案例验证记录。要在本机运行同一组原版测试，可在一个独立 OpenCode 副本中检出课程提交，使用 Bun 1.4.4 从根目录执行 `bun install --frozen-lockfile`，再回到学习目录启动 Jupyter。

```bash
LEARN_OPENCODE_SOURCE=/path/to/pinned-opencode uv run --with jupyterlab --with ipykernel jupyter lab
```

Notebook 会核对源码提交和 Bun 版本，再从 `packages/core` 运行指定用例。模型回复使用上游确定性测试夹具。每个案例对应的命令、源码、断言解释和计数见 [原版案例记录](fixtures/orchestration-cases.json)。

## 重跑事件、投影与恢复实验

08–10 使用同一个 `LEARN_OPENCODE_SOURCE` 配置。默认读取随课保存的 [原版实跑记录](fixtures/storage-cases.json) 和 [SQLite 实测行](fixtures/storage-observations.json)；配置独立副本后，可以重跑原版测试并重新采样。观测单元临时复制固定提交的测试文件，增加只读查询，执行后移除临时测试文件。恢复采样使用隔离的文件数据库，Bun 退出后由 Python 以只读方式重开。测试夹具控制模型及恢复时序。

## 重跑上下文与压缩实验

11–13 使用同一个 `LEARN_OPENCODE_SOURCE` 配置。默认可查看 [原版案例结果](fixtures/context-cases.json) 和 [已采集的模型请求与预算](fixtures/context-observations.json)。配置独立副本后，同一单元格会从固定提交重新采样。配套脚本只在选定副本的测试目录创建临时测试文件，结束后清理。采购材料案例使用虚构文件和固定模型回复，原版 Runner 决定实际触发与接续请求。原生压缩案例在上游本地测试 HTTP 服务采集协议体。

## 重跑扩展机制、客户端与综合实验

14–18 仍使用同一个 `LEARN_OPENCODE_SOURCE` 设置。默认可查 [原版用例实跑清单](fixtures/final-cases.json)、[运行时观测](fixtures/final-observations.json)、[19 个 CI 结构清单](fixtures/ci-workflows.json) 和 [综合实验轨迹](fixtures/capstone-observations.json)。

综合实验将两个课堂案例附加到原版测试的临时副本，通过原版工具分派、文件 SQLite、两个服务作用域、Job 恢复、标准压缩和主请求接续完成核查。模拟故障发生在服务作用域关闭时，模型回复和最终结论使用确定性 TestLLM。课程记录的是原版控制流和证据是否到达模型。CI 章解析全部工作流定义，并实跑本地生成物一致性与契约检查。

## 验证记录

01–04 已用独立 Python 内核逐单元执行。提示词章用 Bun 运行原版模板，消息章的可选单元在独立的 OpenCode 副本里完成上游 HTTP 录制集成测试。ISO 9001 轨迹为虚构教学案例。

独立副本使用原版锁文件及 Bun 1.4.4。执行以下原版 Core 测试的两组结果合计为 370 通过、0 失败。源仓库未因这次验证修改代码或重装依赖。

```bash
cd packages/core
bun run test test/session-runner-recorded.test.ts test/session-run-coordinator.test.ts test/session-system-prompt.test.ts test/plugin/optimize.test.ts test/session-runner-tool-events.test.ts
bun run test test/session-prompt.test.ts test/session-runner.test.ts
```

05–07 同时验证了默认离线读档和从 Notebook 直接运行原版测试两种模式。教材挑了 14 组观测案例，共选中 19 个上游测试，全部通过。单独运行下面九个相关文件，另得到 **119 通过、0 失败**，包含了教材选中的测试。

```bash
cd packages/core
bun run test test/tool-subagent.test.ts test/config/command-subagent.test.ts test/subagent-idle-e2e.test.ts test/subagent-report.test.ts test/subagent-lifetime.test.ts test/subagent-completion.test.ts test/session-execution.test.ts test/plugin/goal.test.ts test/plugin/goal-watchdog.test.ts
```

08–10 的 13 组课堂案例包含 23 个通过的原版测试。独立执行以下九个原版文件，结果为 **229 通过、0 失败**。数据库观测证据覆盖回滚、关闭历史载荷、Inbox 交付、运行认领恢复和完成报告补送。

```bash
cd packages/core
bun run test test/bus.test.ts test/bus-unpersisted.test.ts test/bus-session-routing.test.ts test/session-projector.test.ts test/session-prompt.test.ts test/session-runner-recorded.test.ts test/session-execution.test.ts test/shell-restart.test.ts test/subagent-report.test.ts
```

11–13 默认离线和原版重跑均已验证。课堂索引包含 10 组筛选用例，20 个原版测试通过。另执行教材覆盖的下面六个原版测试文件，结果为 **312 通过、0 失败**。模型兼容检查点的两个课堂测试来自额外的 `session-native.test.ts`，单独包含在课堂索引。

```bash
cd packages/core
bun run test test/session-compaction.test.ts test/session-native-compaction.test.ts test/session-compaction-transport.test.ts test/session-instructions.test.ts test/session-runner.test.ts test/config/compaction.test.ts
```

14–18 的课堂清单包含 14 组原版筛选用例、28 个通过的原版测试，另有 2 条完整课堂场景通过。直接运行相关 Core、Server、CLI、SDK、Client 和 Protocol 测试文件，合计 345 通过、0 失败。Protocol 与 Client 原版 `check:generated` 在固定提交的独立副本中均通过。发布、签名、跨平台矩阵和在线部署部分按 19 个 YAML 定义讲解。

全书共 18 个 Notebook、23 张 Mermaid 图。每个 Notebook 都保留可直接查看的输出与源代码归属，Markdown 阅读版包含全部章节和图源索引。
