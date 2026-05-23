"""LLM-as-judge for Tier 2 evaluation.

Scores a single case's final answer + citations against the rubric:
  - fact_coverage     1-5: how many expected_facts are actually present?
  - citation_accuracy 1-5: do the citations support the claims? (Compliance/Market Watch only)
  - helpfulness       1-5: would an agent / buyer / tenant find this useful?

Uses OpenAI structured outputs (response_format=JudgeVerdict). Reuses the
same Azure OpenAI deployment configured for the app — judge runs at
temperature 0 so verdicts are reproducible within a session.
"""

from __future__ import annotations

import os
from typing import Any, Literal

from openai import OpenAI
from pydantic import BaseModel, Field

JUDGE_SYSTEM_PROMPT = """\
You are evaluating a real-estate AI assistant's response to a fixed test
case. You will be given:
  - the user's prompt,
  - the list of expected facts the assistant should have surfaced,
  - the list of anti-facts the assistant must NOT surface,
  - the assistant's final answer,
  - and the citations the assistant returned.

Score three dimensions, each 1-5 (1=poor, 5=excellent):

1. fact_coverage: how many of the expected_facts appear (semantically — a
   paraphrase still counts) in the final answer or the citation snippets.
   Penalise heavily if any anti_fact appears.

2. citation_accuracy: for Compliance / Market Watch answers, are the cited
   sources real and do they support the claims? Score 5 if N/A (e.g.
   pure Valuation / Listing Draft / Lead Triage with no citations
   expected).

3. helpfulness: would an estate agent / buyer / tenant act on this
   answer? Concrete numbers, clear language, appropriate caveats.

Output strict JSON matching the JudgeVerdict schema with a one-sentence
reasoning for each score.
"""


class JudgeVerdict(BaseModel):
    fact_coverage_score: Literal[1, 2, 3, 4, 5]
    fact_coverage_reasoning: str
    citation_accuracy_score: Literal[1, 2, 3, 4, 5]
    citation_accuracy_reasoning: str
    helpfulness_score: Literal[1, 2, 3, 4, 5]
    helpfulness_reasoning: str

    @property
    def total(self) -> float:
        return (
            self.fact_coverage_score
            + self.citation_accuracy_score
            + self.helpfulness_score
        ) / 3


def _client() -> OpenAI | None:
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
    if not endpoint or not api_key:
        return None
    return OpenAI(base_url=endpoint, api_key=api_key)


def judge_case(case: dict[str, Any], result: dict[str, Any]) -> JudgeVerdict | None:
    """Return a JudgeVerdict or None if the LLM is unavailable / errors out."""
    client = _client()
    if client is None:
        return None

    model = os.getenv("AZURE_OPENAI_CHAT_MODEL", "gpt-4o")
    citations_text = "\n".join(
        f"- [{c.get('source_type', 'local_corpus')}] {c.get('source')}: {c.get('snippet', '')[:200]}"
        for c in (result.get("citations") or [])
    ) or "(no citations)"

    user_payload = (
        f"Prompt: {case['prompt']}\n\n"
        f"Expected facts: {case.get('expected_facts') or []}\n"
        f"Anti-facts (must NOT appear): {case.get('anti_facts') or []}\n\n"
        f"Final answer:\n{result.get('final_message') or '(empty)'}\n\n"
        f"Citations:\n{citations_text}"
    )

    try:
        completion = client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": user_payload},
            ],
            response_format=JudgeVerdict,
            temperature=0,
        )
        return completion.choices[0].message.parsed
    except Exception as exc:  # noqa: BLE001
        print(f"  ! judge failed for {case['id']}: {exc}")
        return None
