"""Listing Drafter — Day 1 stub. Day 2 makes a real LLM call with structured output."""

from __future__ import annotations

from typing import Any

from src.app.services.agents.runtime import emit
from src.app.services.agents.schemas import GraphState, ListingDraft


async def run(state: GraphState, inputs: dict[str, Any]) -> ListingDraft:
    await emit("node_start", {"name": "listing", "note": "[stub]"})
    return ListingDraft(
        headline="[stub] Modern family home in a sought-after pocket",
        body_markdown=(
            "[stub] Day 2 will generate listing copy from the property attributes "
            f"in inputs={inputs!r}."
        ),
        key_features=["[stub]"],
        suggested_price_range=None,
    )
