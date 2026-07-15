# AI Market Analyst Agent

An autonomous research agent that researches a business's competitors and produces a
branded, cited PDF report — the kind of work a market analyst would normally charge
$500-2000+ for, generated in minutes.

Give it a business name and a list of competitors. It plans its own research steps,
searches the web, reads competitor sites and review platforms, replans when a source
fails, and synthesizes everything into a structured report with inline source citations.

## Why this isn't just "a chatbot with a search tool"

- **Multi-step planning with replanning on failure.** If a scrape fails or a search
  returns nothing useful, the agent tries a different query or source rather than
  giving up on that competitor — see `app/core/agent.py`.
- **Provider-agnostic by design.** The LLM backend (`app/core/llm_client.py`) is swappable
  via one environment variable (`LLM_PROVIDER=gemini|groq`), with the same interface
  ready to extend to OpenAI/Anthropic. Built and evaluated entirely on free-tier models.
- **Evaluated, not just demoed.** `eval/` contains a hand-labeled test set and an
  LLM-as-judge harness that scores each report against a checklist (citation
  faithfulness, pricing accuracy, no-hallucination checks). Run it, see a pass rate,
  not just "it seemed to work."
- **Cost- and run-time bounded.** Every run tracks tokens, tool calls, and estimated
  cost (`app/core/cost_tracker.py`), with hard caps so a run can't loop forever or
  blow a budget — the kind of guardrail that matters the moment you're paying per call.
- **Productized for reselling.** Each client is a single YAML config
  (`sample_configs/`) — new business name, competitor list, brand color. No code
  changes needed to run it for a new client.

## Architecture

```
main.py                    entry point (CLI)
app/core/agent.py          plan -> tool call -> replan loop
app/core/llm_client.py     provider-agnostic LLM wrapper (Gemini / Groq)
app/core/synthesizer.py    raw research notes -> structured JSON report
app/core/report_renderer.py structured JSON -> branded PDF
app/core/cost_tracker.py   token/cost/tool-call accounting per run
app/tools/                 web_search (Brave), fetch_page (requests -> Playwright fallback)
eval/                      eval set + LLM-as-judge runner
sample_configs/            one YAML per client
```

## Setup (100% free tier)

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
playwright install chromium   # only needed for JS-heavy competitor sites
cp .env.example .env
```

Fill in `.env`:
- `GEMINI_API_KEY` — free at [aistudio.google.com](https://aistudio.google.com) (or use
  `GROQ_API_KEY` + set `LLM_PROVIDER=groq` for faster/free Llama inference)
- `BRAVE_API_KEY` — free tier (2000 queries/month) at
  [brave.com/search/api](https://brave.com/search/api)

## Run it

```bash
python main.py --config sample_configs/example_client.yaml
```

Outputs a PDF report to `output/` and a full run log (`output/last_run_log.json`) with
the complete tool-call trace and cost breakdown.

## Run the evals

```bash
python eval/run_eval.py
```

Runs the full pipeline against a hand-labeled test set of real, well-known businesses
(so factual claims are checkable), then uses an LLM judge to score each report against
a checklist (pricing found, citations present, no unsupported claims, distinct
competitor positioning). Prints a pass rate and saves detailed results to
`eval/results/`.

## Selling this as a productized service

To onboard a new client: copy `sample_configs/example_client.yaml`, fill in their
business name, competitor list, and brand color, then run `main.py --config`. No code
changes required. Swap `GEMINI_MODEL`/`GROQ_MODEL` for a paid frontier model
(GPT-4o, Claude) in `.env` once you're charging for reports — the cost tracker already
has pricing entries ready in `app/core/cost_tracker.py`.
