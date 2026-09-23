import threading

from src.execution import execute_bounded


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
