"""Listing Drafter — generates listing copy from property attributes.

Pure LLM, no tools. Uses OpenAI structured outputs to return a ListingDraft
directly. Inputs come from the planner (extracted from prompt) or from a
Properties drawer button that passes the property in page_context.
"""

from __future__ import annotations

import logging
from typing import Any

from src.app.services.agents.runtime import emit
from src.app.services.agents.schemas import GraphState, ListingDraft
from src.app.services.llm import chat_structured
from src.settings import settings

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a senior NSW real estate copywriter. Draft a listing description for
the supplied property attributes.

Rules:
- Australian English, no emojis.
- Headline ≤ 90 characters, evocative but not breathless.
- Body markdown: 2-3 short paragraphs (~120 words total). Lead with the
  strongest selling point.
- key_features: 4-7 concise bullet items (e.g. "Renovated kitchen",
  "5 minutes to ferry").
- Do not invent facts. If a number isn't supplied (e.g. land size), avoid
  citing it. Do not guarantee returns or yields.
- suggested_price_range: only include if the inputs include enough to be
  defensible (e.g. predicted_price or a comparable). Otherwise leave null.

Return strict JSON matching the ListingDraft schema.
"""


def _resolve_inputs(state: GraphState, inputs: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if state.page_context.current_item:
        out.update(state.page_context.current_item)
    out.update(inputs or {})
    return out


def _fallback_draft(attrs: dict[str, Any]) -> ListingDraft:
    suburb = attrs.get("suburb") or "this Sydney suburb"
    bed = attrs.get("num_bed") or "well-proportioned"
    bath = attrs.get("num_bath") or "modern"
    type_ = (attrs.get("type") or "Home").title()
    headline = f"Inviting {bed}-bedroom {type_.lower()} in {suburb}"
    body = (
        f"A comfortable {bed}-bedroom, {bath}-bathroom {type_.lower()} situated in "
        f"sought-after {suburb}. Designed for easy family living, with light-filled "
        "interiors and a layout that flows naturally between the kitchen, living and "
        "outdoor spaces.\n\n"
        "Close to local schools, shops, and transport. A solid opportunity for "
        "owner-occupiers and investors alike."
    )
    return ListingDraft(
        headline=headline,
        body_markdown=body,
        key_features=[
            f"{bed} bedrooms" if isinstance(bed, int) else "Generous bedrooms",
            f"{bath} bathrooms" if isinstance(bath, int) else "Updated bathrooms",
            f"Located in {suburb}",
            "Close to schools and transport",
            "Comfortable, livable layout",
        ],
    )


async def run(state: GraphState, inputs: dict[str, Any]) -> ListingDraft:
    attrs = _resolve_inputs(state, inputs)
    await emit("tool_call", {"node": "listing", "tool": "draft_copy", "args": attrs})

    try:
        parsed = chat_structured(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Property attributes:\n{attrs}"},
            ],
            response_model=ListingDraft,
            temperature=0.4,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("listing LLM call failed (%s) — using fallback draft", exc)
        parsed = _fallback_draft(attrs)

    await emit("tool_result", {"node": "listing", "tool": "draft_copy",
                                "preview": parsed.headline})
    return parsed
