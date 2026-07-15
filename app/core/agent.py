"""Agent orchestration loop: plan -> tool calls -> replan on failure -> synthesize.
Deliberately a raw loop (not LangGraph) so every step is visible and debuggable —
this is what an interviewer will actually read."""
from __future__ import annotations
import json
import os

from app.core.llm_client import LLMClient
from app.core.cost_tracker import CostTracker
from app.tools.registry import TOOL_SCHEMAS, call_tool

SYSTEM_PROMPT = """You are a market research analyst agent. Given a business and a list of \
competitors, your job is to research each competitor thoroughly using the tools available \
(web_search, fetch_page) and gather enough evidence to support a competitor comparison report.

For each competitor, find:
- Pricing/plans if publicly available
- Positioning and key messaging (from their homepage/marketing copy)
- Customer sentiment: praises and complaints (search for reviews on G2, Trustpilot, Reddit)
- Recent news or product changes

Work step by step. Call one tool at a time. If a tool fails or returns nothing useful, \
try a different query or a different source rather than giving up on that competitor. \
When you have gathered enough evidence for ALL competitors, respond with plain text starting \
with "RESEARCH_COMPLETE:" followed by a structured summary of everything you found, \
organized per competitor, citing the URL for every claim.
"""


class AgentRunLimitExceeded(Exception):
    pass


class MarketAnalystAgent:
    def __init__(self):
        self.llm = LLMClient()
        self.max_tool_calls = int(os.environ.get("MAX_TOOL_CALLS_PER_RUN", 25))
        self.max_tokens = int(os.environ.get("MAX_TOKENS_PER_RUN", 200_000))
        self.cost = CostTracker(model=self.llm._model)

    def run(self, business_name: str, competitors: list[str]) -> dict:
        task = (
            f"Business to analyze on behalf of: {business_name}\n"
            f"Competitors to research: {', '.join(competitors)}\n"
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
