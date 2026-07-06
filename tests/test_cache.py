"""Tests for AnalysisCache — thread-safe LRU with content hashing."""

from __future__ import annotations

import hashlib
import threading

import numpy as np

import phantom._cache as cache_mod
from phantom._cache import _MISSING, AnalysisCache
from phantom.audio import AudioData


def _make_audio(samples_1d: np.ndarray, sr: int, num_channels: int = 1) -> AudioData:
    """Create an AudioData instance from a 1D sample array."""
    samples_2d = (
        samples_1d.reshape(-1, 1)
        if num_channels == 1
        else np.column_stack([samples_1d, samples_1d])
    )
    return AudioData(
        samples=samples_2d,
        sample_rate=sr,
        num_channels=num_channels,
        duration=len(samples_1d) / sr,
        num_samples=len(samples_1d),
    )


class TestCacheGetPut:
    """Basic get/put semantics."""

    def test_get_on_empty_cache_returns_missing(self) -> None:
        cache = AnalysisCache(max_entries=4)
        audio = _make_audio(np.zeros(100, dtype=np.float32), sr=44100)
        assert cache.get(audio, "spectrum") is _MISSING

    def test_put_then_get_returns_stored_result(self) -> None:
        cache = AnalysisCache(max_entries=4)
        audio = _make_audio(np.zeros(100, dtype=np.float32), sr=44100)
        result = {"centroid": 1200.0}
        cache.put(audio, "spectrum", result)
        assert cache.get(audio, "spectrum") == {"centroid": 1200.0}

    def test_different_func_name_returns_missing(self) -> None:
        """Same audio, different func_name should not collide."""
        cache = AnalysisCache(max_entries=4)
        audio = _make_audio(np.zeros(100, dtype=np.float32), sr=44100)
        cache.put(audio, "spectrum", {"centroid": 1200.0})
        assert cache.get(audio, "loudness") is _MISSING

    def test_clear_empties_the_cache(self) -> None:
        cache = AnalysisCache(max_entries=4)
        audio = _make_audio(np.zeros(100, dtype=np.float32), sr=44100)
        cache.put(audio, "spectrum", {"centroid": 1200.0})
        cache.clear()
        assert cache.get(audio, "spectrum") is _MISSING


class TestContentHashMemoization:
    """The expensive per-instance content digest is computed only once (P-01 follow-up).

    Two cache operations on the SAME AudioData instance must hash the sample
    bytes exactly once — the content digest is memoized on the instance, mirroring
    the ``AudioData.mono`` / ``_true_peaks`` memoization from Tasks 5–6.
    """

    def test_content_digest_computed_once_across_two_ops(self, monkeypatch) -> None:
        cache = AnalysisCache(max_entries=4)
        audio = _make_audio(np.full(100, 0.25, dtype=np.float32), sr=44100)

        calls = {"n": 0}
        real_sha256 = hashlib.sha256

        def _counting_sha256(*args, **kwargs):
            calls["n"] += 1
            return real_sha256(*args, **kwargs)

        # Patch the name where _cache looks it up.
        monkeypatch.setattr(cache_mod.hashlib, "sha256", _counting_sha256)

        # Two independent cache operations on the same instance: a put and a get.
        cache.put(audio, "spectrum", {"centroid": 1200.0})
        cache.get(audio, "spectrum")

        assert calls["n"] == 1, (
            "Expected the sample-bytes SHA-256 base to be constructed exactly once "
            "across two cache operations on the same AudioData instance (memoized "
            f"content digest), got {calls['n']}"
        )

    def test_memoized_key_matches_unmemoized_digest(self) -> None:
        """The memoized key must be byte-identical to a fresh full-content SHA-256.

        Guards against a key-format change: a cold instance (no memo) and the
        canonical one-pass computation must agree.
        """
        cache = AnalysisCache(max_entries=4)
        audio = _make_audio(np.full(100, 0.25, dtype=np.float32), sr=44100)

        # Canonical one-pass digest (the pre-optimization formula).
        h = hashlib.sha256()
        h.update(audio.samples.tobytes())
        h.update(str(audio.sample_rate).encode())
        h.update(str(audio.num_channels).encode())
        h.update("spectrum".encode())
        expected = h.hexdigest()

        assert cache._hash_audio(audio, "spectrum") == expected


