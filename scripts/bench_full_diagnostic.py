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
from phantom._settings import analysis_settings
from phantom.audio import load_audio
from phantom.server import full_diagnostic
from phantom.spectral import _octave_band_energies, analyze_spectrum


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


def _timed(fn) -> float:
    """Return the wall-clock seconds to run ``fn`` once."""
    s = time.perf_counter()
    fn()
    return time.perf_counter() - s


def _probe_spectral(p: str) -> None:
    """P-05 gate probe: time analyze_spectrum vs its octave-band pass alone.

    ``analyze_spectrum`` makes two framed FFT passes over the same mono signal:
    the main 2048/1024 spectral pass and the octave-band 4096/2048 pass (now in
    ``_octave_band_energies``, shared with masking). The audit (P-05) proposed
    fusing these into a single pass, but only if the band pass is a material
    share of spectral time. This probe measures that share so the gate can be
    decided from data.

    Loads the fixture once, then times both on the same in-memory mono signal
    (best of 3 each, after a warmup) so import/JIT costs don't skew the split.
    """
    audio = load_audio(p)
    mono = audio.mono
    sr = audio.sample_rate

    # Warmup both paths so Essentia/JIT costs don't land in the timed runs.
    # The octave-band pass takes the effective settings for its frame sizes
    # (C.1); defaults reproduce the pre-C.1 geometry.
    settings = analysis_settings()
    analyze_spectrum(audio)
    _octave_band_energies(mono, sr, settings)

    spectral_s = min(_timed(lambda: analyze_spectrum(audio)) for _ in range(3))
    band_s = min(_timed(lambda: _octave_band_energies(mono, sr, settings)) for _ in range(3))

    share = (band_s / spectral_s * 100.0) if spectral_s > 0 else 0.0
    print(f"P-05 probe -- analyze_spectrum 60s: {spectral_s * 1000:.1f} ms (best of 3)")
    print(f"P-05 probe -- octave-band pass only: {band_s * 1000:.1f} ms (best of 3)")
    print(f"P-05 probe -- band pass share of spectral: {share:.1f}%")


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

        print(
            f"full_diagnostic 60s stereo COLD (cache cleared): {cold * 1000:.1f} ms (best of 3)"
        )
        print(
            f"full_diagnostic 60s stereo WARM (cache-hit path): {warm * 1000:.1f} ms (best of 3)"
        )

        # P-05 gate probe: split analyze_spectrum time into its two FFT passes.
        _probe_spectral(p)


if __name__ == "__main__":
    main()
