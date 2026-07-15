"""LLM-as-judge eval runner. For each case: run the full agent + synthesis pipeline,
then ask the judge model to score the resulting report JSON against the checklist.
Run: python eval/run_eval.py
Writes eval/results/<timestamp>.json and prints a pass-rate summary.
"""
from __future__ import annotations
import json
import os
import sys
import time

import yaml
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.agent import MarketAnalystAgent, AgentRunLimitExceeded
from app.core.synthesizer import synthesize_report
from app.core.llm_client import LLMClient

JUDGE_PROMPT = """You are grading a market research report against a checklist. \
For each checklist item, respond whether it PASSED or FAILED, with a one-sentence reason. \
Be strict: if a claim in the report isn't backed by the report's own "sources" fields, that's a FAILED \
faithfulness check. Respond as JSON: {"results": [{"check": "...", "verdict": "PASS|FAIL", "reason": "..."}]}
Respond with ONLY the JSON.
"""


def judge_report(report: dict, checks: list[str]) -> list[dict]:
    llm = LLMClient()
    prompt = f"Checklist:\n" + "\n".join(f"- {c}" for c in checks) + f"\n\nReport:\n{json.dumps(report, indent=2)}"
    response = llm.generate(JUDGE_PROMPT, [{"role": "user", "content": prompt}])
    text = response.text.strip().strip("`")
    if text.startswith("json"):
        text = text[4:]
    return json.loads(text)["results"]


def main():
    with open(os.path.join(os.path.dirname(__file__), "eval_set.yaml")) as f:
        cases = yaml.safe_load(f)

    all_results = []
    for case in cases:
        print(f"\n=== {case['id']}: {case['business_name']} ===")
        agent = MarketAnalystAgent()
        try:
            run_result = agent.run(case["business_name"], case["competitors"])
            report = synthesize_report(run_result["research_summary"], agent.cost)
        except (AgentRunLimitExceeded, Exception) as e:
            print(f"  RUN FAILED: {e}")
            all_results.append({"case_id": case["id"], "error": str(e), "checks": []})
            continue

        judged = judge_report(report, case["checks"])
        for j in judged:
            print(f"  [{j['verdict']}] {j['check']}: {j['reason']}")

        all_results.append({
            "case_id": case["id"],
            "cost": agent.cost.summary(),
            "checks": judged,
        })

    total_checks = sum(len(r["checks"]) for r in all_results)
    passed = sum(1 for r in all_results for c in r["checks"] if c["verdict"] == "PASS")
    pass_rate = (passed / total_checks * 100) if total_checks else 0.0

    print(f"\n{'='*50}\nOverall: {passed}/{total_checks} checks passed ({pass_rate:.1f}%)")

    os.makedirs(os.path.join(os.path.dirname(__file__), "results"), exist_ok=True)
    out_path = os.path.join(os.path.dirname(__file__), "results", f"eval_{int(time.time())}.json")
    with open(out_path, "w") as f:
        json.dump({"pass_rate": pass_rate, "results": all_results}, f, indent=2)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
