"""Bounded call execution; drain in-flight responses before stopping on a failure."""

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait


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
