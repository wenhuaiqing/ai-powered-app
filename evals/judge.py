"""LLM-as-judge for Tier 2 evaluation.

Scores a single case's final answer + citations against the rubric:
  - fact_coverage     1-5: how many expected_facts are actually present?
  - citation_accuracy 1-5: do the citations support the claims? (Compliance/Market Watch only)
  - helpfulness       1-5: would an agent / buyer / tenant find this useful?

Uses OpenAI structured outputs (response_format=JudgeVerdict). The judge
is configured independently of the app under test via JUDGE_BASE_URL /
JUDGE_API_KEY / JUDGE_MODEL, falling back to the LLM_* triple when those
are unset. Keeping them separable is deliberate, for two reasons:
scoring a model's output with that same model invites self-preference
bias, and a judge inheriting only *part* of the app's config -- a model
id from one provider against another provider's endpoint -- 404s on
every call. Judge runs at temperature 0 so verdicts are reproducible in
a session.
"""

from __future__ import annotations

import os
import re
import time
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


_JUDGE_MODEL_FALLBACK = "gpt-4-1-mini"
_MAX_JUDGE_RETRIES = 3


def _judge_config() -> tuple[str, str, str] | None:
    """(endpoint, key, model) for the judge, or None if unconfigured.

    JUDGE_* wins as a set. Otherwise the LLM_* triple is used as a set --
    never a mix of the two, which is how you end up asking one provider
    for another provider's model id.
    """
    endpoint = os.getenv("JUDGE_BASE_URL", "")
    api_key = os.getenv("JUDGE_API_KEY", "")
    if endpoint and api_key:
        return endpoint, api_key, os.getenv("JUDGE_MODEL") or _JUDGE_MODEL_FALLBACK

    endpoint = os.getenv("LLM_BASE_URL", "")
    api_key = os.getenv("LLM_API_KEY", "")
    if endpoint and api_key:
        return endpoint, api_key, os.getenv("LLM_CHAT_MODEL") or _JUDGE_MODEL_FALLBACK
    return None


def _client() -> OpenAI | None:
    config = _judge_config()
    if config is None:
        return None
    endpoint, api_key, _ = config
    return OpenAI(base_url=endpoint, api_key=api_key)


def _retry_after_seconds(exc: Exception) -> float | None:
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            header = response.headers.get("retry-after")
        except Exception:  # noqa: BLE001
            header = None
        if header:
            try:
                return float(header)
            except ValueError:
                pass
    match = re.search(r"'retryDelay': '(\d+(?:\.\d+)?)s'", str(exc))
    return float(match.group(1)) if match else None


def judge_case(case: dict[str, Any], result: dict[str, Any]) -> JudgeVerdict | None:
    """Return a JudgeVerdict or None if the LLM is unavailable / errors out."""
    client = _client()
    if client is None:
        return None

    config = _judge_config()
    assert config is not None  # _client() would have returned None
    model = config[2]
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

    from openai import RateLimitError

    for attempt in range(_MAX_JUDGE_RETRIES):
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
        except RateLimitError as exc:
            # No node budget here, unlike the app, so a long wait is
            # honourable -- a scored case beats a skipped one, and a
            # skipped case silently drags the tier's average.
            delay = _retry_after_seconds(exc) or 5.0 * (attempt + 1)
            if attempt == _MAX_JUDGE_RETRIES - 1:
                print(f"  ! judge rate-limited for {case['id']}, giving up")
                return None
            print(f"  . judge rate-limited for {case['id']}, waiting {delay:.0f}s")
            time.sleep(delay)
        except Exception as exc:  # noqa: BLE001
            print(f"  ! judge failed for {case['id']}: {exc}")
            return None
    return None
