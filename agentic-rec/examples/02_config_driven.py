"""Run a paper-style architecture from a config file and evaluate it two ways."""

import copy
import sys

from agentic_rec import (
    MockLLM,
    build_system,
    evaluate_offline,
    load_config,
    make_synthetic,
    simulation_metrics,
)

path = sys.argv[1] if len(sys.argv) > 1 else "configs/interecagent.toml"
data = make_synthetic(n_items=200, n_users=30, seed=0)

system = build_system(load_config(path), MockLLM(), copy.deepcopy(data))
print(system.name, "->", system.recommender.describe())

trajs = system.env.run(system.recommender, system.users)
print("simulation:", simulation_metrics(trajs, n_items=len(data.catalog)))
print("offline   :", evaluate_offline(system.recommender, data.users, data.holdout, k=10, n_items=len(data.catalog)))
