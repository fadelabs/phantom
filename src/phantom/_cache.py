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
from typing import TYPE_CHECKING, Any

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

    def _hash_audio(self, audio: AudioData, func_name: str) -> str:
        """Compute a SHA-256 cache key from audio content and function name.

        The key incorporates:
        - Raw sample bytes (captures all audio content)
        - Sample rate (same bytes at different rates = different audio)
        - Channel count (mono vs stereo reshape = different analysis)
        - Function name (prevents cross-function result collisions)
        """
        h = hashlib.sha256()
        h.update(audio.samples.tobytes())
        h.update(str(audio.sample_rate).encode())
        h.update(str(audio.num_channels).encode())
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


# Module-level singleton for use by analysis/comparison modules.
analysis_cache = AnalysisCache()
