import os
import json
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from agent_graph import create_agent_runtime

load_dotenv()
logger = logging.getLogger("api-gateway")

app_state = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Verify key early during startup
    if not os.getenv("GOOGLE_API_KEY"):
        logger.error("CRITICAL: GOOGLE_API_KEY is not set in .env")
    app_state["graph"] = await create_agent_runtime()
    yield
    app_state.clear()

app = FastAPI(title="Production AI App (Gemini + LangGraph + MCP)", lifespan=lifespan)

class ChatRequest(BaseModel):
    query: str
    thread_id: str = "default-session"

@app.post("/chat/stream")
async def chat_stream_endpoint(payload: ChatRequest):
    graph = app_state.get("graph")
    if not graph:
        def err_stream():
            data = json.dumps({"type": "error", "content": "Graph runtime failed to initialize. Check GOOGLE_API_KEY."})
            yield f"data: {data}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(err_stream(), media_type="text/event-stream")

    async def event_stream():
        config = {"configurable": {"thread_id": payload.thread_id}}
        inputs = {
            "messages": [HumanMessage(content=payload.query)],
            "documents": []
        }

        try:
            async for event in graph.astream_events(inputs, config=config, version="v2"):
                kind = event.get("event")
                
                if kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"].content
                    if chunk:
                        data = json.dumps({"type": "token", "content": chunk})
                        yield f"data: {data}\n\n"
                        
                elif kind == "on_tool_start":
                    data = json.dumps({"type": "tool_start", "name": event.get("name", "Tool")})
                    yield f"data: {data}\n\n"

        except Exception as e:
            err_msg = str(e)
            logger.error(f"Execution error: {err_msg}", exc_info=True)
            
            # User-friendly translation for 429 quota exhaustion
            if "RESOURCE_EXHAUSTED" in err_msg or "429" in err_msg:
                clean_error = "Gemini Free-Tier Rate Limit reached (quota cap: 20 requests). Please wait ~60 seconds before submitting another prompt."
            elif "API_KEY_INVALID" in err_msg or "not set" in err_msg:
                clean_error = "Invalid or missing Google AI Studio API key. Please check your .env file."
            else:
                clean_error = f"Agent error: {err_msg}"
                
            data = json.dumps({"type": "error", "content": clean_error})
            yield f"data: {data}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/chat")
async def chat_sync_endpoint(payload: ChatRequest):
    graph = app_state["graph"]
    config = {"configurable": {"thread_id": payload.thread_id}}
    inputs = {
        "messages": [HumanMessage(content=payload.query)],
        "documents": []
    }
    result = await graph.ainvoke(inputs, config=config)
    return {"response": result["messages"][-1].content}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)