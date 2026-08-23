import asyncio
import json
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from typing import TypedDict, Annotated
from operator import add

from app.model.llm_model import init_llm_model


# 1. 定义状态
class AgentState(TypedDict):
    messages: Annotated[list, add]

# 2. 定义节点
async def chatbot(state: AgentState):
    """普通 LLM 调用节点"""
    llm = init_llm_model()
    response = await llm.ainvoke(state["messages"])
    return {"messages": [response]}

async def tool_node(state: AgentState):
    """模拟工具执行节点"""
    # 模拟耗时操作
    await asyncio.sleep(1)
    return {"messages": [{"role": "tool", "content": "北京今天晴，25°C"}]}

# 3. 构建图
workflow = StateGraph(AgentState)
workflow.add_node("chatbot", chatbot)
workflow.add_node("tool", tool_node)
workflow.set_entry_point("chatbot")
workflow.add_edge("chatbot", "tool")
workflow.add_edge("tool", END)

app = workflow.compile()

# 4. 使用 astream_events 消费事件
async def main():
    config = {"configurable": {"thread_id": "test-1"}}
    inputs = {"messages": [{"role": "user", "content": "今天天气怎么样？"}]}

    # ⚠️ 关键参数: version="v2" 是当前推荐的标准版本
    async for event in app.astream_events(inputs, config=config, version="v2"):
        kind = event["event"]
        name = event.get("name", "")
        data = event.get("data", {})

        # 🔹 过滤并处理你关心的事件类型
        if kind == "on_chat_model_stream":
            # LLM 逐 token 流式输出
            chunk = data.get("chunk")
            if chunk and hasattr(chunk, "content") and chunk.content:
                print(f"[TOKEN] {chunk.content}", end="", flush=True)

        elif kind == "on_tool_start":
            print(f"\n[TOOL START] {name} | Input: {data.get('input')}")

        elif kind == "on_tool_end":
            print(f"[TOOL END] {name} | Output: {data.get('output')}")

        elif kind == "on_chain_start" and name in ("chatbot", "tool"):
            print(f"\n[NODE ENTER] {name}")

        elif kind == "on_chain_end" and name in ("chatbot", "tool"):
            print(f"[NODE EXIT] {name}")

        # 💡 调试技巧：取消下面注释可查看所有原始事件结构
        # print(json.dumps(event, indent=2, default=str))

    print("\n✅ Done")

asyncio.run(main())