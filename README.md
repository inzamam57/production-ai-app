# Enterprise AI Agent Runtime & Support Copilot

An enterprise-ready, microservices-based AI support copilot featuring stateful workflow orchestration, deterministic RAG policy enforcement, and live tool execution powered by the Model Context Protocol (MCP) and Google Gemini.

---

## Architecture Overview

The application is decomposed into three decoupled services communicating through HTTP and Server-Sent Events (SSE):

```text
┌──────────────────────────────────────────────┐
│              Streamlit Frontend              │
│                  Port 8501                   │
│                                              │
│  • Session threading (`thread_id`)          │
│  • Real-time token & status streaming        │
└──────────────────────┬───────────────────────┘
                       │ HTTP POST / SSE
                       ▼
┌──────────────────────────────────────────────┐
│             FastAPI Agent Gateway            │
│                  Port 8000                   │
│                                              │
│  • LangGraph state machine                   │
│  • RAG knowledge grounding                   │
│  • 429 quota interception & retries           │
└───────────────┬───────────────────┬──────────┘
                │ SSE               │ HTTPS
                │ Port 8001         │ API Key
                ▼                   ▼
┌────────────────────────┐   ┌────────────────────────┐
│   FastMCP Tool Server  │   │     Google AI Studio   │
│                        │   │                        │
│ • get_customer_details │   │ • Gemini 3.5 Flash-Lite│
└────────────────────────┘   └────────────────────────┘
```

### Request Flow

```text
User
  │
  ▼
Streamlit UI
  │
  │ POST /chat/stream
  ▼
FastAPI Gateway
  │
  ├──► RAG Policy Retrieval
  │
  ├──► LangGraph Agent
  │       │
  │       ├──► Gemini
  │       │
  │       └──► MCP Tools
  │               │
  │               └──► Customer Data
  │
  ▼
SSE Token / Status Stream
  │
  ▼
Streamlit UI
```

---

## Tech Stack & Components

| Component | Technology | Purpose |
|---|---|---|
| LLM Engine | Google Gemini `gemini-3.5-flash-lite` | Natural-language reasoning and response generation |
| LLM Integration | `langchain-google-genai` | Connects LangChain/LangGraph to Gemini |
| Agent Orchestration | LangGraph | Stateful agent workflow and tool routing |
| Workflow | `START → retrieve → agent ↔ tools → END` | Controls retrieval, reasoning, and tool execution |
| RAG | In-memory policy search | Grounds agent responses in support policies |
| Tool Protocol | Model Context Protocol (MCP) | Standardized tool execution |
| Tool Server | FastMCP | Exposes customer/database functions over SSE |
| Backend | FastAPI + Uvicorn | API gateway and asynchronous streaming |
| Streaming | Server-Sent Events (SSE) | Real-time token and status delivery |
| Frontend | Streamlit | Interactive support copilot interface |
| Session Memory | LangGraph `MemorySaver` | In-memory conversation checkpointing |
| Configuration | `python-dotenv` | Environment variable management |

---

## LangGraph Workflow

The agent uses a state-machine architecture to separate retrieval, reasoning, and tool execution:

```text
                 ┌──────────────┐
                 │    START     │
                 └──────┬───────┘
                        │
                        ▼
                 ┌──────────────┐
                 │   retrieve   │
                 │  RAG Policy  │
                 └──────┬───────┘
                        │
                        ▼
                 ┌──────────────┐
                 │    agent     │
                 │    Gemini    │
                 └──────┬───────┘
                        │
                   Tool required?
                    /         \
                  Yes          No
                   │            │
                   ▼            ▼
             ┌──────────┐    ┌─────┐
             │  tools   │    │ END │
             └────┬─────┘    └─────┘
                  │
                  └──────────► agent
```

This design allows the copilot to:

- Retrieve relevant policy information before making decisions.
- Use customer-specific tools when additional data is required.
- Maintain conversation state using a `thread_id`.
- Stream intermediate and final responses to the frontend.
- Keep policy grounding separate from tool execution.

---