class TestCacheKeyDifferentiation:
    """Different sample rates and channel counts produce distinct cache keys."""

    def test_different_sample_rate_different_key(self) -> None:
        cache = AnalysisCache(max_entries=4)
        samples = np.ones(100, dtype=np.float32) * 0.5
        audio_44 = _make_audio(samples, sr=44100)
        audio_48 = _make_audio(samples, sr=48000)

        cache.put(audio_44, "spectrum", {"rate": 44100})
        cache.put(audio_48, "spectrum", {"rate": 48000})

        assert cache.get(audio_44, "spectrum") == {"rate": 44100}
        assert cache.get(audio_48, "spectrum") == {"rate": 48000}

    def test_different_num_channels_different_key(self) -> None:
        cache = AnalysisCache(max_entries=4)
        samples = np.ones(100, dtype=np.float32) * 0.5
        audio_mono = _make_audio(samples, sr=44100, num_channels=1)
        audio_stereo = _make_audio(samples, sr=44100, num_channels=2)

        cache.put(audio_mono, "spectrum", {"ch": 1})
        cache.put(audio_stereo, "spectrum", {"ch": 2})

        assert cache.get(audio_mono, "spectrum") == {"ch": 1}
        assert cache.get(audio_stereo, "spectrum") == {"ch": 2}


class TestLRUEviction:
    """LRU eviction removes the oldest entry when max_entries exceeded."""

    def test_evicts_oldest_when_full(self) -> None:
        cache = AnalysisCache(max_entries=8)
        audios = []
        for i in range(9):
            audio = _make_audio(np.full(100, i * 0.1, dtype=np.float32), sr=44100)
            audios.append(audio)
            cache.put(audio, "spectrum", {"idx": i})

        # Entry 0 (oldest) should be evicted
        assert cache.get(audios[0], "spectrum") is _MISSING
        # Entry 8 (newest) should still be present
        assert cache.get(audios[8], "spectrum") == {"idx": 8}
        # Entry 1 should still be present (second oldest, but within limit)
        assert cache.get(audios[1], "spectrum") == {"idx": 1}

    def test_get_refreshes_lru_order(self) -> None:
        """Accessing an entry via get() should move it to the end, saving it from eviction."""
        cache = AnalysisCache(max_entries=3)

        audio_a = _make_audio(np.full(100, 0.1, dtype=np.float32), sr=44100)
        audio_b = _make_audio(np.full(100, 0.2, dtype=np.float32), sr=44100)
        audio_c = _make_audio(np.full(100, 0.3, dtype=np.float32), sr=44100)
        audio_d = _make_audio(np.full(100, 0.4, dtype=np.float32), sr=44100)

        cache.put(audio_a, "spectrum", "A")
        cache.put(audio_b, "spectrum", "B")
        cache.put(audio_c, "spectrum", "C")

        # Access A to refresh it — moves A to end
        assert cache.get(audio_a, "spectrum") == "A"

        # Add D — should evict B (now the oldest), not A
        cache.put(audio_d, "spectrum", "D")

        assert cache.get(audio_a, "spectrum") == "A"  # survived eviction
        assert cache.get(audio_b, "spectrum") is _MISSING  # evicted
        assert cache.get(audio_c, "spectrum") == "C"
        assert cache.get(audio_d, "spectrum") == "D"


class TestThreadSafety:
    """Concurrent access must not corrupt internal state."""

    def test_concurrent_put_get_no_exceptions(self) -> None:
        cache = AnalysisCache(max_entries=8)
        errors: list[Exception] = []

        def worker(thread_id: int) -> None:
            try:
                for i in range(50):
                    audio = _make_audio(
                        np.full(100, thread_id * 0.01 + i * 0.001, dtype=np.float32),
                        sr=44100,
                    )
                    cache.put(audio, f"func_{thread_id}", {"t": thread_id, "i": i})
                    cache.get(audio, f"func_{thread_id}")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Thread errors: {errors}"

    def test_concurrent_access_data_integrity(self) -> None:
        """Values retrieved must match what was stored — no cross-thread corruption."""
        cache = AnalysisCache(max_entries=64)
        results: dict[int, bool] = {}

        def worker(thread_id: int) -> None:
            audio = _make_audio(
                np.full(100, thread_id * 0.1, dtype=np.float32),
                sr=44100,
            )
            cache.put(audio, f"func_{thread_id}", {"id": thread_id})
            retrieved = cache.get(audio, f"func_{thread_id}")
            results[thread_id] = retrieved == {"id": thread_id}

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        for tid, ok in results.items():
            assert ok, f"Thread {tid} got corrupted data"
