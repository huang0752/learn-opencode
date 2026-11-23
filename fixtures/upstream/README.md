# 原版文件

以下文件逐字取自 OpenCode 提交 `ee5fe34e136488a1839ac73bcca8321c51a31b75`，随附原版 MIT 许可证。

| 文件 | 上游位置 |
|---|---|
| `system-prompt.ts` | `packages/core/src/session/system-prompt.ts` |
| `runner/prompt/system.txt` | `packages/core/src/session/runner/prompt/system.txt` |
| `session-runner-recorded.test.ts` | `packages/core/test/session-runner-recorded.test.ts` |
| `openai-chat-streams-text.json` | `packages/core/test/fixtures/recordings/session-runner/openai-chat-streams-text.json` |

Notebook 通过 Bun 直接调用原版系统模板渲染模块。HTTP 录制和测试断言可由 Python 离线读取。运行完整测试需要按仓库锁文件安装好原版工作区。
