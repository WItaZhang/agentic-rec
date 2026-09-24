from src.failure_analysis import choose_case_ids, error_tags


def test_error_classes_separate_candidate_misses_from_reranking_losses():
    base = {"hr": 1, "ndcg": 0.5}
    outcome = {"hr": 0, "ndcg": 0, "candidate_recall": 1, "history_count": 2}
    assert error_tags(base, outcome, {"status": "completed"}) == ["baseline_hit_lost", "rank_quality_loss"]
    base = {"hr": 0, "ndcg": 0}
    outcome.update(candidate_recall=0, cold_item=True, history_count=0, repair_errors=["short_output"])
    assert error_tags(base, outcome, {"status": "batch_error"}) == [
        "cold_target", "retrieval_miss", "no_history_miss", "api_failure", "ranking_repair"]


def test_example_selection_does_not_prefer_bigger_quality_losses():
    tagged = {f"q{i}": ["loss"] for i in range(40)}
    selected = choose_case_ids(tagged, 3, 42)
    assert selected == choose_case_ids(dict(reversed(list(tagged.items()))), 3, 42)
    assert len(selected["loss"]) == 3
