"""Timing harness for full_diagnostic on a 60 s stereo file (synthetic audio).

Generates an in-memory 60 s stereo fixture (no real audio committed), then
reports two numbers:

- COLD: best-of-3 wall-clock time for full_diagnostic with the shared
  ``analysis_cache`` cleared before each run (and before warmup), so the timed
  calls measure the actual analysis cost — apples-to-apples with the Task 6
  baseline (2084.6 ms). This is the gate metric.
- WARM: one re-run on the same bytes WITHOUT clearing the cache, measuring the
  cache-hit path (a subsequent same-content tool call).

Used as before/after evidence for the true-peak-once optimization (P-02), the
content-hash memoization (P-01 follow-up), and re-used by later performance
tasks on this branch.

Run: uv run python scripts/bench_full_diagnostic.py
"""

import os
import time
import tempfile

import numpy as np
import soundfile as sf

from phantom._cache import analysis_cache
from phantom.server import full_diagnostic


def _time_cold(p: str) -> float:
    """Time one full_diagnostic with a freshly cleared cache (cold path)."""
    analysis_cache.clear()
    s = time.perf_counter()
    full_diagnostic(p)
    return time.perf_counter() - s


def _time_warm(p: str) -> float:
    """Time one full_diagnostic WITHOUT clearing (cache-hit path)."""
    s = time.perf_counter()
    full_diagnostic(p)
    return time.perf_counter() - s


def main() -> None:
    sr = 44100
    n = sr * 60
    t = np.arange(n) / sr
    rng = np.random.default_rng(0)
    left = (0.4 * np.sin(2 * np.pi * 220 * t) + 0.1 * rng.standard_normal(n)).astype(
        "float32"
    )
    right = (0.4 * np.sin(2 * np.pi * 223 * t) + 0.1 * rng.standard_normal(n)).astype(
        "float32"
    )
    with tempfile.TemporaryDirectory() as d:
        os.environ["PHANTOM_OUTPUT_DIR"] = d
        p = os.path.join(d, "bench.wav")
        sf.write(p, np.column_stack([left, right]), sr)

        # Warmup on the cold path (cache cleared) so JIT/import costs don't skew.
        _time_cold(p)

        # COLD: cache cleared before each run — measures true analysis cost.
        cold = min(_time_cold(p) for _ in range(3))

        # WARM: prime the cache once, then time a same-bytes re-run (cache hits).
        full_diagnostic(p)
        warm = min(_time_warm(p) for _ in range(3))

    print(f"full_diagnostic 60s stereo COLD (cache cleared): {cold * 1000:.1f} ms (best of 3)")
    print(f"full_diagnostic 60s stereo WARM (cache-hit path): {warm * 1000:.1f} ms (best of 3)")


if __name__ == "__main__":
    main()
