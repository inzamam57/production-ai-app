import json
import uuid
import httpx
import streamlit as st

st.set_page_config(
    page_title="Enterprise AI Agent",
    page_icon="🤖",
    layout="centered"
)

st.title("🤖 Production AI Agent")
st.caption("Gemini 3.6 Flash + LangGraph + FastMCP + RAG")

# 1. Initialize persistent session state
if "thread_id" not in st.session_state:
    st.session_state.thread_id = f"session-{uuid.uuid4().hex[:8]}"

if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar Controls
with st.sidebar:
    st.header("Session Settings")
    st.code(f"Thread ID:\n{st.session_state.thread_id}", language="text")
    if st.button("Clear Conversation"):
        st.session_state.messages = []
        st.session_state.thread_id = f"session-{uuid.uuid4().hex[:8]}"
        st.rerun()

# 2. Render conversation history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

def extract_text_content(content) -> str:
    """Helper to safely extract string text regardless of Gemini return type."""
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        extracted = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                extracted.append(item["text"])
            elif isinstance(item, str):
                extracted.append(item)
        return "".join(extracted)
    return ""

# 3. Handle user input and streaming response
if prompt := st.chat_input("Ask about customer accounts, policies, or clearance..."):
    # Display user query
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        status_container = st.status("Thinking...", expanded=True)

        try:
            url = "http://localhost:8000/chat/stream"
            payload = {
                "query": prompt,
                "thread_id": st.session_state.thread_id
            }

            # Connect to FastAPI SSE endpoint using httpx streaming client
            with httpx.Client(timeout=60.0) as client:
                with client.stream("POST", url, json=payload) as response:
                    for line in response.iter_lines():
                        if not line:
                            continue

                        if line.startswith("data: "):
                            data_str = line[6:].strip()

                            if data_str == "[DONE]":
                                break

                            try:
                                event = json.loads(data_str)

                                # Handle backend runtime errors
                                if event.get("type") == "error":
                                    status_container.update(label="Error occurred", state="error")
                                    response_placeholder.error(event.get("content"))
                                    break

                                # Handle tool execution status updates
                                elif event.get("type") == "tool_start":
                                    tool_name = event.get("name", "Tool")
                                    status_container.write(f"⚙️ Executing MCP tool: `{tool_name}`...")

                                # Handle token streaming safely
                                elif event.get("type") == "token":
                                    status_container.update(label="Synthesizing response...", state="running")
                                    raw_chunk = event.get("content", "")
                                    text_chunk = extract_text_content(raw_chunk)

                                    full_response += text_chunk
                                    response_placeholder.markdown(full_response + "▌")
                            except json.JSONDecodeError:
                                continue

            if full_response:
                status_container.update(label="Complete", state="complete", expanded=False)
                response_placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})

        except httpx.RemoteProtocolError:
            status_container.update(label="Connection Interrupted", state="error")
            response_placeholder.error("The backend server closed the connection unexpectedly. Check the main.py terminal logs.")
        except httpx.ConnectError:
            status_container.update(label="Connection Failed", state="error")
            response_placeholder.error("Could not connect to FastAPI backend at http://localhost:8000. Is it running?")