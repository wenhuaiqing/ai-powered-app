# ai-powered-app

A portfolio demo mocking Reapit's "One Platform" — built around Sydney house-price Kaggle data.

Showcases: multi-agent LLM orchestration (LangGraph), retrieval-augmented compliance Q&A (NSW regulations), text-to-DuckDB, live web search (Tavily), and a RandomForest valuation model — all behind a Reapit-themed React UI with a global agent orb.

## Run locally

```powershell
# Build data + model artefacts
cd backend
uv sync
uv run python ../scripts/build_db.py
uv run python ../scripts/train_model.py
uv run python ../scripts/build_review_embeddings.py
uv run python ../scripts/build_regulation_corpus.py

# Backend
uv run uvicorn src.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

See `CLAUDE.md` for layout + conventions, and `C:\Users\Owen.Wen\.claude\plans\under-misc-folder-each-quiet-starfish.md` for the design rationale.
