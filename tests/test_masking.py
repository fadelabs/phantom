"""Tests for the frequency masking analysis module.

Covers MASK-01 through MASK-02.
All test audio is generated in-memory via inline fixtures.
"""

import numpy as np
import pytest

from phantom.audio import AudioData
from phantom.masking import (
    analyze_masking,
    analyze_masking_matrix,
    _compute_band_energies,
    MaskingResult,
    MaskingMatrixResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_audio(samples_1d: np.ndarray, sr: int) -> AudioData:
    """Wrap a 1D mono signal into an AudioData instance."""
    samples_2d = samples_1d.reshape(-1, 1)
    return AudioData(
        samples=samples_2d,
        sample_rate=sr,
        num_channels=1,
        duration=len(samples_1d) / sr,
        num_samples=len(samples_1d),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def overlapping_stems():
    """Two 1-second sines at 300 Hz and 350 Hz (both in 250_hz octave band).

    sr=44100, amplitude 0.5, float32. These should produce high overlap
    in the 250_hz band.
    """
    sr = 44100
    t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
    audio_a = _make_audio((0.5 * np.sin(2 * np.pi * 300 * t)).astype(np.float32), sr)
    audio_b = _make_audio((0.5 * np.sin(2 * np.pi * 350 * t)).astype(np.float32), sr)
    return audio_a, audio_b


@pytest.fixture
def non_overlapping_stems():
    """Two 1-second sines at 100 Hz (125_hz band) and 4000 Hz (4000_hz band).

    sr=44100, amplitude 0.5, float32. These should produce near-zero overlap.
    """
    sr = 44100
    t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
    audio_a = _make_audio((0.5 * np.sin(2 * np.pi * 100 * t)).astype(np.float32), sr)
    audio_b = _make_audio((0.5 * np.sin(2 * np.pi * 4000 * t)).astype(np.float32), sr)
    return audio_a, audio_b


@pytest.fixture
def identical_stems():
    """Two copies of 1-second broadband noise (seeded rng=42, amplitude 0.3).

    Identical stems should produce overlap_score near 1.0 for all bands
    with energy.
    """
    sr = 44100
    rng = np.random.default_rng(42)
    noise = rng.standard_normal(sr).astype(np.float32) * 0.3
    audio_a = _make_audio(noise.copy(), sr)
    audio_b = _make_audio(noise.copy(), sr)
    return audio_a, audio_b


# ---------------------------------------------------------------------------
# MASK-01: Pairwise Masking Analysis
# ---------------------------------------------------------------------------


class TestPairwiseMasking:
    """Verify pairwise frequency masking analysis."""

    def test_returns_model(self, overlapping_stems):
        """analyze_masking should return a MaskingResult model."""
        audio_a, audio_b = overlapping_stems
        result = analyze_masking(audio_a, audio_b)
        assert isinstance(result, MaskingResult)

    def test_result_keys(self, overlapping_stems):
        """Result should have exactly three top-level fields."""
        audio_a, audio_b = overlapping_stems
        result = analyze_masking(audio_a, audio_b)
        expected_keys = {"bands", "overall_severity", "overall_score"}
        assert set(result.model_dump().keys()) == expected_keys

    def test_overlapping_stems_high_band_score(self, overlapping_stems):
        """Two sines in the same octave band should produce high overlap in that band.

        The overall weighted average across 10 bands is naturally lower since
        only the overlapping band(s) contribute. We verify the 250_hz band
        specifically shows significant overlap (>0.3) and the overall score
        reflects meaningful masking (>0.1).
        """
        audio_a, audio_b = overlapping_stems
        result = analyze_masking(audio_a, audio_b)
        band_250 = next(b for b in result.bands if b.band == "250_hz")
        assert band_250.overlap_score > 0.3, (
            f"250_hz band overlap {band_250.overlap_score:.3f} should be > 0.3"
        )
        assert result.overall_score > 0.1

    def test_overlapping_stems_severity(self, overlapping_stems):
        """Two sines in same octave band should have at least 'low' overall severity.

        The overall weighted average across 10 bands dilutes single-band overlap.
        The key signal is that overlapping bands show 'moderate' or 'high' severity.
        """
        audio_a, audio_b = overlapping_stems
        result = analyze_masking(audio_a, audio_b)
        assert result.overall_severity in ("high", "moderate", "low")
        # At least one band should show moderate or high severity
        severe_bands = [b for b in result.bands if b.severity in ("high", "moderate")]
        assert len(severe_bands) >= 1, (
            "Expected at least one band with moderate/high severity"
        )

    def test_non_overlapping_stems_low_score(self, non_overlapping_stems):
        """Two sines in different octave bands should produce overall_score < 0.15."""
        audio_a, audio_b = non_overlapping_stems
        result = analyze_masking(audio_a, audio_b)
        assert result.overall_score < 0.15

    def test_identical_stems_high_overlap(self, identical_stems):
        """Identical stems should produce overlap_score near 1.0 for bands with energy."""
        audio_a, audio_b = identical_stems
        result = analyze_masking(audio_a, audio_b)
        # At least some bands should have high overlap
        high_overlap_bands = [b for b in result.bands if b.overlap_score > 0.9]
        assert len(high_overlap_bands) >= 5, (
            f"Expected at least 5 bands with overlap > 0.9, got {len(high_overlap_bands)}"
        )

    def test_near_silent_stem_a(self):
        """Near-silent stem A with audible stem B returns all overlap_scores at 0.0."""
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
        silent = _make_audio(
            (1e-5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32), sr
        )
        audible = _make_audio(
            (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32), sr
        )
        result = analyze_masking(silent, audible)
        for band in result.bands:
            assert band.overlap_score == 0.0
        assert result.overall_severity == "none"

    def test_both_stems_near_silent(self):
        """Both stems near-silent returns all overlap_scores at 0.0."""
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
        silent_a = _make_audio(
            (1e-5 * np.sin(2 * np.pi * 300 * t)).astype(np.float32), sr
        )
        silent_b = _make_audio(
            (1e-5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32), sr
        )
        result = analyze_masking(silent_a, silent_b)
        for band in result.bands:
            assert band.overlap_score == 0.0
        assert result.overall_severity == "none"

    def test_sample_rate_mismatch(self):
        """Sample rate mismatch (44100 vs 48000) raises AnalysisError."""
        from phantom.exceptions import AnalysisError

        sr1, sr2 = 44100, 48000
        t1 = np.linspace(0, 1.0, sr1, endpoint=False, dtype=np.float32)
        t2 = np.linspace(0, 1.0, sr2, endpoint=False, dtype=np.float32)
        audio_a = _make_audio(
            (0.5 * np.sin(2 * np.pi * 440 * t1)).astype(np.float32), sr1
        )
        audio_b = _make_audio(
            (0.5 * np.sin(2 * np.pi * 440 * t2)).astype(np.float32), sr2
        )
        with pytest.raises(AnalysisError, match="Sample rate mismatch"):
            analyze_masking(audio_a, audio_b)

    def test_empty_audio_raises(self):
        """Empty audio (0 samples) raises AnalysisError."""
        from phantom.exceptions import AnalysisError

        sr = 44100
        empty = AudioData(
            samples=np.zeros((0, 1), dtype=np.float32),
            sample_rate=sr,
            num_channels=1,
            duration=0.0,
            num_samples=0,
        )
        audible_t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
        audible = _make_audio(
            (0.5 * np.sin(2 * np.pi * 440 * audible_t)).astype(np.float32), sr
        )
        with pytest.raises(AnalysisError):
            analyze_masking(empty, audible)


# ---------------------------------------------------------------------------
# MASK-02: Per-Band Severity
# ---------------------------------------------------------------------------


class TestBandSeverity:
    """Verify per-band severity classification."""

    def test_bands_is_list_of_10(self, overlapping_stems):
        """Result 'bands' should be a list of 10 MaskingBand models."""
        audio_a, audio_b = overlapping_stems
        result = analyze_masking(audio_a, audio_b)
        assert isinstance(result.bands, list)
        assert len(result.bands) == 10

    def test_band_model_fields(self, overlapping_stems):
        """Each band should have exactly three fields: band, severity, overlap_score."""
        audio_a, audio_b = overlapping_stems
        result = analyze_masking(audio_a, audio_b)
        expected_keys = {"band", "severity", "overlap_score"}
        for band in result.bands:
            assert set(band.model_dump().keys()) == expected_keys

    def test_band_labels_match(self, overlapping_stems):
        """Band labels should match _BAND_LABELS from spectral.py."""
        from phantom.spectral import _BAND_LABELS

        audio_a, audio_b = overlapping_stems
        result = analyze_masking(audio_a, audio_b)
        actual_labels = [b.band for b in result.bands]
        assert actual_labels == _BAND_LABELS

    def test_severity_values_valid(self, overlapping_stems):
        """Severity values should be one of 'high', 'moderate', 'low', 'none'."""
        audio_a, audio_b = overlapping_stems
        result = analyze_masking(audio_a, audio_b)
        valid_severities = {"high", "moderate", "low", "none"}
        for band in result.bands:
            assert band.severity in valid_severities, (
                f"Band {band.band} has invalid severity '{band.severity}'"
            )

    def test_high_severity_threshold(self, identical_stems):
        """Band with overlap_score >= 0.6 should have severity 'high'."""
        audio_a, audio_b = identical_stems
        result = analyze_masking(audio_a, audio_b)
        for band in result.bands:
            if band.overlap_score >= 0.6:
                assert band.severity == "high", (
                    f"Band {band.band} has score {band.overlap_score:.3f} "
                    f"but severity '{band.severity}' (expected 'high')"
                )

    def test_moderate_severity_threshold(self, identical_stems):
        """Band with 0.3 <= overlap_score < 0.6 should have severity 'moderate'."""
        audio_a, audio_b = identical_stems
        result = analyze_masking(audio_a, audio_b)
        for band in result.bands:
            if 0.3 <= band.overlap_score < 0.6:
                assert band.severity == "moderate", (
                    f"Band {band.band} has score {band.overlap_score:.3f} "
                    f"but severity '{band.severity}' (expected 'moderate')"
                )

    def test_low_severity_threshold(self, identical_stems):
        """Band with 0.1 <= overlap_score < 0.3 should have severity 'low'."""
        audio_a, audio_b = identical_stems
        result = analyze_masking(audio_a, audio_b)
        for band in result.bands:
            if 0.1 <= band.overlap_score < 0.3:
                assert band.severity == "low", (
                    f"Band {band.band} has score {band.overlap_score:.3f} "
                    f"but severity '{band.severity}' (expected 'low')"
                )

    def test_none_severity_threshold(self, non_overlapping_stems):
        """Band with overlap_score < 0.1 should have severity 'none'."""
        audio_a, audio_b = non_overlapping_stems
        result = analyze_masking(audio_a, audio_b)
        for band in result.bands:
            if band.overlap_score < 0.1:
                assert band.severity == "none", (
                    f"Band {band.band} has score {band.overlap_score:.3f} "
                    f"but severity '{band.severity}' (expected 'none')"
                )


# ---------------------------------------------------------------------------
# Fixtures for MASK-03 / MASK-04
# ---------------------------------------------------------------------------


@pytest.fixture
def three_stems():
    """Three 1-second sines for matrix analysis.

    - stem 0: 300 Hz (in 250_hz band)
    - stem 1: 350 Hz (in 250_hz band — overlaps with stem 0)
    - stem 2: 4000 Hz (in 4000_hz band — no overlap with 0 or 1)

    sr=44100, amplitude 0.5, float32.
    """
    sr = 44100
    t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
    stem_0 = _make_audio((0.5 * np.sin(2 * np.pi * 300 * t)).astype(np.float32), sr)
    stem_1 = _make_audio((0.5 * np.sin(2 * np.pi * 350 * t)).astype(np.float32), sr)
    stem_2 = _make_audio((0.5 * np.sin(2 * np.pi * 4000 * t)).astype(np.float32), sr)
    return [stem_0, stem_1, stem_2]


# ---------------------------------------------------------------------------
# MASK-03: Multi-Stem Matrix Analysis
# ---------------------------------------------------------------------------


class TestMatrixMasking:
    """Verify multi-stem matrix masking analysis."""

    def test_three_stems_produces_three_pairs(self, three_stems):
        """3 stems should produce C(3,2) = 3 pairs."""
        result = analyze_masking_matrix(three_stems)
        assert result.pair_count == 3
        assert result.stem_count == 3
        assert len(result.pairs) == 3

    def test_two_stems_produces_one_pair(self, three_stems):
        """2 stems should produce C(2,2) = 1 pair."""
        result = analyze_masking_matrix(three_stems[:2])
        assert result.pair_count == 1
        assert result.stem_count == 2
        assert len(result.pairs) == 1

    def test_single_stem_empty_result(self, three_stems):
        """Single stem should produce 0 pairs, empty list."""
        result = analyze_masking_matrix([three_stems[0]])
        assert result.pair_count == 0
        assert result.stem_count == 1
        assert result.pairs == []

    def test_result_is_model(self, three_stems):
        """analyze_masking_matrix should return a MaskingMatrixResult model."""
        result = analyze_masking_matrix(three_stems)
        assert isinstance(result, MaskingMatrixResult)

    def test_result_keys(self, three_stems):
        """Result should have exactly three top-level fields."""
        result = analyze_masking_matrix(three_stems)
        expected_keys = {"pairs", "stem_count", "pair_count"}
        assert set(result.model_dump().keys()) == expected_keys

    def test_pair_entry_keys(self, three_stems):
        """Each pair entry should have the expected fields."""
        result = analyze_masking_matrix(three_stems)
        expected_keys = {
            "stem_a",
            "stem_b",
            "overall_severity",
            "overall_score",
            "bands",
        }
        for pair in result.pairs:
            assert set(pair.model_dump().keys()) == expected_keys

    def test_stem_indices_are_strings(self, three_stems):
        """stem_a and stem_b should be string keys matching 'stem_N' format (S-WR-01)."""
        result = analyze_masking_matrix(three_stems)
        for pair in result.pairs:
            assert isinstance(pair.stem_a, str)
            assert isinstance(pair.stem_b, str)
            assert pair.stem_a.startswith("stem_")
            assert pair.stem_b.startswith("stem_")

    def test_sample_rate_mismatch_in_matrix(self):
        """Sample rate mismatch among stems raises AnalysisError."""
        from phantom.exceptions import AnalysisError

        sr1, sr2 = 44100, 48000
        t1 = np.linspace(0, 1.0, sr1, endpoint=False, dtype=np.float32)
        t2 = np.linspace(0, 1.0, sr2, endpoint=False, dtype=np.float32)
        stem_a = _make_audio(
            (0.5 * np.sin(2 * np.pi * 300 * t1)).astype(np.float32), sr1
        )
        stem_b = _make_audio(
            (0.5 * np.sin(2 * np.pi * 350 * t2)).astype(np.float32), sr2
        )
        with pytest.raises(AnalysisError, match="Sample rate mismatch"):
            analyze_masking_matrix([stem_a, stem_b])

    def test_near_silent_stem_in_matrix(self):
        """Near-silent stem in matrix should not crash; pairs involving it have score 0.0."""
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
        silent_stem = _make_audio(
            (1e-5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32), sr
        )
        audible_stem = _make_audio(
            (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32), sr
        )
        result = analyze_masking_matrix([silent_stem, audible_stem])
        assert result.pair_count == 1
        pair = result.pairs[0]
        assert pair.overall_score == 0.0
        assert pair.overall_severity == "none"


# ---------------------------------------------------------------------------
# MASK-04: Pair Ranking by Severity
# ---------------------------------------------------------------------------


class TestMatrixRanking:
    """Verify pairs are sorted by overall_score descending."""

    def test_pairs_sorted_descending(self, three_stems):
        """Pairs should be sorted by overall_score descending."""
        result = analyze_masking_matrix(three_stems)
        scores = [p.overall_score for p in result.pairs]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], (
                f"Pair {i} score {scores[i]:.3f} < pair {i + 1} score {scores[i + 1]:.3f}"
            )

    def test_overlapping_pair_ranked_first(self, three_stems):
        """The overlapping pair (stems 0 and 1) should be ranked first."""
        result = analyze_masking_matrix(three_stems)
        first_pair = result.pairs[0]
        indices = {first_pair.stem_a, first_pair.stem_b}
        assert indices == {"stem_0", "stem_1"}, (
            f"Expected overlapping pair (stem_0, stem_1) first but got {indices}"
        )

    def test_pair_bands_format(self, three_stems):
        """Each pair's 'bands' should be a list of 10 MaskingBand models."""
        result = analyze_masking_matrix(three_stems)
        for pair in result.pairs:
            assert isinstance(pair.bands, list)
            assert len(pair.bands) == 10
            for band in pair.bands:
                assert set(band.model_dump().keys()) == {
                    "band",
                    "severity",
                    "overlap_score",
                }


# ---------------------------------------------------------------------------
# Band Energies Edge Cases (sub-frame audio)
# ---------------------------------------------------------------------------


class TestBandEnergiesEdgeCases:
    """Audio shorter than one FFT frame (4096 samples) should return zeros."""

    def test_short_audio_returns_zeros(self):
        """100-sample audio returns np.zeros(10)."""
        sr = 44100
        n_samples = 100
        t = np.linspace(0, n_samples / sr, n_samples, endpoint=False, dtype=np.float32)
        signal = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        result = _compute_band_energies(signal, sr)
        assert result.shape == (10,)
        assert np.all(result == 0.0)

    def test_just_under_frame_size_returns_zeros(self):
        """4095 samples (just under frame_size=4096) returns np.zeros(10)."""
        sr = 44100
        n_samples = 4095
        t = np.linspace(0, n_samples / sr, n_samples, endpoint=False, dtype=np.float32)
        signal = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        result = _compute_band_energies(signal, sr)
        assert result.shape == (10,)
        assert np.all(result == 0.0)

    def test_at_frame_size_returns_nonzero(self):
        """4096 samples (exactly frame_size) returns non-zero array."""
        sr = 44100
        n_samples = 4096
        t = np.linspace(0, n_samples / sr, n_samples, endpoint=False, dtype=np.float32)
        signal = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        result = _compute_band_energies(signal, sr)
        assert result.shape == (10,)
        assert np.sum(result) > 0

    def test_empty_audio_returns_zeros(self):
        """0-sample audio returns np.zeros(10)."""
        signal = np.array([], dtype=np.float32)
        result = _compute_band_energies(signal, 44100)
        assert result.shape == (10,)
        assert np.all(result == 0.0)
