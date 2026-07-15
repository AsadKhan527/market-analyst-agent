"""Entry point: python main.py --config sample_configs/example_client.yaml"""
import argparse
import json
import os
import time

import yaml
from dotenv import load_dotenv

load_dotenv()

from app.core.agent import MarketAnalystAgent, AgentRunLimitExceeded
from app.core.synthesizer import synthesize_report
from app.core.report_renderer import render_pdf


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Path to client YAML config")
    parser.add_argument("--outdir", default="output", help="Directory to write the PDF + run log")
    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)

    os.makedirs(args.outdir, exist_ok=True)
    start = time.time()

    print(f"[1/3] Researching {len(config['competitors'])} competitors for {config['business_name']}...")
    agent = MarketAnalystAgent()
    try:
        run_result = agent.run(config["business_name"], config["competitors"])
    except AgentRunLimitExceeded as e:
        print(f"FAILED: {e}")
        raise SystemExit(1)

    print(f"[2/3] Synthesizing structured report...")
    report = synthesize_report(run_result["research_summary"], agent.cost)

    print(f"[3/3] Rendering PDF...")
    output_path = os.path.join(args.outdir, config.get("output_filename", "report.pdf"))
    render_pdf(report, config["business_name"], config.get("brand_color", "#1A1A1A"), output_path)

    elapsed = time.time() - start
    final_cost = agent.cost.summary()

    log_path = os.path.join(args.outdir, "last_run_log.json")
    with open(log_path, "w") as f:
        json.dump({
            "business_name": config["business_name"],
            "competitors": config["competitors"],
            "elapsed_seconds": round(elapsed, 1),
            "cost": final_cost,
            "trace": run_result["trace"],
        }, f, indent=2)

    print(f"\nDone in {elapsed:.1f}s — report saved to {output_path}")
    print(f"Cost: {final_cost['tool_calls']} tool calls, "
          f"{final_cost['input_tokens'] + final_cost['output_tokens']} tokens, "
          f"${final_cost['estimated_cost_usd']:.4f} estimated")
    print(f"Full run log: {log_path}")


if __name__ == "__main__":
    main()
