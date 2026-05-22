"""Tier-1 shape tests for every agent node.

Verifies each node returns a valid Pydantic model with the expected key fields
populated. These run without external APIs (Azure / Tavily) because every
node has a no-key fallback path.
"""

from __future__ import annotations

import pytest

from src.app.services.agents.nodes import (
    compliance,
    data_query,
    lead_triage,
    listing,
    market_watch,
    matcher,
    valuation,
)
from src.app.services.agents.schemas import (
    ComplianceResult,
    DataQueryResult,
    GraphState,
    LeadTriageResult,
    ListingDraft,
    MarketWatchResult,
    MatcherResult,
    PageContext,
    ValuationResult,
)


@pytest.fixture
def base_state() -> GraphState:
    return GraphState(user_message="placeholder", page_context=PageContext())


@pytest.mark.asyncio
async def test_compliance_returns_typed_result(base_state):
    state = base_state.model_copy(update={"user_message": "What are NSW tenancy bond limits?"})
    result = await compliance.run(state, {})
    assert isinstance(result, ComplianceResult)
    assert isinstance(result.answer, str) and result.answer
    assert result.confidence in {"low", "medium", "high"}
    for c in result.citations:
        assert c.source
        assert c.source_type in {"local_corpus", "web"}


@pytest.mark.asyncio
async def test_data_query_returns_typed_result(base_state):
    state = base_state.model_copy(update={"user_message": "Top 5 suburbs by median price"})
    result = await data_query.run(state, {})
    assert isinstance(result, DataQueryResult)
    assert result.sql.strip().lower().startswith(("select", "with"))
    if result.validation_passed:
        assert result.row_count == len(result.rows)
        assert result.columns


@pytest.mark.asyncio
async def test_valuation_returns_typed_result(base_state):
    result = await valuation.run(base_state, {"num_bed": 3, "num_bath": 2, "suburb": "Bondi"})
    assert isinstance(result, ValuationResult)
    assert result.predicted_price >= 0
    lo, hi = result.confidence_interval
    if result.predicted_price > 0:
        assert lo <= hi
        assert result.contributions  # at least one feature should move the prediction


@pytest.mark.asyncio
async def test_listing_returns_typed_result(base_state):
    result = await listing.run(base_state, {
        "suburb": "Bondi", "num_bed": 3, "num_bath": 2, "type": "House",
    })
    assert isinstance(result, ListingDraft)
    assert result.headline
    assert result.body_markdown
    assert result.key_features


@pytest.mark.asyncio
async def test_lead_triage_returns_typed_result(base_state):
    lead = {
        "lead_id": "LD9999", "name": "Test Lead", "intent": "Buying",
        "min_bed": 3, "budget_min": 800_000, "budget_max": 1_200_000,
        "preferred_suburb": "Bondi", "urgency": "high",
        "notes": "Looking for family-friendly with good schools",
    }
    state = base_state.model_copy(update={
        "page_context": PageContext(module="pipeline", current_item=lead),
    })
    result = await lead_triage.run(state, {})
    assert isinstance(result, LeadTriageResult)
    assert result.summary
    assert result.intent_score in {1, 2, 3, 4, 5}
    assert result.urgency in {"low", "medium", "high"}


@pytest.mark.asyncio
async def test_market_watch_returns_typed_result(base_state):
    state = base_state.model_copy(update={
        "user_message": "What's happening in the Sydney property market?"
    })
    result = await market_watch.run(state, {})
    assert isinstance(result, MarketWatchResult)
    assert result.query_used


@pytest.mark.asyncio
async def test_matcher_returns_typed_result(base_state):
    state = base_state.model_copy(update={
        "user_message": "Family-friendly 3-bed under 1.5M within 20km",
    })
    result = await matcher.run(state, {})
    assert isinstance(result, MatcherResult)
    assert result.filter_summary
    # We don't assert candidates > 0 because filter is data-dependent, but if there are
    # candidates they must have the expected shape.
    for c in result.candidates:
        assert c.suburb
        assert c.predicted_price is not None
