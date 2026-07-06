"""Timing harness for full_diagnostic on a 60 s stereo file (synthetic audio).

Generates an in-memory 60 s stereo fixture (no real audio committed), warms
up once, then reports the best-of-3 wall-clock time for full_diagnostic.

Used as before/after evidence for the true-peak-once optimization (P-02) and
re-used by later performance tasks on this branch.

Run: uv run python scripts/bench_full_diagnostic.py
"""

import os
import time
import tempfile

import numpy as np
import soundfile as sf

from phantom.server import full_diagnostic


def _time_once(p: str) -> float:
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
        full_diagnostic(p)  # warmup
        best = min(_time_once(p) for _ in range(3))
    print(f"full_diagnostic 60s stereo: {best * 1000:.1f} ms (best of 3)")


if __name__ == "__main__":
    main()
