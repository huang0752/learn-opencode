# 附录 · LangChain 对照

学完 OpenCode 主课后，可以用同一组资料核查、周报摘要和订单排查样本，观察简单 Agent 需要保留哪些运行机制。本册样章提供这一阅读索引。后续对照实践按消息与工具回传、证据校验、调用预算、固定样本评测展开。

对照时关注两套系统实际交给模型的消息、工具结果、停止条件、耗时和 token。已有的 DeepSeek Flash ISO 9001 实验属于独立练习。原版 OpenCode 的行为以固定提交中的源码和本册标注的回放为依据。

附 [独立 Python 实验](iso9001-langchain.py) 与 [此前 DeepSeek Flash 实测轨迹](iso9001-langchain-trace.jsonl)。轨迹记录 5 次模型请求、7 次只读工具调用，最终判定「符合」。如需联网重跑，在终端中通过环境变量提供 `DEEPSEEK_API_KEY`，再执行 `uv run --script appendix/iso9001-langchain.py`。Notebook 的默认实验可以离线运行。
