# 内置工具 · 模型如何获得行动能力

模型提出一个工具名称和一组参数。OpenCode 决定该工具是否对当前会话可见、能否访问这些资源、怎样执行，以及把什么结果交回给模型。理解这层边界，就能解释为什么某个工具在源码里存在，却没出现在你的请求里。

![内置插件、工具注册表、会话筛选和实际模型请求](../diagrams/02-tools.svg)

## 先认清三个工具清单

| 看哪里 | 回答什么 |
|---|---|
| **内置插件注册点** | 固定版本随仓库带了哪些能力？某个插件或功能开关生效时，它会注册什么？ |
| **当前位置的注册表 `Tool.list()`** | 当前 Location 有哪些工具已注册？这里还可能包括用户插件和 MCP 服务动态提供的工具。 |
| **当前请求的工具快照和请求定义** | 合并 Agent 与 Session 权限之后，模型真正能看到什么？工具以独立函数暴露，还是由 Code Mode 统一暴露？ |

`SessionContext.select()` 合并权限并计算模型工具策略。`Tool.snapshot()` 排除显式隐藏和整项拒绝的工具，将其余项分成直接工具和 Code Mode 目录。模型请求的 Hook 还能修改描述、参数定义和请求中的工具名。执行时仍会判断具体操作，例如写入哪个文件、访问哪个 URL。**看得到工具，表示模型可以提出调用。具体操作能否执行，由运行时授权。** [内置插件](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/plugin/internal.ts#L264-L332) · [会话选择](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/session/context.ts#L148-L177) · [工具快照](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool.ts#L310-L398) · [请求定义整形](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/session/model-request.ts#L287-L357)

## 一个工具可以怎样呈现

以会话检索为例，源码注册的是命名空间 `opencode.session` 下的 `search`。直接暴露时名称是 `opencode_session_search`。如果该工具进入 Code Mode 目录，模型通过 `execute` 调用 `tools.opencode.session.search`。Code Mode 目录中的各工具仍有各自的参数定义和权限入口。

这里还要区分 **Code Mode** 和 **`full_codemode`**。快照层判断当前权限是否整项拒绝 `execute`。如果拒绝，符合其他条件的目录工具会以直接工具暴露。完整模式是在此之上的实验能力，会改变部分文件工具的呈现，并让模型工具策略隐藏 `glob`、`grep` 和 `webfetch`。例如 Explore 的权限允许 `grep`，却没有给 `execute` 放行，因而可以继续以直接工具使用 `grep`。[命名规则](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/runtime.ts#L300-L307) · [Code Mode 可用条件](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool.ts#L497-L503) · [模型工具策略](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/model-policy.ts#L3-L23) · [Explore 权限](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/plugin/agent.ts#L72-L93)

## 固定版本工具总表

教学基准 `ee5fe34e1364`。下面列出可追到这一版本的固定注册项，包括 Core 工具、随仓 Browser 和 Console 插件，以及快照生成的 `execute`。命名空间工具用点号表示注册分组。直接暴露或经 Code Mode 调用时，按上节的命名方式读取。功能开关的默认值还取决于开发构建和正式发行构建，因此一次实际请求里的数量会变化。配置中的外部 MCP 服务和用户插件可注册新工具，具体成员随运行环境变化。[功能开关声明](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/schema/src/config/flag.ts#L7-L30) · [MCP 动态注册](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/mcp.ts#L38-L77)

### Core · 文件、进程和协作

| 工具 | 接收什么 → 返回或改变什么 |
|---|---|
| `read` | 路径和读取范围 → 行、目录条目或支持的文件内容。[源码](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/plugin/read.ts#L21-L64) |
| `glob` | 路径模式和范围 → 匹配文件列表。[源码](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/plugin/glob.ts#L16-L61) |
| `grep` | 文本或正则、目录和过滤条件 → 匹配位置与行内容。[源码](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/plugin/grep.ts#L15-L81) |
| `edit` | 文件和新旧文本 → 局部编辑与差异信息。[源码](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/plugin/edit.ts#L268-L283) |
| `write` | 文件路径和完整内容 → 创建或覆盖文件。[源码](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/plugin/write.ts#L17-L57) |
| `patch` | 描述新增、修改或删除的补丁 → 变更结果。模型策略通常让 GPT-5 系使用 `patch`，其余走 `edit` 和 `write`，具体匹配以源码条件为准。[注册](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/plugin/patch.ts#L22-L29) · [选择规则](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/model-policy.ts#L19-L36) |
| `shell` | 命令、工作目录和执行时限等 → 输出、退出状态，或后台进程信息。[输入输出](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/plugin/shell.ts#L59-L101) |
| `question` | 问题和可选回答 → 用户返回的答案。[注册](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/plugin/question.ts#L23-L82) |
| `subagent` | 子 Agent、指令、简述和可选子 Session ID → 新建或继续子任务并返回 Session ID。后续报告可通过父会话 Inbox 交付。[输入](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/plugin/subagent.ts#L30-L54) · [Job](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/plugin/subagent.ts#L170-L223) |
| `todowrite` | 带状态的条目列表 → 更新当前会话的待办。须显式启用 `todo` 开关。这个清单记录进度，后台执行由其他组件管理。[源码](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/plugin/todo.ts#L46-L75) |
| `skill` | Skill ID → 激活对应 Skill 并把相关指令用于当前会话。[源码](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/plugin/skill.ts#L36-L67) |
| `webfetch` | URL、输出格式和超时 → 获取单个地址的内容。[源码](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/plugin/webfetch.ts#L13-L32) |
| `websearch` | 查询词 → 搜索结果。模型工具策略会在没有可用搜索提供方时隐藏它。[注册](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/plugin/websearch.ts#L38-L61) · [可见性](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/model-policy.ts#L10-L21) |
| `experimental_image_generate` | 生成要求、输出路径和可选参考素材等 → 生成任务信息。有可用图像模型时注册，图像生成配置和权限也参与控制。[源码](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/plugin/image-generate.ts#L232-L273) |
| `experimental_video_generate` | 生成要求、参考素材、时长等 → 生成任务信息。需视频功能开关和可用视频模型。[开关](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/plugin/video-generate.ts#L191-L194) · [注册](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/plugin/video-generate.ts#L276-L309) |

### Core · 管理、调度和扩展

| 工具 | 接收什么 → 返回或改变什么 |
|---|---|
| `opencode.session.rename`、`opencode.session.move` | 目标 Session 和新名称或目录 → 更新标题或交付会话迁移控制项。[源码](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/plugin/opencode.ts#L122-L177) |
| `opencode.session.search`、`opencode.session.read` | 搜索条件或会话 ID 和游标 → 历史命中或分页消息。由 `sqlite_fts` 控制注册。[源码](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/plugin/session-search.ts#L56-L97) |
| `opencode.worktree_create`、`opencode.worktree_list`、`opencode.worktree_remove` | 工作树名称、当前项目或目标路径 → 创建、列出或移除工作树。移除还检查 `edit` 权限。[源码](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/plugin/opencode.ts#L179-L234) |
| `opencode.models` | 提供方、类型、名称等过滤条件 → 分页模型信息。[源码](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/plugin/opencode.ts#L235-L287) |
| `opencode.list_mcp_resources`、`opencode.read_mcp_resource`、`opencode.list_mcp_events` | MCP 服务名称及资源 URI 等 → 列出资源、读取资源内容或列出可订阅的事件描述。[资源](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/plugin/mcp-resource.ts#L16-L77) · [事件](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/plugin/mcp-events.ts#L30-L68) |
| `opencode.artifact_create`、`opencode.artifact_read`、`opencode.artifact_update`、`opencode.artifact_delete` | 文件映射、提供方或产物 ID → 管理已配置提供方上的产物。由 `artifacts` 控制注册，执行依赖产物服务。[源码](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/plugin/artifact.ts#L66-L152) |
| `automation.create`、`automation.list`、`automation.pause`、`automation.resume`、`automation.delete` | 触发器与动作定义或自动化 ID → 管理项目的定时和事件触发任务。由 `automations` 配置控制，执行再检查项目和操作权限。[源码](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/plugin/automation.ts#L53-L156) |
| `machine.list` | 当前上下文 → 已配置机器列表。由 `machines` 控制注册。[源码](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool/plugin/machine.ts#L12-L36) |

### Browser · 同一套工具定义服务于桌面浏览器

Browser 插件将协议里的 **44 个操作**逐个注册到 `browser` 命名空间。执行需浏览器能力与相应授权，文件传入或传出还检查文件权限。这里按原协议名列出，可在每项前加 `browser.` 得到命名空间路径。[注册器](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/plugin-browser/src/tools.ts#L173-L222) · [完整协议](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/plugin-browser/src/rpc.ts#L292-L665)

| 用途 | 操作 |
|---|---|
| 标签页、导航和加载 | `tabs.list`、`tabs.open`、`tabs.focus`、`tabs.close`、`navigate`、`back`、`forward`、`reload`、`stop` |
| 页面结构与观察 | `frames`、`snapshot`、`find`、`evaluate`、`screenshot` |
| 页面操作 | `click`、`hover`、`drag`、`fill`、`fill_form`、`select`、`check`、`press`、`scroll`、`wait`、`dialog` |
| 页面文件 | `files.upload`、`files.drop`、`files.list`、`files.get` |
| 控制台和网络观察 | `console`、`network.list`、`network.get` |
| 性能记录与报告 | `trace.start`、`trace.stop`、`trace.analyze`、`cpu.start`、`cpu.stop`、`cpu.analyze`、`lighthouse` |
| 内存快照 | `heap.snapshot`、`heap.summary`、`heap.query`、`heap.object`、`heap.compare` |

### 条件注册与快照生成

| 工具 | 在什么场景出现 |
|---|---|
| `console_watch.watch`、`console_watch.unwatch`、`console_watch.watches`、`console_watch.events` | 对支持事件订阅且允许连接的 Console 工作区，开启 `console_watches` 后管理订阅、查看订阅和可用事件。处理发回会话的事件是后台能力。[连接条件](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/plugin/provider/opencode.ts#L332-L356) · [注册](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/plugin/provider/opencode-watches.ts#L258-L391) |
| `execute` | 快照按权限生成的 Code Mode 入口。模型提交程序，通过目录调用已授权工具，得到执行结果和调用记录。[生成](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/tool.ts#L336-L389) · [入口](https://github.com/anomalyco/opencode/blob/ee5fe34e136488a1839ac73bcca8321c51a31b75/packages/core/src/codemode/tool.ts#L141-L169) |

## 用日期错误练一次判断

假设项目的证书到期日判断了 `expiry > deadline`，业务要求是同一天也算有效。打开本章 Notebook 的清单，观察下面三件事。

1. **查哪里。** 先用 `grep` 找判断，再用 `read` 读实现和测试。Explore 可以产出证据和文件位置。
2. **谁能改。** 找到一行错误之后，改动交给有编辑权限的 Agent。根据模型工具策略，同一改动可能用 `patch`，也可能用 `edit`。跑测试则由 `shell` 发起。
3. **结果从哪里回来。** 模型提出文件编辑或测试操作。运行时返回差异、退出状态等证据，再由下一步模型根据记录决定是否完成。

**自测。** 源码里有 `todowrite`，为什么新装的实例可能看不到？答：`todo` 是须显式启用的功能开关。启用后，仍要经过当前 Agent 的权限和请求筛选。又如当前请求只出现 `execute` 而没有 `opencode_session_search`，可以先查看该工具是否进入 Code Mode 目录。这两种现象分别发生在注册层和请求呈现层。
