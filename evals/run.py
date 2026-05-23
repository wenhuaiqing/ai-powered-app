"""Tier 2 / Tier 3 eval runner.

Usage from the repo root:
    uv run python evals/run.py --tier smoke           # tier3 cases, no LLM judge
    uv run python evals/run.py --tier full            # all cases + LLM judge
    uv run python evals/run.py --tier smoke --filter compliance
    uv run python evals/run.py --backend http://localhost:8000

Hits the running backend's /orb/chat SSE endpoint with each case prompt,
captures the planner decision + node events + final message, then runs
the tier's assertions.

Tier 3 (smoke):
  - planner picked the expected_agents set (exact set match)
  - SSE produced node_start/node_end for each chosen agent
  - no node_error events for chosen agents
  - final_message event fired
  - expected_facts appear in the final answer (case-insensitive substring)
  - anti_facts do NOT appear
  Result: pass/fail. Exit code reflects overall pass rate.

Tier 2 (full):
  - everything in tier 3
  - plus an LLM-judge verdict on fact_coverage / citation_accuracy /
    helpfulness, each 1-5.
  Result: a results JSON written to evals/results/ with timestamps,
  exit code reflects overall pass rate.
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx
import yaml
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
CASES_DIR = Path(__file__).resolve().parent / "cases"
RESULTS_DIR = Path(__file__).resolve().parent / "results"
DEFAULT_BACKEND = "http://localhost:8000"
END_TO_END_TIMEOUT = 120.0   # generous — Tavily-backed runs can take ~30s

# Load .env from repo root so AZURE_OPENAI_* picks up for the judge.
load_dotenv(REPO_ROOT / ".env")

REQUIRED_FIELDS = {"id", "prompt", "expected_agents"}


# ---------------------------------------------------------------------------
# Case loading
# ---------------------------------------------------------------------------

def load_cases(filter_substr: str | None = None, tier: str = "smoke") -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for path in sorted(CASES_DIR.glob("*.yml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            print(f"  ! failed to parse {path.name}: {exc}", file=sys.stderr)
            continue
        if not isinstance(data, dict):
            continue
        missing = REQUIRED_FIELDS - data.keys()
        if missing:
            print(f"  ! {path.name} missing required fields: {missing}", file=sys.stderr)
            continue
        if tier == "smoke" and not data.get("tier3"):
            continue
        if filter_substr and filter_substr not in data["id"]:
            continue
        data.setdefault("expected_facts", [])
        data.setdefault("anti_facts", [])
        data.setdefault("page_context", {"module": "dashboard", "current_item": None})
        cases.append(data)
    return cases


# ---------------------------------------------------------------------------
# SSE consumer — POST + drain
# ---------------------------------------------------------------------------

def _parse_sse_block(raw: str) -> dict[str, Any] | None:
    event = "message"
    data_lines: list[str] = []
    for line in raw.splitlines():
        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            event = line[len("event:"):].strip()
        elif line.startswith("data:"):
            data_lines.append(line[len("data:"):].strip())
    payload = "\n".join(data_lines)
    if not payload and event == "message":
        return None
    try:
        data = json.loads(payload) if payload else None
    except json.JSONDecodeError:
        data = payload
    return {"event": event, "data": data}


def run_case(case: dict[str, Any], backend: str) -> dict[str, Any]:
    """POST to /orb/chat and drain SSE. Returns a flat dict of trace facts."""
    started = time.time()
    body = {"message": case["prompt"], "page_context": case["page_context"]}

    events: list[dict[str, Any]] = []
    planner_decision: dict[str, Any] | None = None
    final_message: str | None = None
    final_data: dict[str, Any] | None = None
    node_starts: set[str] = set()
    node_ends: set[str] = set()
    node_errors: list[dict[str, Any]] = []
    all_citations: list[dict[str, Any]] = []

    try:
        with httpx.stream(
            "POST",
            f"{backend}/orb/chat",
            json=body,
            timeout=END_TO_END_TIMEOUT,
            headers={"Accept": "text/event-stream"},
        ) as r:
            if r.status_code >= 400:
                return {
                    "id": case["id"],
                    "error": f"HTTP {r.status_code}: {r.read()[:200]!r}",
                    "duration_s": round(time.time() - started, 2),
                    "events_count": 0,
                }
            buffer = ""
            for chunk in r.iter_text():
                buffer += chunk.replace("\r\n", "\n")
                while "\n\n" in buffer:
                    raw, _, buffer = buffer.partition("\n\n")
                    evt = _parse_sse_block(raw)
                    if not evt:
                        continue
                    events.append(evt)
                    name = evt["event"]
                    payload = evt["data"] or {}
                    if name == "planner_decision":
                        planner_decision = payload
                    elif name == "node_start":
                        node_starts.add(payload.get("name", ""))
                    elif name == "node_end":
                        node_ends.add(payload.get("name", ""))
                        # Drain citations / final-shaped data per node
                        result = payload.get("result") or {}
                        for c in result.get("citations") or []:
                            all_citations.append(c)
                        for h in result.get("hits") or []:
                            all_citations.append({**h, "source": h.get("title", h.get("url"))})
                    elif name == "node_error":
                        node_errors.append(payload)
                    elif name == "final_message":
                        final_data = payload
                        final_message = payload.get("message")
                    elif name == "done":
                        break
    except httpx.HTTPError as exc:
        return {
            "id": case["id"],
            "error": f"transport error: {exc}",
            "duration_s": round(time.time() - started, 2),
            "events_count": len(events),
        }

    chosen_agents = sorted({c.get("name") for c in (planner_decision or {}).get("agents_to_call") or [] if c.get("name")})
    return {
        "id":               case["id"],
        "prompt":           case["prompt"],
        "expected_agents":  sorted(case["expected_agents"]),
        "chosen_agents":    chosen_agents,
        "node_starts":      sorted(node_starts),
        "node_ends":        sorted(node_ends),
        "node_errors":      node_errors,
        "final_message":    final_message,
        "final_data":       final_data,
        "citations":        all_citations,
        "duration_s":       round(time.time() - started, 2),
        "events_count":     len(events),
    }


# ---------------------------------------------------------------------------
# Tier 3 assertions
# ---------------------------------------------------------------------------

def smoke_assertions(case: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []

    if result.get("error"):
        failures.append(f"transport: {result['error']}")
        return {"passed": False, "failures": failures, "checks": {}}

    expected = set(case["expected_agents"])
    chosen = set(result["chosen_agents"])
    routing_ok = expected.issubset(chosen)
    if not routing_ok:
        missing = expected - chosen
        failures.append(f"routing: missing agents {sorted(missing)} (got {sorted(chosen)})")

    nodes_done = set(result["node_ends"])
    missing_ends = expected - nodes_done
    if missing_ends:
        failures.append(f"events: no node_end for {sorted(missing_ends)}")

    relevant_errors = [e for e in result["node_errors"] if e.get("name") in expected]
    if relevant_errors:
        failures.append(f"errors: {[e.get('name') for e in relevant_errors]}")

    final_lower = (result.get("final_message") or "").lower()
    citation_haystack = " ".join(
        (c.get("snippet") or c.get("body") or "") for c in result.get("citations") or []
    ).lower()
    haystack = final_lower + " " + citation_haystack

    missing_facts = [f for f in case["expected_facts"] if f.lower() not in haystack]
    if missing_facts:
        failures.append(f"facts missing: {missing_facts}")

    hit_anti = [a for a in case["anti_facts"] if a.lower() in haystack]
    if hit_anti:
        failures.append(f"anti-facts hit: {hit_anti}")

    return {
        "passed": not failures,
        "failures": failures,
        "checks": {
            "routing": routing_ok,
            "missing_node_ends": sorted(missing_ends),
            "node_errors": [e.get("name") for e in relevant_errors],
            "facts_present": [f for f in case["expected_facts"] if f.lower() in haystack],
            "facts_missing": missing_facts,
            "anti_facts_hit": hit_anti,
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

ANSI = {
    "ok":   "\x1b[32m",
    "bad":  "\x1b[31m",
    "dim":  "\x1b[90m",
    "off":  "\x1b[0m",
}

def colour(s: str, name: str) -> str:
    if sys.stdout.isatty():
        return f"{ANSI[name]}{s}{ANSI['off']}"
    return s


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tier", choices=["smoke", "full"], default="smoke")
    parser.add_argument("--filter", default=None, help="case-id substring filter")
    parser.add_argument("--backend", default=DEFAULT_BACKEND)
    parser.add_argument("--out", default=None, help="results JSON path; defaults to evals/results/<timestamp>.json")
    args = parser.parse_args()

    cases = load_cases(filter_substr=args.filter, tier=args.tier)
    if not cases:
        print(f"No cases matched (tier={args.tier}, filter={args.filter!r}).")
        return 0

    print(f"=== Tier {2 if args.tier == 'full' else 3} evaluation ===")
    print(f"Loaded {len(cases)} case{'' if len(cases) == 1 else 's'} from {CASES_DIR}")
    print(f"Backend: {args.backend}")
    print()

    summary = []
    for case in cases:
        result = run_case(case, args.backend)
        smoke = smoke_assertions(case, result)
        row: dict[str, Any] = {
            "case_id":   case["id"],
            "duration":  result.get("duration_s"),
            "events":    result.get("events_count"),
            "passed":    smoke["passed"],
            "failures":  smoke["failures"],
            "checks":    smoke["checks"],
            "chosen_agents": result.get("chosen_agents"),
            "expected_agents": result.get("expected_agents"),
            "final_message_preview": (result.get("final_message") or "")[:280],
        }
        if args.tier == "full":
            from evals.judge import judge_case
            verdict = judge_case(case, result)
            if verdict:
                row["judge"] = verdict.model_dump()
                row["judge"]["total"] = round(verdict.total, 2)

        summary.append(row)

        status = colour("OK  ", "ok") if smoke["passed"] else colour("FAIL", "bad")
        suffix = ""
        if "judge" in row:
            suffix = f" · judge {row['judge']['total']}/5"
        print(f"[{status}] {case['id']:<42} {result.get('duration_s', '—')}s · {result.get('events_count', 0)} events{suffix}")
        for f in smoke["failures"]:
            print(f"        {colour(f, 'bad')}")

    passed = sum(1 for r in summary if r["passed"])
    total = len(summary)
    print()
    print(f"Summary: {colour(f'{passed}/{total} passed', 'ok' if passed == total else 'bad')}")

    # Write results JSON
    if args.out:
        out_path = Path(args.out)
    else:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        out_path = RESULTS_DIR / f"{args.tier}-{stamp}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "tier": args.tier,
        "backend": args.backend,
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "summary": {"passed": passed, "total": total, "pass_rate": round(passed / max(total, 1), 3)},
        "cases": summary,
    }, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out_path.relative_to(REPO_ROOT)}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
