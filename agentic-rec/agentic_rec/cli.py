"""Command-line entry point.

    agentic-rec list                          # show registered components
    agentic-rec run configs/interecagent.toml # simulate + offline eval with the mock LLM
    agentic-rec compare configs/*.toml        # side-by-side table
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

from .core.config import load_config
from .core.registry import registry
from .data.synthetic import make_synthetic
from .evaluation.metrics import evaluate_offline, simulation_metrics
from .llm import AnthropicLLM, MockLLM, OpenAICompatibleLLM
from .recipes.build import build_system


def make_llm(name: str, model: str | None) -> MockLLM | OpenAICompatibleLLM | AnthropicLLM:
    if name == "mock":
        return MockLLM()
    if name == "openai":
        return OpenAICompatibleLLM(model=model or "gpt-4o-mini")
    if name == "anthropic":
        return AnthropicLLM(model=model or "claude-sonnet-5")
    raise SystemExit(f"unknown llm backend {name}")


def run_one(path: str, args: argparse.Namespace) -> dict:
    cfg = load_config(path)
    data = make_synthetic(n_items=args.items, n_users=args.users, seed=args.seed)
    llm = make_llm(args.llm, args.model)
    sim_data = copy.deepcopy(data)  # the simulation mutates user histories
    system = build_system(cfg, llm, sim_data, seed=args.seed)
    trajs = system.env.run(system.recommender, system.users)
    sim = simulation_metrics(trajs, n_items=len(data.catalog))
    off = evaluate_offline(system.recommender, data.users, data.holdout, k=system.env.config.k, n_items=len(data.catalog))
    return {
        "config": Path(path).stem,
        "name": system.name,
        "architecture": system.recommender.describe(),
        "simulation": sim.as_dict(),
        "offline": off.as_dict(),
        "llm_calls": llm.stats.calls,
    }


def cmd_list(_: argparse.Namespace) -> None:
    for kind in registry.kinds():
        print(f"{kind:12s} {', '.join(registry.names(kind))}")


def cmd_run(args: argparse.Namespace) -> None:
    for path in args.configs:
        r = run_one(path, args)
        if args.json:
            print(json.dumps(r, indent=2))
            continue
        print(f"== {r['name']} ({r['config']})")
        print("   " + r["architecture"])
        s, o = r["simulation"], r["offline"]
        print(f"   simulation: turns={s['avg_turns']:.2f} click_rate={s['click_rate']:.3f} CTR={s['ctr']:.3f} exit={s['exit_rate']:.3f} reward={s['avg_reward']:.3f}")
        print(f"   offline   : HR@{o['k']}={o['hit_rate']:.3f} NDCG={o['ndcg']:.3f} MRR={o['mrr']:.3f} Cov={o['coverage']:.3f}  (llm calls: {r['llm_calls']})")


def cmd_compare(args: argparse.Namespace) -> None:
    rows = [run_one(p, args) for p in args.configs]
    head = f"{'config':16s} {'turns':>6s} {'click':>6s} {'CTR':>6s} {'exit':>6s} {'HR':>6s} {'NDCG':>6s} {'calls':>6s}"
    print(head)
    print("-" * len(head))
    for r in rows:
        s, o = r["simulation"], r["offline"]
        print(f"{r['config']:16s} {s['avg_turns']:6.2f} {s['click_rate']:6.3f} {s['ctr']:6.3f} {s['exit_rate']:6.3f} {o['hit_rate']:6.3f} {o['ndcg']:6.3f} {r['llm_calls']:6d}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="agentic-rec", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    for name, fn in (("run", cmd_run), ("compare", cmd_compare)):
        sp = sub.add_parser(name)
        sp.add_argument("configs", nargs="+")
        sp.add_argument("--llm", default="mock", choices=["mock", "openai", "anthropic"])
        sp.add_argument("--model", default=None)
        sp.add_argument("--users", type=int, default=30)
        sp.add_argument("--items", type=int, default=200)
        sp.add_argument("--seed", type=int, default=0)
        sp.add_argument("--json", action="store_true")
        sp.set_defaults(fn=fn)
    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":  # pragma: no cover
    main(sys.argv[1:])
