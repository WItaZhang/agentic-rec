"""Component ablation: toggle memory / reflection / planner on one architecture.

Because every component is an optional parameter, an ablation is just a
loop over config dictionaries.
"""

import copy

from agentic_rec import MockLLM, build_system, make_synthetic, simulation_metrics

base = {
    "recommender": {
        "profile": "history",
        "memory": {"type": "window", "size": 20},
        "planner": {"type": "react", "max_steps": 6},
        "tools": ["history", "retrieve", "rank"],
        "reflector": "self_critique",
    },
    "user": {"policy": {"type": "preference", "patience": 2}},
    "environment": {"max_turns": 6, "k": 8},
}

variants = {
    "full": {},
    "no_memory": {"memory": None},
    "no_reflection": {"reflector": None},
    "no_profile": {"profile": None},
    "direct_planner": {"planner": "direct"},
    "hierarchical": {"planner": {"type": "hierarchical", "max_steps": 5}},
}

data = make_synthetic(n_items=200, n_users=25, seed=0)
print(f"{'variant':16s} {'turns':>6s} {'click':>6s} {'CTR':>6s} {'exit':>6s} {'reward':>7s}")
for name, patch in variants.items():
    cfg = copy.deepcopy(base)
    for k, v in patch.items():
        if v is None:
            cfg["recommender"].pop(k, None)
        else:
            cfg["recommender"][k] = v
    system = build_system(cfg, MockLLM(), copy.deepcopy(data))
    r = simulation_metrics(system.env.run(system.recommender, system.users))
    print(f"{name:16s} {r.avg_turns:6.2f} {r.click_rate:6.3f} {r.ctr:6.3f} {r.exit_rate:6.3f} {r.avg_reward:7.3f}")

print(
    "\nNote: with MockLLM the variants that only change prompt content (memory, profile, reflection)\n"
    "are identical by construction; the mock ignores those sections. Point `llm` at a real backend\n"
    "to measure them. The table above verifies the plumbing: each variant builds and runs."
)
