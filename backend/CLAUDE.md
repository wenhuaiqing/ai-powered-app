# Backend conventions

FastAPI app. Python 3.12, uv-managed.

## Layout

```
backend/
├── pyproject.toml
├── src/
│   ├── main.py                  FastAPI app + route registration + CORS
│   ├── settings.py              Env loading via pydantic-settings
│   └── app/
│       ├── routers/             One file per page-endpoint group (thin handlers)
│       └── services/
│           ├── duckdb_client.py   get_conn() + fetch_rows()
│           ├── ai_client.py       Azure OpenAI client (lru_cached)
│           ├── model.py           Trained RandomForest loader
│           ├── sql_validator.py   DuckDB SELECT-only + allowlist
│           ├── rag/               regulations + reviews retrieval
│           ├── tools/             Tool wrappers (web_search, etc.)
│           └── agents/            LangGraph nodes + graph + planner + summariser
└── tests/
    └── agents/                  Tier-1 shape tests per node
```

## Patterns

- **Thin routers** — handler ≤20 lines. SQL + business logic in `services/`.
- **Structured outputs** — every agent returns a Pydantic model via OpenAI `response_format`. Never free text into graph state.
- **DuckDB query rule** — never f-string user input into SQL. Use parameter binding or run through `sql_validator` for LLM-generated SQL.
- **SSE streaming** — agent endpoints use `sse-starlette`. Event types: `planner_decision`, `node_start`, `tool_call`, `tool_result`, `node_end`, `node_error`, `final_message`.
- **Per-node policy** — 30s timeout, 1 retry on ValidationError, append `NodeError` and continue on second failure.
- **Australian English** in user-facing strings.

## Testing

```powershell
cd backend
uv run pytest                    # all tests
uv run pytest tests/agents -v   # agent shape tests only
```
