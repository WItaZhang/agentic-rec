import json

from src.data import ReviewEvent
from src.evidence import build_prompt
from src.protocol import CandidateSnapshot, RequestView


def test_evidence_sources_change_without_candidate_or_label_change():
    events = tuple(ReviewEvent(i, "u", f"h{i}", 5, f"e{i}", f"review{i}") for i in range(1, 5))
    view = RequestView("q", "u", 5, events, "validation")
    snapshot = CandidateSnapshot("q", ("a", "b"), (2.0, 1.0), "model", 5)
    meta = {"a": {"title": "A", "categories": ["science"], "average_rating": 5},
            "b": {"title": "B", "categories": ["sports"]}}
    config = {"title_tokens": 40, "category_tokens": 48, "review_tokens": 128,
              "recent_events": 1, "max_history_events": 3, "k": 2}
    outputs = [build_prompt(view, snapshot, meta, plan, config, lambda s, n: (s, False), "rank")
               for plan in ("R1", "R2", "R3", "R4")]
    data = [json.loads(output[0][1]["content"]) for output in outputs]
    assert [len(d["history"]) for d in data] == [1, 3, 1, 3]
    assert all([r["id"] for r in d["candidates"]] == ["C001", "C002"] for d in data)
    assert "categories" not in data[0]["candidates"][0]
    assert data[2]["candidates"][0]["categories"] == '["science"]'
    assert all("average_rating" not in output[0][1]["content"] for output in outputs)
    assert all(output[3]["candidate_hash"] == snapshot.content_hash for output in outputs)
    assert "review1" not in outputs[3][0][1]["content"]


def test_shuffled_categories_keep_candidate_identity_and_exact_text_multiset():
    snapshot = CandidateSnapshot('q', tuple(f'i{i}' for i in range(20)), tuple(range(20)), 'model', 10)
    view = RequestView('q', 'u', 10, (), 'validation')
    metadata = {item: {'title': item, 'categories': [f'category {i}']} for i, item in enumerate(snapshot.item_ids)}
    config = {'title_tokens': 40, 'category_tokens': 48, 'review_tokens': 128,
              'recent_events': 1, 'max_history_events': 20, 'k': 10, 'category_permutation_seed': 42}
    def build(plan):
        return json.loads(build_prompt(view, snapshot, metadata, plan, config, lambda s, n: (s, False), 'rank')[0][1]['content'])
    original, shuffled = build('R4'), build('S4')
    assert [(r['id'], r['title']) for r in original['candidates']] == [(r['id'], r['title']) for r in shuffled['candidates']]
    def categories(value):
        return [r['categories'] for r in value['candidates']]
    assert sorted(categories(original)) == sorted(categories(shuffled))
    assert categories(original) != categories(shuffled)
    assert build('S4') == shuffled
    assert original['history'] == shuffled['history']
