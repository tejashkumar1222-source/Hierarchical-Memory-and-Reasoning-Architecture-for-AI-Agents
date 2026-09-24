# Hierarchical Memory and Reasoning Architecture for AI Agents (HMRA)

A research prototype combining **3 Memory Scopes**, **3 Reasoning Levels**, **5 Specialized Agents**, **Central Orchestration**, a **Modular Tool Layer**, and an interactive ChatGPT/Gemini-style Web Dashboard.

---

## 1. Project Overview

**HMRA** is an agent architecture designed around existing Large Language Models (LLMs). 
> **Important Distinction:** This project is **not** a new foundational LLM, nor does it require model fine-tuning. Instead, it coordinates one underlying language model through role-specific reasoning levels, organizational memory scopes with strict access control, and verifiable execution tracing.

### Key Capabilities
- **Hierarchical Memory**: Global, Team, and Private memory boundaries.
- **Hierarchical Reasoning**: Slow Mind (Strategic), Fast Mind (Tactical), and Executor (Operational).
- **Multi-Agent Collaboration**: Five specialized roles (Researcher, Coder, Reviewer, Critic, Synthesizer).
- **8-Signal Retrieval**: Weighted scoring across semantic similarity, lexical overlap, recency, importance, confidence, access frequency, scope relevance, and source quality.
- **Memory Consolidation**: Deduplication, automatic merging, contradiction detection, and conflict clustering.
- **Controlled Knowledge Promotion**: Reviewer-gated graduation from `PRIVATE -> TEAM -> GLOBAL`.
- **Multi-Format Document Ingestion**: Ingests TXT, MD, CSV, JSON, and PDF files into chunked memory records.
- **Live Web Retrieval**: Safe external search via Brave Search API with graceful offline fallback.
- **Empirical Evaluation**: Benchmark comparisons against 4 baselines and 6 ablation configurations across 14 research categories.

---

## 2. Target Architecture

The HMRA system is composed of five clear architectural tiers:

```
+-------------------------------------------------------------------------+
|                           CENTRAL ORCHESTRATOR                          |
+------------------------------------+------------------------------------+
                                     |
              +----------------------+----------------------+
              |                                             |
+-------------v---------------+              +--------------v-------------+
|    3 REASONING LEVELS       |              |      3 MEMORY SCOPES       |
|                             |              |                            |
| 1. SLOW MIND (Strategic)    |              | 1. GLOBAL MEMORY           |
|    "WHAT should be done?"   |              |    Broadly verified facts  |
| 2. FAST MIND (Tactical)     |              | 2. TEAM MEMORY             |
|    "HOW should it be done?" |              |    Shared task context     |
| 3. EXECUTOR (Operational)   |              | 3. PRIVATE MEMORY          |
|    "DO it."                 |              |    Isolated agent scratch  |
+-------------+---------------+              +--------------+-------------+
              |                                             |
              +----------------------+----------------------+
                                     |
              +----------------------v----------------------+
              |            5 SPECIALIZED AGENTS             |
              |                                             |
              | 1. RESEARCHER  (Evidence & Search)          |
              | 2. CODER       (Technical Implementation)   |
              | 3. REVIEWER    (Quality Gate & Validation)  |
              | 4. CRITIC      (Objections & Contradictions)|
              | 5. SYNTHESIZER (Disagreement Resolution)    |
              +----------------------+----------------------+
                                     |
              +----------------------v----------------------+
              |              MODULAR TOOL LAYER             |
              | Calculator | Web Search | Documents | Memory|
              +---------------------------------------------+
```

---

## 3. Memory Hierarchy

| Memory Scope | Read Access | Write Access | Description & Use Cases |
| :--- | :--- | :--- | :--- |
| **GLOBAL** | All authorized agents | Promotion pipeline only | Broadly reusable organization knowledge, architectural standards, verified facts. |
| **TEAM** | Agents within the task team | Authorized team members | Ingested documents, sprint agreements, collective research findings. |
| **PRIVATE** | Owning agent only | Owning agent only | Transient scratchpad observations, code notes, critical reservations. Isolated from foreign agents. |

### Access Control Rules
Access control is enforced directly within backend retrieval (`can_read_memory`, `can_write_memory`):
- Private memories are completely invisible to other agents until promoted.
- Agents cannot write directly into `GLOBAL` scope; knowledge must be promoted through validation gates.

