import copy
import math
from pathlib import Path

import pytest

from agentic_rec import (
    MockLLM,
    build_system,
    evaluate_offline,
    load_config,
    make_synthetic,
    simulation_metrics,
)
from agentic_rec.core.types import RecList
from agentic_rec.evaluation import ranking_metrics
from agentic_rec.orchestration import ManagerOrchestrator, PipelineOrchestrator, VoteOrchestrator

CONFIGS = sorted(Path(__file__).resolve().parents[1].joinpath("configs").glob("*.toml"))


def test_ranking_metrics_exact_values():
    recs = [RecList("u1", ["a", "b", "c"]), RecList("u2", ["x", "y", "z"])]
    truth = {"u1": ["b"], "u2": ["q"]}
    r = ranking_metrics(recs, truth, k=3, n_items=10)
    assert r.hit_rate == 0.5 and r.mrr == 0.25 and r.n_users == 2
    assert abs(r.ndcg - 0.5 * (1 / math.log2(3))) < 1e-9  # b at rank 2 for u1, miss for u2
    assert r.coverage == 0.6


def test_ranking_metrics_ndcg_math():
    r = ranking_metrics([RecList("u", ["a", "b"])], {"u": ["b"]}, k=2)
    assert abs(r.ndcg - 1 / math.log2(3)) < 1e-9


@pytest.mark.parametrize("path", CONFIGS, ids=[p.stem for p in CONFIGS])
def test_every_config_builds_and_runs(path):
    cfg = load_config(path)
    data = make_synthetic(n_items=80, n_users=4, seed=3)
    sim_data = copy.deepcopy(data)
    system = build_system(cfg, MockLLM(), sim_data, seed=3)
    trajs = system.env.run(system.recommender, system.users)
    assert len(trajs) == 4 and all(t.n_turns >= 1 for t in trajs)
    report = simulation_metrics(trajs, n_items=len(data.catalog))
    assert 0.0 <= report.click_rate <= 1.0
    off = evaluate_offline(system.recommender, data.users, data.holdout, k=system.env.config.k)
    assert off.n_users == 4
    assert system.recommender.describe()


def test_orchestrator_types():
    data = make_synthetic(n_items=60, n_users=3, seed=5)
    for name in ("macrec", "macrs", "iagent"):
        cfg = load_config(Path(__file__).resolve().parents[1] / "configs" / f"{name}.toml")
        system = build_system(cfg, MockLLM(), copy.deepcopy(data))
        rec = system.recommender
        assert isinstance(rec, (ManagerOrchestrator, VoteOrchestrator, PipelineOrchestrator))
        out = rec.recommend(data.users[0])
        assert out.item_ids


def test_manager_exposes_workers_as_tools():
    data = make_synthetic(n_items=60, n_users=3, seed=5)
    cfg = load_config(Path(__file__).resolve().parents[1] / "configs" / "macrec.toml")
    system = build_system(cfg, MockLLM(), copy.deepcopy(data))
    names = system.recommender.manager.tools.names()
    assert {"user_analyst", "item_analyst"} <= set(names)


def test_cli_smoke(capsys):
    from agentic_rec.cli import main

    main(["list"])
    main(["run", str(CONFIGS[0]), "--users", "3", "--items", "50"])
    out = capsys.readouterr().out
    assert "simulation:" in out and "offline" in out
