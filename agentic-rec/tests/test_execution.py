import threading

from src.execution import RatePacer, execute_bounded


def test_failure_drains_inflight_without_dispatching_remaining():
    release = threading.Event()

    def worker(job):
        if job == 1:
            assert release.wait(timeout=5)
        return {"status": "generation_error" if job == 0 else "completed",
                "actual_known_usd": None if job == 0 else 0.001}

    iterator = execute_bounded(range(20), worker, 2)
    first = next(iterator)
    assert first[0] == 0
    release.set()
    results = [first, *iterator]
    assert {job for job, _ in results} == {0, 1}


def test_pacer_reserves_token_and_request_spacing(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr("src.execution.time.monotonic", lambda: clock[0])
    monkeypatch.setattr("src.execution.time.sleep", lambda delay: clock.__setitem__(0, clock[0] + delay))
    pacer = RatePacer(tokens_per_minute=60, requests_per_minute=30)
    assert pacer.wait(3, 1) == 0
    assert pacer.wait(0, 0) == 4000
    assert pacer.wait(0, 0) == 2000