---

## 4. Reasoning Hierarchy

HMRA divides cognitive load into three distinct layers:

1. **Level 1 — Slow Mind (Strategic Reasoning)**
   - Answers: *"WHAT should be done?"*
   - Analyzes user intent, identifies constraints, estimates complexity, decomposes subgoals, and maps agent/tool requirements.
   - Does *not* perform low-level execution.

2. **Level 2 — Fast Mind (Tactical Reasoning)**
   - Answers: *"HOW should the plan be organized and adapted?"*
   - Sequences agent invocations, prioritizes goals, evaluates intermediate tool outputs, and performs local retries on tool errors without restarting the strategic plan.

3. **Level 3 — Executor (Operational Execution)**
   - Answers: *"DO it."*
   - Dispatches operational tools (math calculator, time, web search, document parsing, memory retrieval/write) and records latency telemetry.

---

## 5. Five Specialized Agents

Each agent has a dedicated system role and receives minimal structured context:

- **Researcher**: Gathers empirical evidence from memory and web search; attaches source provenance; stores private findings.
- **Coder**: Implements, explains, and debugs algorithms and code snippets.
- **Reviewer**: Serves as the quality gate; validates outputs against constraints; checks for missing requirements; approves/rejects memory promotions.
- **Critic**: Challenges unsupported assertions; identifies contradictions and hallucinations; flags weak evidence.
- **Synthesizer**: Integrates agent findings; resolves critical disagreements conservatively; outputs the final user response.

---

## 6. Central Orchestrator

The Orchestrator coordinates the end-to-end task lifecycle:
1. Receives user query and registers execution ID.
2. Retrieves scope-authorized memories using 8-signal scoring.
3. Invokes Slow Mind to generate the strategic plan.
4. Invokes Fast Mind to organize tactical execution steps.
5. Dispatches Executor for tool executions (web search, calculator, etc.).
6. Gathers structured outputs across Researcher, Coder, Reviewer, and Critic.
7. Dispatches Synthesizer to formulate the final answer.
8. Selectively writes back durable facts into Private memory and evaluates Team promotion.
9. Returns answer, agent summaries, and execution trace to the client.

---

## 7. Modular Tool Layer

The system includes a extensible `ToolRegistry` with schema validation and database execution logging:
1. **Calculator**: Safe Python AST-based mathematical evaluator (no unsafe `eval`).
2. **Current Time**: Real-time localized and UTC timestamp generation.
3. **Web Search**: Safe search integration via Brave Search API with SSRF protection (private IP blocking).
4. **Fetch Web Page**: Safe HTTP page text extraction.
5. **Document Ingestion**: Parser for TXT, MD, CSV, JSON, and PDF files.
6. **Memory Operations**: Structured retrieval, writing, and consolidation tools.

---

## 8. Multi-Signal Retrieval Engine

Memories are ranked using eight configurable signals:
$$\text{Score} = w_{\text{sem}} S_{\text{sem}} + w_{\text{lex}} S_{\text{lex}} + w_{\text{rec}} S_{\text{rec}} + w_{\text{imp}} S_{\text{imp}} + w_{\text{conf}} S_{\text{conf}} + w_{\text{freq}} S_{\text{freq}} + w_{\text{scope}} S_{\text{scope}} + w_{\text{qual}} S_{\text{qual}}$$

### Configurable Weights (`.env`):
- `W_SEMANTIC = 0.30` (Normalized term vector cosine similarity with lexical fallback)
- `W_LEXICAL = 0.10` (Jaccard keyword overlap)
- `W_RECENCY = 0.10` (Exponential decay: $e^{-\Delta t / 30}$)
- `W_IMPORTANCE = 0.15` (Subject matter priority)
- `W_CONFIDENCE = 0.15` (Fact verification confidence)
- `W_FREQUENCY = 0.05` (Access saturation: $1 - e^{-\text{count} / 5}$)
- `W_SCOPE = 0.10` (Private: 1.0, Team: 0.9, Global: 0.8)
- `W_SOURCE_QUALITY = 0.05` (Provenance credibility)

> **Performance:** Retrieval executes in $< 100\text{ ms}$ for stores below 10,000 entries on standard CPU.

