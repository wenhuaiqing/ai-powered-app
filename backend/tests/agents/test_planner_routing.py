"""Tier-1 tests for the heuristic planner — verifies routing without an LLM."""

from __future__ import annotations

import pytest

from src.app.services.agents.planner import _heuristic_decision


@pytest.mark.parametrize(
    "prompt, expected_first_agent",
    [
        # Compliance keywords
        ("What stamp duty applies to a $900k purchase in NSW?", "compliance"),
        ("What are the bond limits for a residential tenancy?", "compliance"),
        ("Tell me about FIRB rules for foreign buyers", "compliance"),
        ("Are there strata levies for off-the-plan apartments?", "compliance"),
        # Market Watch keywords (live web)
        ("What's happening in the Sydney property market this week?", "market_watch"),
        ("Any recent news about NSW interest rate changes?", "market_watch"),
        # Listing drafter
        ("Draft listing copy for the property at 5 Smith Street", "listing"),
        # Lead triage
        ("Triage this lead and suggest a next action", "lead_triage"),
        # Property matcher (buyer requirements)
        ("Find me a 3-bed family-friendly suburb under 1.5M within 20km", "matcher"),
        ("Looking for a tenant-friendly suburb close to a train station", "matcher"),
        # Valuation
        ("Estimate the value of a 4-bed house in Manly with 800sqm", "valuation"),
        # Data query (analytics keywords)
        ("How many sales were there in Bondi last year?", "data_query"),
        ("Top 10 suburbs by median price", "data_query"),
    ],
)
def test_heuristic_routes(prompt: str, expected_first_agent: str):
    decision = _heuristic_decision(prompt)
    chosen = [c.name for c in decision.agents_to_call]
    assert chosen, f"no agent chosen for prompt: {prompt!r}"
    assert chosen[0] == expected_first_agent, (
        f"prompt {prompt!r} routed to {chosen}, expected first={expected_first_agent}"
    )


def test_no_double_agent_for_same_keyword():
    # A prompt with multiple compliance keywords shouldn't route compliance twice.
    decision = _heuristic_decision(
        "What stamp duty applies and how do tenancy bonds work?"
    )
    names = [c.name for c in decision.agents_to_call]
    assert names.count("compliance") == 1


def test_unknown_prompt_defaults_to_general():
    # Casual chit-chat / no specialist keyword -> falls through to the
    # general chat agent so the user always gets some useful response.
    decision = _heuristic_decision("hello there")
    chosen = [c.name for c in decision.agents_to_call]
    assert chosen == ["general"]


def test_platform_question_routes_to_general():
    decision = _heuristic_decision("How does this app work?")
    chosen = [c.name for c in decision.agents_to_call]
    assert chosen == ["general"]
