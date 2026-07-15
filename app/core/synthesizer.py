"""Turns the agent's raw research summary into a structured report the PDF
renderer can lay out predictably (fixed sections, not free-form prose)."""
import json

from app.core.llm_client import LLMClient
from app.core.cost_tracker import CostTracker

SYNTHESIS_PROMPT = """You are a market research report writer. You will be given raw research \
notes about a business and its competitors. Produce a structured JSON report with this exact shape:

{
  "executive_summary": "2-3 sentence overview of the competitive landscape",
  "competitors": [
    {
      "name": "...",
      "pricing": "summary of pricing/plans found, or 'Not publicly available'",
      "positioning": "how they position themselves in the market",
      "strengths": ["...", "..."],
      "weaknesses": ["...", "..."],
      "sources": ["url1", "url2"]
    }
  ],
  "opportunities": ["gap or opportunity the client business could exploit", "..."],
  "recommendations": ["actionable recommendation", "..."]
}

Only state claims that are supported by the research notes. Respond with ONLY the JSON, no markdown fences.
"""


def synthesize_report(research_summary: str, cost: CostTracker) -> dict:
    llm = LLMClient()
    messages = [{"role": "user", "content": f"Research notes:\n\n{research_summary}"}]
    response = llm.generate(SYNTHESIS_PROMPT, messages)
    cost.record(response.input_tokens, response.output_tokens, label="synthesis")

    text = response.text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)
