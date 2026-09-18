# CircuitMind

> **An AI-powered electronics assistant that generates, explains, diagnoses, and exports simple circuits — through a single conversational gateway.**

---

## What it does

CircuitMind is a FastAPI service (plus a Streamlit UI) that turns a plain-English request like *"make me a LED circuit"* into a structured circuit description, and can then explain it in plain English, check it for common electrical mistakes, export it to SPICE/SVG/gate-JSON, or give a hint on a separate digital-logic gate-builder problem — all through one chat-style endpoint, `/chat`.

It is **not** a fine-tuned domain-specific model. Circuit generation is done by an LLM call to Groq's hosted `llama-3.3-70b-versatile`, constrained to a fixed vocabulary of ~30 component types, with a deterministic keyword-matching fallback for when the LLM is unavailable. Explaining and diagnosing are done with a hand-curated component knowledge base and a set of rule-based checks — not machine learning. Routing between these actions is handled by a **LangChain tool-calling agent**, not by separate REST routes.

---

## ⚙️ Architecture

### The gateway

Previously this was six separate REST routes (`/generate`, `/explain`, `/diagnose`, `/export`, `/hint`, `/generate-and-explain`), each stateless — callers had to hold the circuit JSON themselves and re-send it on every call. That's now collapsed into one route:
'''
POST /chat  { "session_id": "...", "message": "..." }
→ { "reply": "...", "circuit": {...} | null }
'''
A LangChain tool-calling agent (`agent/executor.py`) decides which of five tools to call based on the message and the session's existing state:

| Tool | Wraps | Operates on |

|---|---|---|
| `generate_circuit_tool` | `generate/generate.py` | the user's prompt — writes the result into session state |
| `explain_circuit_tool` | `explain/explain_module.py` | the session's current circuit (no argument needed) |
| `diagnose_circuit_tool` | `diagnose/diagnose_module.py` | the session's current circuit (no argument needed) |
| `export_circuit_tool` | `export/export_module.py` | the session's current circuit + `export_format` |
| `generate_hint_tool` | `hint/hint_module.py` | its own gate/wire graph payload — independent of "the circuit" |

### Statefulness

Two things persist per `session_id`, via `agent/session_store.py`:

- **Chat history** — `ChatMessageHistory`, threaded through the agent by `RunnableWithMessageHistory`
- **The current circuit** — a plain dict, read/written by the tools via `RunnableConfig` injection, so the LLM never has to re-type a full circuit JSON as a tool argument

Both are in-process dicts today — they reset on restart and aren't shared across multiple workers (the Dockerfile runs `--workers 2`). For multi-worker/production use, swap them for Redis-backed equivalents (`langchain_community`'s `RedisChatMessageHistory` for history; a Redis hash for the circuit store), using the Redis connection already provisioned via `RATE_LIMIT_REDIS_URL`.

### Module split

Each of `generate/` and `hint/` is split into three files:

| File | Purpose |

|---|---|
| `<module>.py` | Public entry point — thin orchestrator: try LLM, fall back to rules |
| `llm_<module>.py` | The Groq-calling logic |
| `rule_<module>.py` (or `rule_templates.py`) | The deterministic fallback |

`explain/`, `diagnose/`, and `export/` are unchanged — they're pure, rule-based, and have no LLM dependency, so nothing about the LangChain migration touches them.

---

## 🗂️ Project Structure

CircuitMind/
├── agent/                       # the gateway layer
│   ├── tools.py                 # LangChain tools wrapping generate/explain/diagnose/export/hint
│   ├── llm.py                   # ChatGroq instance
│   ├── prompt.py                # system prompt for the gateway agent
│   ├── executor.py              # tool-calling agent + RunnableWithMessageHistory
│   └── session_store.py         # per-session chat history + current circuit
├── api/app.py                   # single /chat route (+ /chat/reset, /health)
├── generate/                    # generate.py (orchestrator) + llm_generate.py + rule_templates.py
├── explain/explain_module.py
├── diagnose/diagnose_module.py
├── export/export_module.py
├── hint/                        # hint_module.py (orchestrator) + llm_hint.py + rule_hint.py
├── utils/component_resolver.py  # shared component knowledge base
├── cv_module/                   # experimental, NOT wired into the API
├── tests/
│   ├── test_all_modules.py      # generate/explain/diagnose/export/hint, pure-function level
│   └── test_agent.py            # tool-layer tests (session state, no live LLM calls)
├── app_streamlit.py             # single chat UI, replaces the old 5-tab layout
├── settings.py                  # centralized config, reads .env via pydantic-settings
├── Dockerfile / docker-compose.yml
├── requirements.txt
└── .env.example

