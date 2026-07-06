"""Thread-safe LRU analysis cache keyed by audio content hash.

Eliminates redundant analysis work when the same audio is analyzed
multiple times (e.g., compare_to_reference running spectrum, loudness,
dynamics, and stereo on both files).

Cache keys are SHA-256 hashes of the audio sample bytes combined with
sample_rate, num_channels, and the analysis function name.
"""

from __future__ import annotations

import hashlib
import logging
import threading
from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from phantom.audio import AudioData

logger = logging.getLogger(__name__)

# Sentinel object used to distinguish a cache miss from a cached ``None`` result.
_MISSING = object()


class AnalysisCache:
    """Thread-safe LRU cache for analysis results.

    Parameters
    ----------
    max_entries:
        Maximum number of cached results before LRU eviction.
        Defaults to 8 (sufficient for a typical compare workflow
        analyzing 4 functions x 2 files).
    """

    def __init__(self, max_entries: int = 8) -> None:
        self._max_entries = max_entries
        self._store: OrderedDict[str, Any] = OrderedDict()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _content_digest(self, audio: AudioData) -> "hashlib._Hash":
        """Return a SHA-256 object pre-fed with the per-instance content bytes.

        The digest state (sample bytes + sample rate + channel count) is
        per-instance-constant — samples are never mutated after construction
        (established in Task 5's review) — so it is computed once and memoized
        on the ``AudioData`` instance under ``_content_hash``. This is the same
        ``audio.__dict__`` mechanism used for ``AudioData.mono`` (Task 5) and
        ``_true_peaks`` (Task 6), and avoids re-hashing the (potentially large)
        sample buffer on every cache ``get``/``put``.

        Callers must ``.copy()`` the returned object before feeding the
        per-function suffix so the memoized base state is never mutated.
        """
        cached = audio.__dict__.get("_content_hash")
        if cached is not None:
            return cached

        h = hashlib.sha256()
        h.update(audio.samples.tobytes())
        h.update(str(audio.sample_rate).encode())
        h.update(str(audio.num_channels).encode())
        audio.__dict__["_content_hash"] = h
        return h

    def _hash_audio(self, audio: AudioData, func_name: str) -> str:
        """Compute a SHA-256 cache key from audio content and function name.

        The key incorporates:
        - Raw sample bytes (captures all audio content)
        - Sample rate (same bytes at different rates = different audio)
        - Channel count (mono vs stereo reshape = different analysis)
        - Function name (prevents cross-function result collisions)

        The content-digest portion (sample bytes + rate + channels) is memoized
        per instance via :meth:`_content_digest`; only the cheap ``func_name``
        suffix is fed per call. The resulting key is byte-identical to feeding
        all four parts into a single fresh SHA-256, so the key format is
        unchanged.
        """
        h = self._content_digest(audio).copy()
        h.update(func_name.encode())
        return h.hexdigest()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, audio: AudioData, func_name: str) -> Any:
        """Retrieve a cached analysis result.

        Returns the module-level ``_MISSING`` sentinel on cache miss.
        On hit, the entry is moved to the end of the LRU queue
        (most recently used).
        """
        key = self._hash_audio(audio, func_name)
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
                logger.debug("Cache hit for %s (key=%s...)", func_name, key[:12])
                return self._store[key]
        return _MISSING

    def put(self, audio: AudioData, func_name: str, result: Any) -> None:
        """Store an analysis result in the cache.

        If the cache is full, the least-recently-used entry is evicted.
        """
        key = self._hash_audio(audio, func_name)
        with self._lock:
            if key in self._store:
                # Update existing entry and refresh position
                self._store.move_to_end(key)
                self._store[key] = result
            else:
                self._store[key] = result
                if len(self._store) > self._max_entries:
                    evicted_key, _ = self._store.popitem(last=False)
                    logger.debug(
                        "Cache evicted oldest entry (key=%s...)", evicted_key[:12]
                    )

    def clear(self) -> None:
        """Remove all cached entries.

        Used to measure the cold (cache-miss) analysis path in the timing
        harness, so successive runs don't measure cache hits.
        """
        with self._lock:
            self._store.clear()


# Module-level singleton for use by analysis/comparison modules.
analysis_cache = AnalysisCache()


def _cached_analysis(
    audio: AudioData, func_name: str, func: Callable[[AudioData], Any]
) -> Any:
    """Run an analysis function with cache lookup/store.

    Checks the shared ``analysis_cache`` first. On miss, runs ``func(audio)``
    and stores the result under ``func_name`` for subsequent calls with the
    same audio content. Composite tools (``full_diagnostic``,
    ``batch_diagnostic``), the ``analyze`` CLI, and the ``compare_*`` tools all
    route through this helper so they share per-analyzer results (P-01).
    """
    result = analysis_cache.get(audio, func_name)
    if result is not _MISSING:
        return result
    result = func(audio)
    analysis_cache.put(audio, func_name, result)
    return result
