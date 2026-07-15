"""Provider-agnostic LLM client. Swap providers via LLM_PROVIDER env var only."""
from __future__ import annotations
import os
import json
from dataclasses import dataclass, field
from typing import Any
from tenacity import retry, stop_after_attempt, wait_exponential


@dataclass
class LLMResponse:
    text: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0


class LLMClient:
    def __init__(self):
        self.provider = os.environ.get("LLM_PROVIDER", "gemini")
        if self.provider == "gemini":
            from google import genai
            self._client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
            self._model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
        elif self.provider == "groq":
            from groq import Groq
            self._client = Groq(api_key=os.environ["GROQ_API_KEY"])
            self._model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
        else:
            raise ValueError(f"Unknown LLM_PROVIDER: {self.provider}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20))
    def generate(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        if self.provider == "gemini":
            return self._generate_gemini(system_prompt, messages, tools)
        return self._generate_groq(system_prompt, messages, tools)

    def _generate_gemini(self, system_prompt, messages, tools):
        from google.genai import types

        contents = [
            types.Content(role="user" if m["role"] == "user" else "model", parts=[types.Part(text=m["content"])])
            for m in messages
        ]
        config = types.GenerateContentConfig(system_instruction=system_prompt)
        if tools:
            config.tools = [types.Tool(function_declarations=[_to_gemini_fn(t) for t in tools])]

        resp = self._client.models.generate_content(model=self._model, contents=contents, config=config)

        tool_calls = []
        text_parts = []
        for part in resp.candidates[0].content.parts:
            if getattr(part, "function_call", None):
                tool_calls.append({
                    "name": part.function_call.name,
                    "arguments": dict(part.function_call.args),
                })
            elif getattr(part, "text", None):
                text_parts.append(part.text)

        usage = resp.usage_metadata
        return LLMResponse(
            text="".join(text_parts),
            tool_calls=tool_calls,
            input_tokens=usage.prompt_token_count or 0,
            output_tokens=usage.candidates_token_count or 0,
        )

    def _generate_groq(self, system_prompt, messages, tools):
        chat_messages = [{"role": "system", "content": system_prompt}] + messages
        kwargs = {}
        if tools:
            kwargs["tools"] = [{"type": "function", "function": t} for t in tools]
            kwargs["tool_choice"] = "auto"

        resp = self._client.chat.completions.create(
            model=self._model, messages=chat_messages, **kwargs
        )
        choice = resp.choices[0].message

        tool_calls = []
        if choice.tool_calls:
            for tc in choice.tool_calls:
                tool_calls.append({
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments),
                })

        return LLMResponse(
            text=choice.content or "",
            tool_calls=tool_calls,
            input_tokens=resp.usage.prompt_tokens,
            output_tokens=resp.usage.completion_tokens,
        )


def _to_gemini_fn(tool: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": tool["name"],
        "description": tool["description"],
        "parameters": tool["parameters"],
    }