---

## 9. Memory Consolidation & Conflict Management

- **Duplicate Detection**: Identifies records with similarity $\ge 0.85$, merges access counts, and links lineage.
- **Contradiction Detection**: Detects contrasting claims or polarity conflicts and registers them in the `conflicts` table.
- **Conflict Resolution**: Compares evidence deltas (confidence and source quality). If delta is decisive ($\ge 0.25$), it auto-resolves favoring the stronger record and marks the other `SUPERSEDED`. Otherwise, it preserves both records with `OPEN` status for human/agent review.

---

## 10. Controlled Memory Promotion

Graduation of knowledge follows a verified audit trail:
- **PRIVATE $\rightarrow$ TEAM**: Requires confidence $\ge 0.60$, importance $\ge 0.40$, and no unresolved conflicts.
- **TEAM $\rightarrow$ GLOBAL**: Requires confidence $\ge 0.75$, importance $\ge 0.60$, source quality $\ge 0.60$, and Reviewer approval.
- Demotions (e.g. `GLOBAL -> PRIVATE`) are strictly rejected.

---

## 11. Installation (Windows PowerShell)

### Prerequisites
- Windows 10/11
- Python 3.11+
- PowerShell 5.1 or PowerShell 7+

### Step-by-Step Setup
```powershell
# 1. Navigate to project root
cd c:\Users\karth\Downloads\HMRA_Live_project\HMRA_Live

# 2. Create Python virtual environment
py -m venv .venv

# 3. Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# 4. Install backend dependencies
python -m pip install -r backend\requirements.txt
```

---

## 12. Environment Configuration

Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```

Edit `.env` to configure your API keys:
```env
# Supported providers: groq, gemini, openai, openai_compatible
LLM_PROVIDER=groq
LLM_MODEL=openai/gpt-oss-20b
LLM_API_KEY=your_actual_api_key_here
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_TIMEOUT=60
LLM_TEMPERATURE=0.2

# Optional: Brave Web Search API Key (leave empty for graceful offline mode)
BRAVE_API_KEY=your_brave_api_key_here

# Database path
HMRA_DB_PATH=data/hmra.db
```

---

## 13. Running the System

Start the server using Python or PowerShell script:
```powershell
# Option A: Direct Python startup
python run.py

