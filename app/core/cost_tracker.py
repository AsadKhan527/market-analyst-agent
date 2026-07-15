"""Tracks token usage and estimated cost per agent run. Free-tier models cost $0,
but this keeps the same interface so swapping to a paid model later needs no code changes."""
from __future__ import annotations
from dataclasses import dataclass, field

# $ per 1M tokens (input, output). Free-tier providers priced at 0 for now —
# update when you swap to a paid model for a real client run.
PRICING = {
    "gemini-2.0-flash": (0.0, 0.0),
    "llama-3.3-70b-versatile": (0.0, 0.0),
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "claude-sonnet-5": (3.00, 15.00),
}


@dataclass
class CostTracker:
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: int = 0
    events: list[dict] = field(default_factory=list)

    def record(self, input_tokens: int, output_tokens: int, label: str = ""):
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.events.append({
            "label": label,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        })

    def record_tool_call(self, tool_name: str):
        self.tool_calls += 1
        self.events.append({"label": f"tool:{tool_name}", "input_tokens": 0, "output_tokens": 0})

    @property
    def estimated_cost_usd(self) -> float:
        in_price, out_price = PRICING.get(self.model, (0.0, 0.0))
        return (self.input_tokens / 1_000_000) * in_price + (self.output_tokens / 1_000_000) * out_price

    def summary(self) -> dict:
        return {
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "tool_calls": self.tool_calls,
            "estimated_cost_usd": round(self.estimated_cost_usd, 4),
        }