---

## 📦 Installation

### Requirements

- Python 3.10+
- A free [Groq API key](https://console.groq.com)

### Setup

```bash
# clone project
git clone https://github.com/QuantumLogicsLabs/CircuitMind.git

# move into project
cd CircuitMind

#create virtual environment
python3 -m venv .venv

# activate the virtual environment
source .venv/bin/activate
# install dependencies
pip install -r requirements.txt

cp .env.example .env

# then edit .env and set GROQ_API_KEY
```

### Run the API

```bash
uvicorn api.app:app --reload
# Interactive docs: http://localhost:8000/docs
```

### Run the Streamlit UI

```bash
streamlit run app_streamlit.py
```

### Run both together (Docker Compose)

```bash
docker-compose up --build
# API:       http://localhost:8000
# Streamlit: http://localhost:8501
```

---

## 🚀 REST API

| Method | Endpoint | Description |

|---|---|---|
| GET | `/health` | Health check |
| POST | `/chat` | Send a message for this session; the agent routes it to the right action(s) |
| POST | `/chat/reset` | Clear a session's chat history and current circuit |

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "abc123", "message": "make me a LED circuit"}'

curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "abc123", "message": "now check it for issues"}'
```

Requests are rate-limited per-IP via `slowapi` (`chat_rate_limit`, default 10/min — see `settings.py`) and, if `CIRCUITMIND_API_KEY` is set, require an `X-API-Key` header.

---

## 🔑 Environment Variables

| Variable | Required | Purpose |

|---|---|---|
| `GROQ_API_KEY` | Yes | Without it, generate/hint fall back to their rule-based paths |
| `CIRCUITMIND_API_KEY` | No | If set, locks `/chat` behind an `X-API-Key` header; unset = open access |
| `ALLOWED_ORIGINS` | No | Comma-separated CORS allow-list |
| `RATE_LIMIT_REDIS_URL` | No | Redis connection string so rate limits (and, once migrated, session state) hold across workers/instances |
| `LANGCHAIN_TRACING_V2` / `LANGCHAIN_API_KEY` / `LANGCHAIN_PROJECT` | No | Optional LangSmith tracing for the gateway agent |

---

## 🧪 Testing

```bash
pytest tests/
```

`test_all_modules.py` covers generate/explain/diagnose/export/hint as pure functions. `test_agent.py` covers the tool layer directly — session isolation, error handling with no circuit in context — without making live LLM calls (full agent routing accuracy needs a live Groq call and isn't covered by the automated suite).

---

## ⚠️ Known Limitations

- Session state (`agent/session_store.py`) is in-process — resets on restart, not shared across multiple uvicorn workers. Fine for single-worker/dev; needs a Redis-backed swap for production multi-worker deployments.
- Generation quality is bounded by the LLM prompt and by the hardcoded fallback templates in `rule_templates.py` — no trained, domain-specific circuit model, no SPICE simulation to validate generated circuits.
- The component knowledge base (`utils/component_resolver.py`) covers ~30 common component types; anything outside it is treated as "unknown" by explain/diagnose.
- **`cv_module/`** (image → circuit JSON via YOLO object detection) is an unfinished, standalone experiment, not imported or exposed by `api/app.py`.
- `app_streamlit.py` and this gateway both call the LangChain agent **in-process** (monolithic architecture, same as before the migration) — there is no HTTP hop between them.

CircuitMind is **proprietary software** — see [`LICENSE`](LICENSE) for the full terms.

---

*CircuitMind — a practical circuit assistant, not a research model.*
