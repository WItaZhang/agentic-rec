"""Pure, target-free evidence construction; token truncation is supplied by the caller."""

import json


def build_prompt(request, candidates, metadata, plan, config, truncate, instructions):
    if plan not in ("R1", "R2", "R3", "R4"):
        raise ValueError("Unknown evidence plan")
    if request.request_id != candidates.request_id or request.prediction_time != candidates.prediction_time:
        raise ValueError("Candidate snapshot does not belong to request")
    long_history, attributes = plan in ("R2", "R4"), plan in ("R3", "R4")
    aliases = {f"C{i:03d}": item for i, item in enumerate(candidates.item_ids, 1)}
    truncations = 0

    def shorten(text, limit):
        nonlocal truncations
        value, cut = truncate(str(text or ""), limit)
        truncations += int(cut)
        return value

    def identity(item):
        value = {"title": shorten(metadata.get(item, {}).get("title", item), config["title_tokens"])}
        if attributes:
            value["categories"] = shorten(json.dumps(metadata.get(item, {}).get("categories") or [],
                                                     ensure_ascii=False), config["category_tokens"])
        return value

    rows = [{"id": alias, **identity(item)} for alias, item in aliases.items()]
    recent_count = config["recent_events"]
    retained = config["max_history_events"] if long_history else recent_count
    history = [{**identity(event.item), "rating": event.rating,
                "age_days": (request.prediction_time - event.timestamp) // 86400000,
                "review": shorten(event.text, config["review_tokens"])}
               for event in request.history[-retained:]]
    data = {"candidate_order": "descending frozen base-model score", "candidates": rows,
            "history": history, "history_order": "oldest to newest", "top_k": config["k"]}
    schema = {"type": "object", "properties": {"item_ids": {"type": "array",
              "items": {"type": "string", "enum": list(aliases)},
              "minItems": config["k"], "maxItems": config["k"]}},
              "required": ["item_ids"], "additionalProperties": False}
    return ([{"role": "system", "content": instructions},
             {"role": "user", "content": json.dumps(data, ensure_ascii=False, separators=(",", ":"))}],
            schema, aliases, {"evidence_plan": plan, "history_available": len(request.history),
                             "history_provided": len(history), "attributes": attributes,
                             "field_truncations": truncations,
                             "candidate_hash": candidates.content_hash,
                             "metadata_visibility": "snapshot_assumed_static",
                             "history_event_ids": [e.event_id for e in request.history[-retained:]],
                             "tool_calls": 2 + int(attributes)})
