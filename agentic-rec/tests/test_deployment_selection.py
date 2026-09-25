import copy

import pytest
import yaml

from src.deployment_selection import select_deployment


def test_selection_uses_registered_budget_quality_tolerance_and_simplicity():
    with open("configs/amazon_deployment_selection_v1.yaml", encoding="utf-8") as stream:
        settings = yaml.safe_load(stream)["selection"]
    candidates = {name: {"ndcg": .05, "api_usd_per_1000": 0} for name in settings["candidates"]}
    candidates["causal_sequence"]["ndcg"] = .055
    candidates["selected_learned"] = {"ndcg": .1, "api_usd_per_1000": .3}
    assert select_deployment(candidates, settings)["selected_method"] == "causal_sequence"
    # A cheaper simple method within the *registered* tolerance wins; this is not equivalence.
    candidates["itemknn"]["ndcg"] = .054
    assert select_deployment(candidates, settings)["selected_method"] == "itemknn"
    candidates["popularity"]["ndcg"] = .054
    assert select_deployment(candidates, settings)["selected_method"] == "popularity"
    wrong = copy.deepcopy(settings)
    wrong["partition"] = "test"
    with pytest.raises(ValueError, match="protocol"):
        select_deployment(candidates, wrong)
    candidates.pop("selected_fixed")
    with pytest.raises(ValueError, match="candidate set"):
        select_deployment(candidates, settings)
