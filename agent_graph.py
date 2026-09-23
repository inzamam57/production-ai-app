import os
import operator
import logging
from typing import Annotated, TypedDict, List
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from rag_engine import search_policy_docs

load_dotenv()
logger = logging.getLogger("agent-runtime")

# 1. Define State Structure
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    documents: List[str]

async def create_agent_runtime():
    # 2. Verify API credentials
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not set. Please add it to your .env file.")

    # 3. Connect to FastMCP Tool Server via SSE transport
    mcp_url = os.getenv("MCP_SERVER_URL", "http://localhost:8001/sse")
    client = MultiServerMCPClient({
        "customers": {
            "transport": "sse",
            "url": mcp_url
        }
    })
    tools = await client.get_tools()

    # 4. Initialize Gemini with active high-throughput Flash-Lite model
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash-lite",
        api_key=api_key,
        max_retries=5  # Automatically backs off if temporary rate limit spikes occur
    )
    llm_with_tools = llm.bind_tools(tools)

    # 5. Define Graph Nodes
    async def retriever_node(state: AgentState) -> dict:
        """Ground queries against internal policy documents before LLM execution."""
        last_query = state["messages"][-1].content
        docs = search_policy_docs(last_query)
        return {"documents": docs}

    async def agent_node(state: AgentState) -> dict:
        """Reason over user prompt and retrieved RAG context to take actions."""
        messages = list(state["messages"])
        if state.get("documents"):
            doc_context = "\n".join(state["documents"])
            system_msg = HumanMessage(
                content=f"[SYSTEM CONTEXT - POLICIES]:\n{doc_context}\n\nStrictly adhere to these policies in your reasoning."
            )
            messages.append(system_msg)

        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

    # 6. Define Conditional Edge Router
    def router(state: AgentState) -> str:
        """Route to 'tools' if model requested tool call, otherwise complete."""
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END

    # 7. Assemble StateGraph Workflow
    workflow = StateGraph(AgentState)
    
    workflow.add_node("retrieve", retriever_node)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(tools))

    # Graph transitions: START -> retrieve -> agent -> (tools <-> agent) -> END
    workflow.add_edge(START, "retrieve")
    workflow.add_edge("retrieve", "agent")
    workflow.add_conditional_edges("agent", router, {"tools": "tools", END: END})
    workflow.add_edge("tools", "agent")

    # 8. Compile runtime with in-memory session checkpointing
    return workflow.compile(checkpointer=MemorySaver())