"""Property Matcher — composes Data Query + Reviews RAG + Valuation.

Takes buyer/tenant requirements (from a lead in the Pipeline drawer or
extracted by the planner from a free-text prompt) and returns a ranked list
of candidate suburbs with predicted prices and lifestyle rationale.

Composition rather than just hitting one tool is the demo value here — the
trace shows three tool calls fanning out from a single agent.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from src.app.services.agents.runtime import emit
from src.app.services.agents.schemas import Candidate, GraphState, MatcherResult
from src.app.services.duckdb_client import fetch_rows
from src.app.services.model import predict_with_contributions
from src.app.services.rag.reviews import retrieve as reviews_retrieve

log = logging.getLogger(__name__)

DEFAULT_MAX_PRICE = 1_500_000
DEFAULT_MIN_BED = 2
DEFAULT_MAX_KM = 30
TOP_N = 5


def _extract_requirements(state: GraphState, inputs: dict[str, Any]) -> dict[str, Any]:
    """Best-effort extraction. Planner inputs win, then page_context.current_item, then regex."""
    req: dict[str, Any] = {}

    if state.page_context.current_item:
        lead = state.page_context.current_item
        if "min_bed" in lead:
            req["min_bed"] = int(lead["min_bed"])
        if "budget_max" in lead:
            req["max_price"] = float(lead["budget_max"])
        if "max_km_from_cbd" in lead:
            req["max_km_from_cbd"] = float(lead["max_km_from_cbd"])
        if "preferred_suburb" in lead and lead["preferred_suburb"]:
            req["preferred_suburb"] = str(lead["preferred_suburb"])
        if "notes" in lead and lead["notes"]:
            req["lifestyle"] = str(lead["notes"])

    if inputs:
        for key in ("min_bed", "max_price", "max_km_from_cbd", "preferred_suburb", "lifestyle"):
            if inputs.get(key) not in (None, ""):
                req[key] = inputs[key]

    # Regex fallbacks from the user prompt
    msg = state.user_message or ""
    if "min_bed" not in req:
        m = re.search(r"(\d+)\s*[- ]*bed", msg, re.IGNORECASE)
        if m:
            req["min_bed"] = int(m.group(1))
    if "max_price" not in req:
        m = re.search(r"\$?\s*(\d+(?:\.\d+)?)\s*(m|M|million)", msg)
        if m:
            req["max_price"] = float(m.group(1)) * 1_000_000
        else:
            m = re.search(r"under\s+\$?\s*(\d{3,})k", msg, re.IGNORECASE)
            if m:
                req["max_price"] = float(m.group(1)) * 1_000
    if "max_km_from_cbd" not in req:
        m = re.search(r"within\s+(\d+)\s*km", msg, re.IGNORECASE)
        if m:
            req["max_km_from_cbd"] = float(m.group(1))
    if "lifestyle" not in req:
        req["lifestyle"] = msg

    req.setdefault("min_bed", DEFAULT_MIN_BED)
    req.setdefault("max_price", DEFAULT_MAX_PRICE)
    req.setdefault("max_km_from_cbd", DEFAULT_MAX_KM)
    return req


def _filter_properties(req: dict[str, Any]) -> list[dict[str, Any]]:
    sql = """
        SELECT suburb,
               MEDIAN(price)        AS median_price,
               MEDIAN(km_from_cbd)  AS median_km,
               MEDIAN(num_bed)      AS median_bed,
               COUNT(*)             AS n_sales,
               ANY_VALUE(suburb_lat) AS suburb_lat,
               ANY_VALUE(suburb_lng) AS suburb_lng
        FROM properties
        WHERE num_bed >= ?
          AND price BETWEEN ? AND ?
          AND km_from_cbd <= ?
        GROUP BY suburb
        HAVING COUNT(*) >= 3
        ORDER BY n_sales DESC
        LIMIT 40
    """
    params = [
        int(req["min_bed"]),
        50_000,                  # arbitrary floor to exclude data errors
        float(req["max_price"]),
        float(req["max_km_from_cbd"]),
    ]
    cols, rows = fetch_rows(sql, params)
    return [dict(zip(cols, r)) for r in rows]


async def run(state: GraphState, inputs: dict[str, Any]) -> MatcherResult:
    req = _extract_requirements(state, inputs)
    await emit("tool_call", {"node": "matcher", "tool": "duckdb_filter", "args": req})

    candidates_raw = _filter_properties(req)
    await emit("tool_result", {
        "node": "matcher",
        "tool": "duckdb_filter",
        "preview": f"{len(candidates_raw)} suburb(s) matched the budget+distance+bed filter",
    })

    # Suburb-level lifestyle ranking via reviews RAG
    lifestyle_query = str(req.get("lifestyle") or state.user_message)
    await emit("tool_call", {"node": "matcher", "tool": "reviews_retrieve",
                              "args": {"query": lifestyle_query, "k": 10}})
    suburb_hits = reviews_retrieve(lifestyle_query, k=10)
    suburb_scores = {h.name.lower(): h for h in suburb_hits}
    await emit("tool_result", {
        "node": "matcher",
        "tool": "reviews_retrieve",
        "preview": f"{len(suburb_hits)} suburb card(s) ranked by lifestyle fit",
    })

    # Score + select top N candidates
    scored: list[tuple[float, dict[str, Any]]] = []
    for cand in candidates_raw:
        suburb_key = str(cand["suburb"]).lower()
        lifestyle = suburb_scores.get(suburb_key)
        score = lifestyle.score if lifestyle else 0.0
        scored.append((score, cand))
    scored.sort(key=lambda kv: kv[0], reverse=True)
    top = [c for s, c in scored[:TOP_N]] or candidates_raw[:TOP_N]

    # Predict price per candidate (median bed/bath/parking from properties)
    out_candidates: list[Candidate] = []
    for cand in top:
        suburb = cand["suburb"]
        try:
            valuation = predict_with_contributions({
                "suburb": suburb,
                "num_bed": int(req["min_bed"]),
                "num_bath": max(1, int(req["min_bed"]) - 1),
                "num_parking": 1,
                "property_size": 500,
                "type": "House",
            })
            predicted = float(valuation.predicted_price)
        except Exception as exc:  # noqa: BLE001
            log.warning("valuation failed for %s: %s", suburb, exc)
            predicted = float(cand.get("median_price") or 0.0)

        lifestyle = suburb_scores.get(str(suburb).lower())
        rationale_bits = []
        if lifestyle:
            if lifestyle.family_friendliness:
                rationale_bits.append(f"family {lifestyle.family_friendliness:.0f}/10")
            if lifestyle.safety:
                rationale_bits.append(f"safety {lifestyle.safety:.0f}/10")
            if lifestyle.public_transport:
                rationale_bits.append(f"transport {lifestyle.public_transport:.0f}/10")
            if lifestyle.time_to_cbd_pt_min:
                rationale_bits.append(f"{lifestyle.time_to_cbd_pt_min:.0f} min to CBD")
        else:
            rationale_bits.append(f"{cand.get('n_sales', 0)} recent sales")
        rationale_bits.append(f"~{cand.get('median_km', 0):.0f} km from CBD")

        out_candidates.append(Candidate(
            suburb=str(suburb),
            sample_address=None,
            predicted_price=round(predicted, 2),
            lifestyle_score=(lifestyle.score if lifestyle else None),
            rationale="; ".join(rationale_bits),
        ))

    await emit("tool_call", {"node": "matcher", "tool": "predict_price",
                              "args": {"candidates": len(out_candidates)}})
    await emit("tool_result", {"node": "matcher", "tool": "predict_price",
                                "preview": f"valued {len(out_candidates)} candidate suburb(s)"})

    summary = (
        f"Filtered to {len(candidates_raw)} suburb(s) with ≥{int(req['min_bed'])} bed, "
        f"≤${int(req['max_price']):,}, within {int(req['max_km_from_cbd'])} km of CBD; "
        f"ranked top {len(out_candidates)} by lifestyle fit."
    )
    return MatcherResult(filter_summary=summary, candidates=out_candidates)
