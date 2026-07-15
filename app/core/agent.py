"""Agent orchestration loop: plan -> tool calls -> replan on failure -> synthesize.
Deliberately a raw loop (not LangGraph) so every step is visible and debuggable —
this is what an interviewer will actually read.

No live search API is used (see app/tools/search.py for why) — the agent researches
from seed URLs supplied per competitor plus a few predictable review-site URL guesses,
using fetch_page to read each one. This is still a genuine multi-step agent: it decides
which URLs are worth fetching, replans when a fetch fails, and knows when it has
gathered enough evidence to stop."""
from __future__ import annotations
import json
import os

from app.core.llm_client import LLMClient
from app.core.cost_tracker import CostTracker
from app.tools.registry import TOOL_SCHEMAS, call_tool
from app.tools.search import guess_review_urls

SYSTEM_PROMPT = """You are a market research analyst agent. Given a business and a list of \
competitors (each with candidate URLs to investigate), your job is to research each \
competitor thoroughly using the fetch_page tool and gather enough evidence to support a \
competitor comparison report.

For each competitor, find:
- Pricing/plans if publicly available
- Positioning and key messaging (from their homepage/marketing copy)
- Customer sentiment: praises and complaints (from any review-site URLs provided)
- Recent news or product changes, if mentioned on the pages you fetch

Work step by step. Call fetch_page one URL at a time, starting with the most likely to \
have pricing/positioning info (usually the homepage or a /pricing page). If a fetch fails \
or returns a 404/thin page, move on to the next candidate URL for that competitor rather \
than giving up on it entirely. You do not have a search tool — only fetch the URLs you \
were given or that you find LINKED from a page you already fetched (the page text may \
mention other relevant URLs; you can propose fetching those too).

When you have gathered enough evidence for ALL competitors, respond with plain text starting \
with "RESEARCH_COMPLETE:" followed by a structured summary of everything you found, \
organized per competitor, citing the URL for every claim. If a competitor's pages were \
mostly unreachable, say so plainly rather than inventing details.
"""


class AgentRunLimitExceeded(Exception):
    pass


class MarketAnalystAgent:
    def __init__(self):
        self.llm = LLMClient()
        self.max_tool_calls = int(os.environ.get("MAX_TOOL_CALLS_PER_RUN", 25))
        self.max_tokens = int(os.environ.get("MAX_TOKENS_PER_RUN", 200_000))
        self.cost = CostTracker(model=self.llm._model)

    def run(self, business_name: str, competitors: list[dict]) -> dict:
        """competitors: list of {"name": str, "urls": list[str]} — urls come from the
        client config; review-site guesses are appended automatically."""
        competitor_briefs = []
        for comp in competitors:
            urls = list(comp.get("urls", []))
            urls.extend(u for u in guess_review_urls(comp["name"]) if u not in urls)
            competitor_briefs.append(f"- {comp['name']}: candidate URLs: {', '.join(urls)}")

        task = (
            f"Business to analyze on behalf of: {business_name}\n"
            f"Competitors to research:\n" + "\n".join(competitor_briefs) + "\n"
            "Begin your research now."
        )
        messages = [{"role": "user", "content": task}]

        trace = []
        for step in range(self.max_tool_calls):
            if self.cost.input_tokens + self.cost.output_tokens > self.max_tokens:
                raise AgentRunLimitExceeded("Token budget exceeded")

            response = self.llm.generate(SYSTEM_PROMPT, messages, tools=TOOL_SCHEMAS)
            self.cost.record(response.input_tokens, response.output_tokens, label=f"step_{step}")

            if response.text.strip().startswith("RESEARCH_COMPLETE:"):
                trace.append({"step": step, "type": "final_answer"})
                return {
                    "research_summary": response.text.replace("RESEARCH_COMPLETE:", "", 1).strip(),
                    "trace": trace,
                    "cost": self.cost.summary(),
                }

            if not response.tool_calls:
                # Model produced plain text without finishing — nudge it forward.
                messages.append({"role": "assistant", "content": response.text or "(no output)"})
                messages.append({
                    "role": "user",
                    "content": "Continue researching, or if done, respond starting with RESEARCH_COMPLETE:",
                })
                continue

            messages.append({"role": "assistant", "content": response.text or ""})
            for tc in response.tool_calls:
                self.cost.record_tool_call(tc["name"])
                result = call_tool(tc["name"], tc["arguments"])
                trace.append({"step": step, "type": "tool_call", "tool": tc["name"], "args": tc["arguments"], "result_status": result.get("result", {}).get("status", "error" if "error" in result else "ok")})
                messages.append({
                    "role": "user",
                    "content": f"Tool `{tc['name']}` result:\n{json.dumps(result)[:6000]}",
                })

        raise AgentRunLimitExceeded(f"Exceeded {self.max_tool_calls} tool-call steps without finishing")