## Project Structure

```text
production-ai-app/
├── mcp_server.py       # Standalone FastMCP microservice (Port 8001)
├── agent_graph.py      # LangGraph state graph & Gemini initialization
├── rag_engine.py       # In-memory vector/policy search engine
├── main.py             # FastAPI gateway & SSE streaming handler (Port 8000)
├── frontend.py         # Streamlit chat interface (Port 8501)
├── requirements.txt    # Python dependencies
├── .env                # Local environment variables (do not commit)
└── README.md           # Project documentation
```

---

## Getting Started

### Prerequisites

Make sure the following are installed:

- Python 3.11+
- `pip`
- A valid Google AI Studio API key

You can obtain a Google AI Studio API key from:

https://aistudio.google.com/

> **Security:** Never commit your real API key to Git. Store secrets only in `.env` or a secure secrets manager.

---

## Environment Configuration

Create a `.env` file in the project root:

```ini
GOOGLE_API_KEY=your_gemini_api_key_here
MCP_SERVER_URL=http://localhost:8001/sse
PORT=8000
```

### Environment Variables

| Variable | Example | Description |
|---|---|---|
| `GOOGLE_API_KEY` | `your_gemini_api_key_here` | Google Gemini API key |
| `MCP_SERVER_URL` | `http://localhost:8001/sse` | FastMCP SSE endpoint |
| `PORT` | `8000` | FastAPI gateway port |

---

## Installation

### 1. Create a virtual environment

#### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

#### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install fastapi uvicorn streamlit langchain-google-genai langchain-mcp-adapters langgraph fastmcp python-dotenv
```

Alternatively, if `requirements.txt` is already configured:

```bash
pip install -r requirements.txt
```

---

## Running the Application

The full stack consists of three processes. Open **three separate terminals**, activate the virtual environment in each terminal, and run the following services.

### Terminal 1 — Start MCP Tool Server

```powershell
python mcp_server.py
```

Expected endpoint:

```text
http://localhost:8001/sse
```

The MCP service exposes tools such as:

```text
get_customer_details
```

---

### Terminal 2 — Start FastAPI Backend

```powershell
python main.py
```

Expected API endpoint:

```text
http://localhost:8000
```

FastAPI Swagger documentation:

```text
http://localhost:8000/docs
```

The gateway handles:

- Agent execution
- RAG retrieval
- Gemini requests
- MCP tool calls
- SSE streaming
- Rate-limit handling
- Session/thread state

---

### Terminal 3 — Start Streamlit Frontend

```powershell
streamlit run frontend.py
```

The Streamlit interface will normally be available at:

```text
http://localhost:8501
```

---

## Verification Test Cases

Use the Streamlit chat interface to validate the main agent capabilities.

| Test Case | Prompt | Expected Agent Action |
|---|---|---|
| **1. Policy Override** | `Can customer cust_101 bypass manual supervisor sign-off?` | Queries `get_customer_details`, identifies Sarah Connor as **Enterprise Level 4**, and applies the configured policy for an eligible override. |
| **2. Policy Enforcement** | `Can cust_102 make orders right now?` | Identifies Miles Dyson as **Suspended** and blocks order creation according to the configured accounts-receivable policy. |
| **3. Multi-Turn Memory** | `Why was his account suspended, and what tier was he on?` | Resolves the pronoun **"his"** using the existing `thread_id` conversation context. |
| **4. Missing Customer / No Hallucination** | `Check clearance for cust_999` | Handles the missing-record condition and reports that the customer does not exist instead of inventing customer information. |

> **Note:** The expected outcomes above assume the sample customer records and policy rules implemented in the project source code.

---

## Core Capabilities

### 1. Stateful Agent Conversations

Each conversation can be associated with a `thread_id`.

This allows the application to preserve conversation state across multiple requests during the lifetime of the configured checkpoint store.

Example:

```text
User:
Why is cust_102 restricted?

Agent:
cust_102 is suspended under the configured account policy.

User:
Why was his account suspended?

