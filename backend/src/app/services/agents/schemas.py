"""Structured-output contracts for every agent node + LangGraph state.

Each *Result model is the return shape of one node. GraphState is the rolling
state object LangGraph threads through the graph.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

AgentName = Literal[
    "compliance",
    "data_query",
    "matcher",
    "valuation",
    "listing",
    "lead_triage",
    "market_watch",
]


# ---------------------------------------------------------------------------
# Page context (sent from the frontend with every orb request)
# ---------------------------------------------------------------------------

class PageContext(BaseModel):
    module: str = "dashboard"          # e.g. "properties", "pipeline", "compliance"
    current_item: dict[str, Any] | None = None   # e.g. a property dict or lead dict


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------

class AgentCall(BaseModel):
    """One agent call decided by the planner.

    `inputs_json` is the raw JSON string the LLM emits; Azure strict mode
    forbids open-shape `dict[str, Any]` in nested response_format objects,
    so we round-trip through a string and decode via the `inputs` property.
    """
    model_config = ConfigDict(extra="forbid")

    name: AgentName
    inputs_json: str = "{}"
    reasoning: str = ""

    @property
    def inputs(self) -> dict[str, Any]:
        if not self.inputs_json:
            return {}
        try:
            value = json.loads(self.inputs_json)
        except json.JSONDecodeError:
            return {}
        return value if isinstance(value, dict) else {}


class PlannerDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agents_to_call: list[AgentCall]
    reasoning: str
    needs_clarification: bool = False


# ---------------------------------------------------------------------------
# Per-agent results
# ---------------------------------------------------------------------------

class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    url: str | None = None
    snippet: str
    score: float
    source_type: Literal["local_corpus", "web"] = "local_corpus"


class ComplianceResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str
    citations: list[Citation] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "medium"
    used_web_fallback: bool = False


class DataQueryResult(BaseModel):
    sql: str
    columns: list[str] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)
    row_count: int = 0
    interpretation: str = ""
    validation_passed: bool = True
    validation_errors: list[str] = Field(default_factory=list)


class FeatureContribution(BaseModel):
    feature: str
    value: Any = None
    contribution_aud: float


class ValuationResult(BaseModel):
    predicted_price: float
    confidence_interval: tuple[float, float]
    contributions: list[FeatureContribution] = Field(default_factory=list)
    inputs_used: dict[str, Any] = Field(default_factory=dict)


class Candidate(BaseModel):
    suburb: str
    sample_address: str | None = None
    predicted_price: float | None = None
    lifestyle_score: float | None = None
    rationale: str


class MatcherResult(BaseModel):
    filter_summary: str
    candidates: list[Candidate] = Field(default_factory=list)


class ListingDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headline: str
    body_markdown: str
    key_features: list[str] = Field(default_factory=list)
    # Azure strict mode dislikes Optional tuple — use two floats instead.
    suggested_price_min: float | None = None
    suggested_price_max: float | None = None


class LeadTriageResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    intent_score: Literal[1, 2, 3, 4, 5] = 3
    urgency: Literal["low", "medium", "high"] = "medium"
    suggested_actions: list[str] = Field(default_factory=list)
    matched_suburbs: list[str] = Field(default_factory=list)


class WebHit(BaseModel):
    title: str
    url: str
    snippet: str
    score: float
    source_type: Literal["local_corpus", "web"] = "web"


class MarketWatchResult(BaseModel):
    answer: str
    hits: list[WebHit] = Field(default_factory=list)
    query_used: str


class NodeError(BaseModel):
    node: AgentName | Literal["planner", "summariser"]
    message: str
    retry_count: int = 0


# ---------------------------------------------------------------------------
# Final LLM summarisation
# ---------------------------------------------------------------------------

class FinalMessage(BaseModel):
    message: str
    used_agents: list[AgentName] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Graph state — single source of truth threaded through every node
# ---------------------------------------------------------------------------

class GraphState(BaseModel):
    user_message: str
    page_context: PageContext = Field(default_factory=PageContext)
    planner_decision: PlannerDecision | None = None
    compliance_result: ComplianceResult | None = None
    data_query_result: DataQueryResult | None = None
    valuation_result: ValuationResult | None = None
    matcher_result: MatcherResult | None = None
    listing_draft: ListingDraft | None = None
    lead_triage_result: LeadTriageResult | None = None
    market_watch_result: MarketWatchResult | None = None
    final_message: str | None = None
    errors: list[NodeError] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}
