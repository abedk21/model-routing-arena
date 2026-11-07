"""Run: python -m routing_arena demo [--out examples/report.html]"""
import argparse
import json
from pathlib import Path
from .engine import compare_policies
from .report import render


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministic LLM model routing arena")
    parser.add_argument("command", choices=["demo"])
    parser.add_argument("--workload", type=Path, default=Path(__file__).resolve().parents[1] / "fixtures" / "workload.json")
    parser.add_argument("--out", type=Path, default=Path("examples/arena_report.html"))
    parser.add_argument("--seed", type=int, default=41)
    args = parser.parse_args()
    cfg = json.loads(args.workload.read_text(encoding="utf-8"))
    results = compare_policies(cfg["models"], cfg["tasks"], args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(results), encoding="utf-8")
    print(json.dumps({"report": str(args.out), "summary": [{k: v for k,v in r.items() if k != "outcomes"} for r in results]}, indent=2))


if __name__ == "__main__":
    main()
