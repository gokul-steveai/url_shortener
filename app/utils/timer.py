import time
from contextlib import contextmanager
from typing import Generator


class _Timer:
    """Holds the elapsed ms after the context exits."""
    elapsed: int = 0


@contextmanager
def timer() -> Generator[_Timer, None, None]:
    """
    Usage:
        with timer() as t:
            ...
        logger.info("elapsed_ms=%s", t.elapsed)
    """
    t = _Timer()
    start = time.perf_counter()
    yield t
    t.elapsed = round((time.perf_counter() - start) * 1000)
