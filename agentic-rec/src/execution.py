"""Bounded call execution; drain in-flight responses before stopping on a failure."""

import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait


class RatePacer:
    """Conservative smooth token pacing; queue time is observable and separately logged."""
    def __init__(self, tokens_per_minute, requests_per_minute):
        if min(tokens_per_minute, requests_per_minute) <= 0:
            raise ValueError("Positive rate limits required")
        self.tokens_per_minute = tokens_per_minute
        self.requests_per_minute = requests_per_minute
        self.next_start = time.monotonic()
        self.lock = threading.Lock()

    def wait(self, input_tokens, max_output_tokens):
        with self.lock:
            now = time.monotonic()
            start = max(now, self.next_start)
            self.next_start = start + max(60 / self.requests_per_minute,
                (input_tokens + max_output_tokens) * 60 / self.tokens_per_minute)
        delay = start - now
        if delay > 0:
            time.sleep(delay)
        return delay * 1000


def execute_bounded(jobs, worker, concurrency):
    pending_jobs = iter(jobs)
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        active = {}

        def submit():
            try:
                job = next(pending_jobs)
            except StopIteration:
                return False
            active[pool.submit(worker, job)] = job
            return True

        for _ in range(concurrency):
            if not submit():
                break
        failed = False
        while active:
            done, _ = wait(active, return_when=FIRST_COMPLETED)
            # Observe the whole completed batch before scheduling any replacements.
            results = []
            for future in done:
                job = active.pop(future)
                record = future.result()
                failed |= record["status"] in ("count_error", "generation_error")
                failed |= record.get("actual_known_usd") is None
                results.append((job, record))
            yield from results
            if not failed:
                for _ in results:
                    submit()
