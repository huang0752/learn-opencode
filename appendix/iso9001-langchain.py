# /// script
# dependencies = ["langchain-openai>=1,<2"]
# ///
import json
import os
from time import perf_counter

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from typing import Literal

PAGES = {
    "P04": "投标人：华宁设备服务有限公司。",
    "P07": "投标截止日期：2026-11-25。",
    "P12": "证书类型：ISO 9001 质量管理体系认证。证书持有人：华宁设备服务有限公司。有效期至 2027-06-30。",
    "P13": "证书类型：ISO 14001 环境管理体系认证。有效期至 2028-02-01。",
}


@tool
def search_pages(keyword: str) -> str:
    """按字面关键词查找材料，只返回匹配的页码。用简短关键词，如 ISO 9001。"""
    return json.dumps([page for page, text in PAGES.items() if keyword.casefold() in text.casefold()])


@tool
def read_page(page: str) -> str:
    """按页码读取完整原文，例如 P12。"""
    return PAGES.get(page, "该页不存在")


class Result(BaseModel):
    status: Literal["符合", "不符合", "待复核"]
    evidence: list[str]
    reason: str


def main():
    tools = {item.name: item for item in (search_pages, read_page)}
    model = ChatOpenAI(
        model="deepseek-flash",
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com",
        extra_body={"thinking": {"type": "disabled"}},
        max_retries=0,
        timeout=30,
        max_tokens=512,
    ).bind_tools(list(tools.values()))
    messages = [
        SystemMessage(content=(
            "你核查一条商务要求。先用搜索定位 ISO 9001 证书候选页，再读取原文，"
            "并读取需要的其他材料。搜索命中仅提供位置。证据不足或冲突时判待复核。"
            '最后只输出 JSON，字段为 status（符合、不符合或待复核）、'
            'evidence（实际读取的页码列表）、reason（简短理由）。'
        )),
        HumanMessage(content="核查投标人是否提交了本公司持有且在投标截止日仍有效的 ISO 9001 证书。"),
    ]
    read_pages = set()
    for step in range(1, 6):
        start = perf_counter()
        reply = model.invoke(messages)
        print(json.dumps({
            "step": step, "seconds": round(perf_counter() - start, 2),
            "finish": reply.response_metadata.get("finish_reason"), "usage": reply.usage_metadata,
        }, ensure_ascii=False), flush=True)
        messages.append(reply)
        if reply.invalid_tool_calls or reply.response_metadata.get("finish_reason") == "length":
            raise RuntimeError("模型返回了无效工具调用或输出截断")
        if not reply.tool_calls:
            result = Result.model_validate_json(reply.content)
            if not set(result.evidence) <= read_pages or (result.status != "待复核" and not result.evidence):
                raise RuntimeError("结论缺少已读取的证据")
            print(result.model_dump_json(), flush=True)
            return result
        for call in reply.tool_calls:
            outcome = tools[call["name"]].invoke(call)
            if call["name"] == "read_page" and call["args"]["page"] in PAGES:
                read_pages.add(call["args"]["page"])
            print(json.dumps({
                "tool": call["name"], "args": call["args"],
                "linked": outcome.tool_call_id == call["id"], "result": outcome.content,
            }, ensure_ascii=False), flush=True)
            messages.append(outcome)
    raise RuntimeError("模型调用已达 5 次上限")


if __name__ == "__main__":
    result = main()
    assert result.status == "符合" and set(result.evidence) == {"P04", "P07", "P12"}, result