# Option B: Automated startup script
.\run_hmra.ps1
```

Access the web interface at:
**http://127.0.0.1:8000**

---

## 14. Document Ingestion

You can upload documents in two ways:
1. **Chat Composer `＋` Button**: Select any supported file (`.txt`, `.md`, `.csv`, `.json`, `.pdf`). It is immediately chunked and ingested into TEAM memory, followed by an inline chat notification.
2. **Document Memory Tab**: Allows choosing target scope (`GLOBAL`, `TEAM`, `PRIVATE`) and viewing chunking diagnostics.

---

## 15. Web Search Usage

- Click the **🌐 Web Search** toggle in the chat composer to turn on live web search.
- When enabled, Slow Mind and Fast Mind route the query to the `web_search` tool, Brave Search retrieves relevant results, and the Researcher cites them with provenance.
- If `BRAVE_API_KEY` is not set, the system gracefully continues offline without crashing.

---

## 16. Running Automated Tests

Run the complete test suite (37 automated tests across access control, reasoning, tools, and memory):
```powershell
.\.venv\Scripts\python -m pytest tests/ -v
```

---

## 17. Running Evaluation Benchmarks

Run the empirical evaluation comparing 4 Baselines and 6 Ablations across 14 research categories:
```powershell
# Run from terminal
.\.venv\Scripts\python -m backend.app.evaluation.runner
```
Or click **▶ Run Live Comparative Benchmark** directly in the **Evaluation** tab of the web dashboard.

---

## 18. Project Structure

```
HMRA_Live/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI endpoints & application bootstrap
│   │   ├── config.py            # Central environment & weights configuration
│   │   ├── db.py                # SQLite schema, WAL mode, migrations
│   │   ├── llm.py               # LLM client with adaptive 429 retry
│   │   ├── memory/              # 3-Scope Memory System
│   │   │   ├── models.py        # Pydantic schemas & enums
│   │   │   ├── access_control.py# Scope authorization rules
│   │   │   ├── store.py         # Persistent MemoryManager
│   │   │   ├── retrieval.py     # 8-Signal scoring engine
│   │   │   ├── lifecycle.py     # Status transitions & lineage
│   │   │   ├── consolidation.py # Deduplication & conflict detection
│   │   │   ├── promotion.py     # Private -> Team -> Global gates
│   │   │   └── conflicts.py     # Conflict group manager
│   │   ├── reasoning/           # 3 Reasoning Levels
│   │   │   ├── slow_mind.py     # Level 1: Strategic planner
│   │   │   ├── fast_mind.py     # Level 2: Tactical coordinator
│   │   │   └── executor.py      # Level 3: Operational tool runner
│   │   ├── agents/              # 5 Specialized Agents
│   │   │   ├── base.py          # Base agent & AgentMessage protocol
│   │   │   ├── researcher.py    # Researcher agent
│   │   │   ├── coder.py         # Coder agent
│   │   │   ├── reviewer.py      # Reviewer quality gate
│   │   │   ├── critic.py        # Critic skepticism agent
│   │   │   └── synthesizer.py   # Synthesizer integration agent
│   │   ├── orchestration/       # Central Orchestration
│   │   │   ├── orchestrator.py  # End-to-end task coordinator
│   │   │   ├── state.py         # Live agent telemetry
│   │   │   └── messages.py      # Trace & result models
│   │   ├── tools/               # Modular Tool Layer
│   │   │   ├── registry.py      # Tool discovery & logging
│   │   │   ├── calculator.py    # AST math evaluator
│   │   │   ├── current_time.py  # Local & UTC time
│   │   │   ├── web_search.py    # Brave Search & SSRF safety
│   │   │   ├── documents.py     # TXT, MD, CSV, JSON, PDF parser
│   │   │   └── memory_tools.py  # Internal memory wrappers
│   │   └── evaluation/          # Research Benchmark Suite
│   │       ├── dataset.py       # 14 benchmark test cases
│   │       ├── metrics.py       # Precision, recall, latency, accuracy
│   │       └── runner.py        # Baselines 1-4 & Ablations A-F runner
│   └── requirements.txt
├── frontend/
│   └── index.html               # ChatGPT/Gemini-style green-accented UI
├── tests/                       # 37 Automated pytest test files
├── data/
│   ├── hmra.db                  # Persistent SQLite database
│   └── uploads/                 # Stored document files
├── .env.example
├── run.py                       # Uvicorn entrypoint
├── run_hmra.ps1                 # PowerShell startup script
└── README.md                    # Comprehensive documentation
```

---

## 19. Troubleshooting

- **SQLite Database Locked**: HMRA enables SQLite WAL mode (`PRAGMA journal_mode=WAL`) and a 30-second busy timeout. If locked, ensure no external database browser holds exclusive file locks.
- **LLM 429 Rate Limits**: Groq on-demand models have per-minute token limits. HMRA incorporates adaptive backoff that extracts exact millisecond retry times from the API error payload and compacts inter-agent contexts.
- **Web Search Offline**: If `BRAVE_API_KEY` is not set, HMRA will clearly display `"Web search is not configured"` and continue running in offline research mode.

---

## 20. Research Positioning & Limitations

### Positioning in Existing Literature
HMRA builds upon and synthesizes concepts from:
- **Cognitive Agent Architectures**: CoALA, MemoryBank, Generative Agents.
- **Externalized Memory**: MemGPT, Mem0, MemoryOS, HippoRAG.
- **Multi-Agent Collaboration**: MetaGPT, AutoGen, ChatDev, CAMEL.

HMRA's contribution lies in the combined integration of:
1. Multi-tenant organizational memory scopes (`GLOBAL`, `TEAM`, `PRIVATE`) with backend access control.
2. 8-signal scoring for Explainable Memory Retrieval.
3. Reviewer-gated knowledge promotion.
4. Tri-level cognitive reasoning (Slow Mind $\rightarrow$ Fast Mind $\rightarrow$ Executor) coordinating specialized agents.

### Limitations
- **Single Underlying Model**: All 5 agents use one underlying LLM instance with distinct system prompts and context boundaries.
- **Local Vectors**: Local embeddings use normalized subword term vectors for sub-50ms CPU latency without external vector database dependencies.