Agent:
"His" is resolved from the previous conversation context.
```

---

### 2. RAG Policy Grounding

The agent retrieves relevant policy information before taking action.

The current implementation uses an in-memory policy engine in:

```text
rag_engine.py
```

This provides a deterministic grounding layer between user requests and agent decisions.

The production roadmap includes migrating this layer to a persistent vector store such as:

- ChromaDB
- PGVector

---

### 3. MCP Tool Execution

The FastMCP service separates tool execution from the main agent gateway.

Example tool:

```text
get_customer_details
```

The architecture allows additional enterprise tools to be exposed independently without tightly coupling their implementation to the agent service.

---

### 4. Real-Time SSE Streaming

The FastAPI gateway streams agent events back to Streamlit using Server-Sent Events.

A typical flow is:

```text
FastAPI
   │
   ├── status event
   ├── retrieved policy
   ├── tool execution
   ├── token chunks
   └── [DONE]
          │
          ▼
      Streamlit UI
```

This provides a responsive user experience while the agent is executing.

---

## Error Handling & Resilience

### Rate-Limit Resilience

The Gemini client is configured with retries to handle transient quota/rate-limit errors.

The application uses:

```text
max_retries = 5
```

The FastAPI layer also catches Google API `429 RESOURCE_EXHAUSTED` conditions and can stream a friendly retry/countdown message instead of abruptly terminating the SSE connection.

> Exact retry behavior depends on the implementation in `agent_graph.py` and `main.py`.

---

### Polymorphic Stream Chunk Parsing

Streaming responses can contain different content structures.

The frontend includes an `extract_text_content()` helper that recursively extracts textual content from nested:

- strings
- lists
- dictionaries

This helps the UI remain compatible with different streaming event/chunk formats.

---

### SSE / Socket Protection

The backend handles client disconnects and streaming-related protocol errors such as `RemoteProtocolError`.

The application can close streams using a standardized completion event:

```text
[DONE]
```

This reduces the likelihood of unhandled exceptions when a browser/client disconnects during generation.

---

## API Overview

### `POST /chat/stream`

Primary streaming endpoint used by the Streamlit frontend.

Conceptually:

```text
Client
  │
  │ POST /chat/stream
  │
  ▼
FastAPI
  │
  ├── LangGraph
  ├── RAG
  ├── Gemini
  └── MCP
  │
  ▼
SSE event stream
```

The exact request and response schema should be treated as defined by the implementation in `main.py`.

### Interactive API Documentation

When the backend is running, open:

```text
http://localhost:8000/docs
```

---

## Configuration & Security

For local development:

```text
.env
```

should contain secrets and environment-specific configuration.

Recommended `.gitignore` entries:

```gitignore
.venv/
__pycache__/
*.pyc
.env
.env.*
!.env.example
```

For production deployments, use a dedicated secret-management solution rather than storing API keys directly in source control.

Examples include:

- Cloud secret managers
- Container platform secrets
- CI/CD secret stores
- Environment-level secret injection

---

## Production Roadmap

The following improvements are planned for a production deployment:

- [ ] **Persistent State**
  - Replace `MemorySaver` with `AsyncPostgresSaver` or `AsyncSqliteSaver`.

- [ ] **SQL Database Integration**
  - Connect `mcp_server.py` to PostgreSQL or SQLite.
  - Use SQLAlchemy for database access.

- [ ] **Persistent Vector Store**
  - Replace the static/in-memory policy list with ChromaDB or PGVector.

- [ ] **Human-in-the-Loop (HITL)**
  - Add LangGraph `interrupt()` approval gates before executing critical overrides.

- [ ] **Containerization**
  - Add `Dockerfile`.
  - Add `docker-compose.yml`.
  - Package the services for container-based deployment.

- [ ] **Cloud Deployment**
  - Deploy to platforms such as Azure Container Apps or AWS ECS.

- [ ] **Observability**
  - Add structured logging.
  - Add request tracing.
  - Track tool latency and LLM latency.
  - Add service health checks.

- [ ] **Authentication & Authorization**
  - Add API authentication.
  - Add role-based access control for sensitive support operations.

- [ ] **Persistent Customer Data**
  - Replace demo customer records with a production database.

---

## Recommended Production Architecture

For a production deployment, the architecture can evolve toward:

```text
                         ┌───────────────────────┐
                         │      Web / Client     │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │    API Gateway /      │
                         │    Load Balancer      │
                         └───────────┬───────────┘
                                     │
                         ┌───────────▼───────────┐
                         │   FastAPI Agent API   │
                         │                       │
                         │       LangGraph       │
                         └──────┬───────┬────────┘
                                │       │
                 ┌──────────────┘       └──────────────┐
                 ▼                                     ▼
        ┌──────────────────┐                 ┌──────────────────┐
        │   Vector Store   │                 │    MCP Server    │
        │ Chroma / PGVector│                 │ Enterprise Tools │
        └──────────────────┘                 └────────┬─────────┘
                                                      │
                                                      ▼
                                             ┌──────────────────┐
                                             │ SQL / Enterprise │
                                             │    Database      │
                                             └──────────────────┘

                         ┌───────────────────────┐
                         │ Google Gemini / LLM   │
                         └───────────────────────┘
