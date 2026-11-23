# 15 · Hooks、MCP 与运行时能力边界

假设采购 Agent 需要调用资料库的搜索工具。OpenCode 会先确定当前 Location 有哪些 MCP 工具，再为当前 Session 生成可调用的目录。模型提出调用后，工具运行时处理参数、许可、服务器连接和返回值。Hooks 则能介入这条链中的特定时点。把这两个扩展面分开看，就能定位一个工具究竟是没发现、没展示、没授权，还是调用后返回了错误。

![Hook 扩展点与 MCP 发现、授权、执行和更新](../diagrams/20-hooks-mcp.svg)

## 1 · Hook 改的是哪一刻的数据

`PluginHooks` 把回调按 domain 和事件名分组，注册作用域结束后会卸载。触发时，适用的回调按注册顺序处理同一个事件对象。带 provider 过滤的回调只处理匹配的模型请求。Hook 有明确的调用阶段和字段，调试时先确认自己拿到的是准备中的草稿、已组装的请求，还是工具执行后的结果。[作用域、触发和 provider 过滤](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/plugin/hooks.ts#L69-L101)

| 时点 | Hook 能参与什么 |
|---|---|
| 提交 prompt | `session.prompt` 可改待提交的 prompt、元信息与投递方式。Runner 后续才读取写入的内容。 |
| 准备模型请求 | `context`、`compaction`、`generate` 和 `title` 分别接收对应草稿。主请求的 `context` 可以整理系统片段、消息、工具描述与参数定义。 |
| 协议与模型调用 | `session.model.request` 在组装之后触发。已注册的 HTTP Hooks 可围住传输请求和响应。这里能看到更接近实际线上请求的内容。 |
| 工具前后 | `tool.execute.before` 可整理参数或工具名，允许通过类型化错误拒绝执行。运行时接着解析别名、可用性与参数。进入执行后，`tool.execute.after` 会看到完成结果，或被捕获的工具错误。 |
| 运行边界 | `session.retry` 和 `experimental.idle` 分别在重试和即将空闲时触发。第 07 章的 `/goal` 就通过 idle Hook 看证据并决定是否续做。 |

[提交前处理](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/session/prompt.ts#L38-L54) · [请求组装与 Hook](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/session/model-request.ts#L287-L329) · [模型与 HTTP 时点](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/session/model-request.ts#L364-L419) · [压缩和生成等入口](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/session/model-request.ts#L469-L476) · [工具执行前后](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool.ts#L164-L224) · [重试入口](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/session/model-request.ts#L430-L444) · [目标复核](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/plugin/goal.ts#L209)

**案例 · 工具名和参数需要修正。** 原版集成测试让模型给出别名或形状有误的参数，观察前置 Hook 怎样修复它们，再由原来的工具 schema 校验。Code Mode 的内层调用也有相应的输入校验。即使 Hook 把名称改成一个已知工具，当前请求没有授权该工具定义时，工具快照仍会拦下它。工具自己的资源许可继续在执行阶段生效。[修复测试](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/test/plugin/tool-input-repair-integration.test.ts#L19) · [内层 Code Mode 测试](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/test/plugin/tool-input-repair-integration.test.ts#L127) · [快照与别名约束](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool.ts#L398-L417) · [工具参数解码](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/runtime.ts#L40-L57)

## 2 · MCP 从一个连接变成模型能调用的工具

配置中的服务器可以是本地进程或远程连接，客户端还可以附加自己提供的连接。连接建立时，MCP 客户端协商协议能力，再读取服务器实际提供的工具、资源或提示词。对于正在连接的配置服务器，Session 选上下文时会通过 `McpTool.flush` 给它有限的等待时间，随后使用已就绪的工具，目录接口也能返回当前已连接的清单。此提交的启动等待以连接开始计，宽限为 2 秒。[连接协商](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/mcp/client.ts#L349-L410) · [当前目录和启动宽限](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/mcp/index.ts#L1041-L1063) · [宽限常量](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/mcp/index.ts#L126-L130) · [Session 选上下文](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/session/context.ts#L148-L185)

SDK 读取分页目录后，OpenCode 逐条检查工具定义。缺少名称或基本输入 schema 形状有误的项可以单独跳过。通过检查的项进入工具注册表，并使用从服务器名派生的 namespace。同一能力可以作为直接工具，也可以出现在 Code Mode 目录中。Session 快照会根据 Agent、会话权限与 Code Mode 是否可用决定呈现方式。服务器提供的说明也从该快照判断，只为至少有一个工具可达的服务器展示。[分页与逐项检查](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/mcp/client.ts#L789-L842) · [目录登记](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/mcp.ts#L23-L60) · [工具快照](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool.ts#L318-L356) · [服务器说明的可达检查](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/mcp/instructions.ts#L70-L102)

名字相同的客户端附加连接和配置服务器可以同时存在。已附加连接对它列出的同名工具有优先权，同一附加名称也可以堆叠多个连接，关闭顶层后回退。服务器连接状态或列表变化发出事件，经过防抖后重新建立注册表。后续请求会看到新的快照。在工具列表里看到条目仍需等运行时授权。[附加连接的目录优先级](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/mcp/index.ts#L804-L835) · [调用归属](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/mcp/index.ts#L1064-L1089) · [目录变更刷新](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/mcp.ts#L122-L150) · [目录变动测试](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/test/mcp-attach.test.ts#L319)

## 3 · 权限、调用身份和返回值看哪几层

执行 MCP 工具时，适配器以有效工具名调用 `permission.assert`，通过后才向具体服务器发出 `tools/call`。运行时通过调用上下文传入 Session ID，MCP 客户端把它作为协议元信息发送。直接工具和 Code Mode 都沿这条授权与身份传递路径工作。模型的函数参数里无需提供 Session ID。原版授权测试用延迟门控，确认批准前外部调用次数为 0，批准后为 1。拒绝路径不会调用外部工具。[权限与调用上下文](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/mcp.ts#L61-L83) · [MCP 元信息](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/mcp/client.ts#L877-L888) · [两种调用形态测试](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/test/mcp.test.ts#L2853) · [授权等待及拒绝测试](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/test/mcp.test.ts#L3046)

回来的内容分为结构化输出与模型可读部分，有 `isError` 时走工具错误。内容可以是文字或支持的媒体，其他二进制内容保存后用路径提示。目录中的输出 schema 会保留给调用方参考，OpenCode 客户端实际调用时跳过 SDK 对返回值的严检，有些服务动作已完成却返回空响应或不符合声明的字段。教学实验需要区分「目录保留 schema」「原始 SDK 的校验行为」和「OpenCode 适配器实际保留的结果」。[返回值适配](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/mcp.ts#L84-L114) · [媒体与二进制处理](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/mcp.ts#L155-L170) · [SDK 校验选择](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/mcp/client.ts#L892-L900) · [分页保留输出结构](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/test/mcp.test.ts#L756) · [OpenCode 客户端的兼容结果测试](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/test/mcp.test.ts#L1341)

## 4 · 资源用于读证据，事件用于启动工作

**案例 · 读取采购附件。** MCP 资源描述可读对象及模板。原版的 list/read 工具会分别按服务器和资源 URI 申请权限。通过目录定位 URI 后再读取，得到文件正文或支持的媒体。MCP prompt 也有独立的发现与获取路径。资源、prompt 和工具使用各自的协议目录与更新通知。[资源列表与读权限](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/plugin/mcp-resource.ts#L18-L76) · [协议目录能力检查](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/mcp/client.ts#L846-L876) · [连接就绪后通知](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/mcp/index.ts#L696-L705) · [资源目录变化测试](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/test/mcp.test.ts#L1429)

**案例 · 订单状态推送。** 原版工具能列出支持 push 的实验性 MCP 事件。设置自动化时，会验证被授权的服务器、事件与参数。运行中，订阅按游标接收事件，执行器再次检查自动化仍有效，再运行对应动作。普通 MCP 共享订阅也能重连并跳过已记住的近期事件 ID。自动化还维护持久游标与交付状态，用于重连后接续。需要判断是否重复执行时，可以先查事件 ID 和游标，再查 Session Inbox 的交接。[事件工具](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/plugin/mcp-events.ts#L30-L60) · [游标与近期去重](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/mcp/index.ts#L298-L347) · [自动化消费与游标](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/automation.ts#L822-L865) · [事件订阅重连测试](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/test/automation-event.test.ts#L369)

### Notebook 要验证什么

1. 在修复参数实验里，区分 Hook 看见的输入和最终交给原工具校验的输入。
2. 比较目录中的 MCP 工具名、许可请求和真实 `tools/call`。关键证据是批准前调用计数为 0，以及协议元信息中的 Session 身份。
3. 对照目录刷新、资源变化和事件重连三个案例。它们分别改变工具可见性、更新可读取的证据、触发后续工作。