```

---

## Development Guidelines

### Keep Services Decoupled

Each service should have a clear responsibility:

```text
frontend.py
    ↓
User interface

main.py
    ↓
API + streaming + orchestration entry point

agent_graph.py
    ↓
Agent workflow + LLM

rag_engine.py
    ↓
Policy retrieval / grounding

mcp_server.py
    ↓
Enterprise tool execution
```

Avoid placing database, UI, or tool-server logic directly inside the LangGraph workflow when it can remain isolated behind a service boundary.

---

## Troubleshooting

### MCP server is unavailable

Verify that Terminal 1 is running:

```powershell
python mcp_server.py
```

Then confirm:

```text
http://localhost:8001/sse
```

matches the value configured in `.env`.

---

### FastAPI is not reachable

Start the backend:

```powershell
python main.py
```

Then check:

```text
http://localhost:8000/docs
```

---

### Streamlit cannot connect to the backend

Make sure:

1. FastAPI is running.
2. The backend port is `8000`.
3. No firewall or local process is blocking the port.
4. The frontend is configured to call the correct backend endpoint.

---

### Gemini API errors

Check:

```ini
GOOGLE_API_KEY=your_gemini_api_key_here
```

Also verify that the key is valid and that the configured Gemini model is available to the project.

---

### Environment variables are not loading

Make sure:

- `.env` is located in the project root.
- `python-dotenv` is installed.
- The application loads environment variables before creating clients that depend on them.

---

## Example End-to-End Interaction

```text
User:
Can customer cust_101 bypass manual supervisor sign-off?

        │
        ▼

Streamlit
        │
        ▼

FastAPI /chat/stream
        │
        ▼

LangGraph
        │
        ├──► RAG: retrieve override policy
        │
        ├──► Gemini: determine required information
        │
        └──► MCP: get_customer_details("cust_101")
                    │
                    ▼
              Customer Record
                    │
                    ▼
              LangGraph Agent
                    │
                    ▼
             Policy-grounded answer
                    │
                    ▼
              SSE → Streamlit
```

---

## Project Goals

This project demonstrates how enterprise AI support systems can combine:

- Agentic workflows
- RAG-based policy grounding
- Stateful conversations
- MCP-based tool execution
- Microservice architecture
- Real-time SSE streaming
- LLM-powered reasoning
- Resilience and error handling

The architecture is intentionally modular so that individual components can be replaced or upgraded independently as the system moves from prototype to production.

---

## License

Add the appropriate license for your repository, for example:

```text
MIT License
```

If this project is private, proprietary, academic, or company-owned, replace the section above with the applicable licensing and usage terms.

---

## Author

**Mohd Inzamam**

Enterprise AI Agent Runtime & Support Copilot  
Built with Python, FastAPI, LangGraph, FastMCP, Streamlit, RAG, and Google Gemini.
