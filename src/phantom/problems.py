"""Problem detection functions.

Provides detect_problems() which accepts an AudioData object and scans
for audio production problems, returning a severity-ranked list of
detected issues.

Uses numpy for time-domain checks (clipping, DC offset, noise floor, SNR),
Essentia for specialized algorithms (TruePeakDetector, HumDetector), and
scipy for frequency-domain analysis (sibilance, mud, harshness, resonances,
lossy codec detection).
Near-silent audio returns an empty problems list with clean=True (per D-12).
"""

from __future__ import annotations

import numpy as np
import essentia.standard as es
import scipy.signal as sig
from scipy.fft import rfft, rfftfreq

from pydantic import BaseModel, ConfigDict

from phantom.audio import AudioData
from phantom._bands import FlatMapModel
from phantom._settings import AnalysisSettings, analysis_settings
from phantom._utils import guarded_mono, wrap_errors

_SEVERITY_SORT_ORDER = {"dealbreaker": 0, "significant": 1, "moderate": 2, "minor": 3}

# All detection thresholds live in AnalysisSettings (C.1), one knob per
# detector (PROB-01..13); see phantom._settings for names, defaults, and env
# overrides.


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ProblemDetails(FlatMapModel):
    """Typed per-problem detail fields (C.2).

    Declares every key the built-in detectors write (one field per
    detector); fields serialize under their own names with unset fields
    dropped, so ``model_dump()`` output is byte-identical to the raw dicts
    this replaces -- including partial detail sets (e.g. mono dc_offset
    carries no ``channel``). Unknown keys pass through as extras (matching
    the band maps' policy) so forward-compatible detail vocabulary from
    callers or future detectors is never dropped at serialization.
    """

    model_config = ConfigDict(extra="allow")

    # PROB-01 clipping
    clipped_samples: int | None = None
    clipped_percent: float | None = None
    # PROB-02 dc offset (channel present only for stereo)
    dc_offset: float | None = None
    channel: str | None = None
    # PROB-03 inter-sample peaks
    true_peak_dbtp: float | None = None
    sample_peak_dbfs: float | None = None
    overshoot_db: float | None = None
    # PROB-04/05 noise floor + SNR (share values). Declared in the SNR
    # detector's construction order so the serialized key order matches the
    # raw dicts exactly; the noise-floor item carries only noise_floor_dbfs.
    snr_db: float | None = None
    signal_rms_dbfs: float | None = None
    noise_floor_dbfs: float | None = None
    quality: str | None = None
    # PROB-06 hum
    primary_frequency_hz: float | None = None
    primary_salience: float | None = None
    num_components: int | None = None
    frequencies_hz: list[float] | None = None
    # PROB-07/08/09 band excess
    band_energy_db: float | None = None
    overall_energy_db: float | None = None
    excess_db: float | None = None
    # PROB-10 resonances
    num_resonances: int | None = None
    resonances: list[dict[str, float]] | None = None
    # PROB-13 lossy codec
    shelf_drop_db: float | None = None
    energy_14_16khz_db: float | None = None
    energy_16_20khz_db: float | None = None
    # batch sample-rate mismatch (inject_sample_rate_mismatch)
    sample_rates: dict[str, int] | None = None


class ProblemItem(BaseModel):
    """A single detected audio problem."""

    type: str
    severity: str
    message: str
    details: ProblemDetails


class ProblemSummary(BaseModel):
    """Severity count summary."""

    dealbreaker: int = 0
    significant: int = 0
    moderate: int = 0
    minor: int = 0
    total: int = 0


class ProblemsResult(BaseModel):
    """Result of audio problem detection."""

    problems: list[ProblemItem] = []
    clean: bool = True
    summary: ProblemSummary = ProblemSummary()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _empty_result() -> ProblemsResult:
    """Return a clean result with no problems detected."""
    return ProblemsResult()


def build_summary(problems: list[ProblemItem]) -> ProblemSummary:
    """Build a severity-count summary from a list of problem items."""
    summary = {
        "dealbreaker": 0,
        "significant": 0,
        "moderate": 0,
        "minor": 0,
        "total": 0,
    }
    for p in problems:
        sev = p.severity
        if sev in summary:
            summary[sev] += 1
    summary["total"] = len(problems)
    return ProblemSummary(**summary)


def inject_sample_rate_mismatch(
    problems_result: ProblemsResult,
    sample_rates: dict,
) -> ProblemsResult:
    """Prepend a sample-rate-mismatch dealbreaker to a ProblemsResult (P-10).

    Shared between the batch_diagnostic MCP tool (server.py) and the CLI batch
    path (cli/analyze.py). Callers detect the mismatch (len(unique_rates) > 1)
    and iterate over stems; this helper builds the dealbreaker ProblemItem from
    ``sample_rates``, prepends it to ``problems_result.problems``, and returns a
    freshly-built ProblemsResult with clean=False and an updated summary.

    Args:
        problems_result: The stem's existing ProblemsResult to augment.
        sample_rates: Mapping of stem name -> sample rate (Hz) across the batch.

    Returns:
        A new ProblemsResult with the mismatch item first, clean=False, and a
        summary rebuilt via build_summary. The input is not mutated.
    """
    mismatch_detail = {name: int(rate) for name, rate in sample_rates.items()}
    mismatch = ProblemItem(
        type="sample_rate_mismatch",
        severity="dealbreaker",
        message=f"Sample rate mismatch across stems: {mismatch_detail}",
        details={"sample_rates": mismatch_detail},
    )
    all_problems = [mismatch] + list(problems_result.problems)
    return ProblemsResult(
        problems=all_problems,
        clean=False,
        summary=build_summary(all_problems),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@wrap_errors("Problem detection failed")
def detect_problems(
    audio: AudioData, settings: AnalysisSettings | None = None
) -> ProblemsResult:
    """Detect audio production problems and return severity-ranked results.

    All detection thresholds are AnalysisSettings-tunable (C.1); *settings*
    defaults to the per-call env resolution.

    Runs all detection checks internally (D-01). Returns a ProblemsResult
    with problems (list of ProblemItem), clean (bool), and summary
    (ProblemSummary with counts per severity tier).

    Args:
        audio: AudioData object to analyze.

    Returns:
        ProblemsResult with problems, clean, and summary fields.

    Raises:
        AnalysisError: If analysis fails or audio has 0 samples.
    """
    effective = settings if settings is not None else analysis_settings()

    # Empty/silence guards (B.2): mono, or None when near-silent (D-12).
    mono = guarded_mono(audio, "Problem detection failed")
    if mono is None:
        return _empty_result()

    problems: list[ProblemItem] = []
    problems.extend(_detect_clipping(mono, effective))
    problems.extend(_detect_dc_offset(audio, effective))
    problems.extend(_detect_inter_sample_peaks(audio, effective))
    # Noise floor + SNR are ~half identical (P10 block-RMS percentile and the
    # dynamic-spread guard); both inputs are memoized on AudioData (A.2).
    problems.extend(
        _detect_noise_and_snr(audio.block_rms_db, audio.mono_rms, effective)
    )
    problems.extend(_detect_hum(mono, audio.sample_rate))

    # Pre-compute shared FFT results for frequency-domain detectors.
    # _spectral_flatness (frame_size=4096) is used by all 3 _detect_band_excess
    # calls; _average_power_spectrum (frame_size=8192) is used by both
    # _detect_resonances and _detect_lossy_codec. Pre-computing eliminates
    # 4 redundant FFT passes (3 flatness + 1 power spectrum).
    flatness = _spectral_flatness(mono, frame_size=effective.flatness_frame_size)
    spectrum_8k = _average_power_spectrum(
        mono, effective.spectrum_frame_size, audio.sample_rate
    )

    # Frequency-domain detectors (band excess via parametric function)
    problems.extend(
        _detect_band_excess(
            mono,
            audio.sample_rate,
            5000.0,
            10000.0,
            "sibilance",
            "sibilance",
            "5-10kHz",
            spectral_flatness=flatness,
            settings=effective,
        )
    )
    problems.extend(
        _detect_band_excess(
            mono,
            audio.sample_rate,
            200.0,
            500.0,
            "mud",
            "mud",
            "200-500Hz",
            spectral_flatness=flatness,
            settings=effective,
        )
    )
    problems.extend(
        _detect_band_excess(
            mono,
            audio.sample_rate,
            2000.0,
            4000.0,
            "harshness",
            "harshness",
            "2-4kHz",
            spectral_flatness=flatness,
            settings=effective,
        )
    )
    problems.extend(
        _detect_resonances(
            mono, audio.sample_rate, power_spectrum=spectrum_8k, settings=effective
        )
    )
    problems.extend(
        _detect_lossy_codec(
            mono, audio.sample_rate, power_spectrum=spectrum_8k, settings=effective
        )
    )

    # Sort by severity: dealbreaker first, minor last
    problems.sort(key=lambda p: _SEVERITY_SORT_ORDER[p.severity])

    return ProblemsResult(
        problems=problems,
        clean=len(problems) == 0,
        summary=build_summary(problems),
    )


# ---------------------------------------------------------------------------
# Private detectors -- time domain
# ---------------------------------------------------------------------------


def _detect_clipping(mono: np.ndarray, settings: AnalysisSettings) -> list[ProblemItem]:
    """Detect samples at digital maximum (+/-1.0). PROB-01."""
    clipped_mask = np.abs(mono) >= settings.clipping_threshold
    n_clipped = int(np.sum(clipped_mask))
    if n_clipped == 0:
        return []
    pct = 100.0 * n_clipped / len(mono)
    return [
        ProblemItem(
            type="clipping",
            severity="dealbreaker",
            message=(
                f"Clipping detected: {n_clipped} samples "
                f"({pct:.2f}%) at digital maximum."
            ),
            details={
                "clipped_samples": n_clipped,
                "clipped_percent": round(pct, 4),
            },
        )
    ]


def _detect_dc_offset(
    audio: AudioData, settings: AnalysisSettings
) -> list[ProblemItem]:
    """Detect non-zero DC offset. PROB-02.

    Checks DC per channel so antiphase DC (L=+x, R=-x), which cancels in the
    mono mixdown, is still caught (P-13). Mono files are checked exactly as
    before — the flagged item's shape is byte-identical to the pre-P-13 output.
    Stereo files additionally emit a "channel" key naming the worst channel;
    this is an additive detail field (existing keys preserved with the same
    semantics).
    """
    if audio.num_channels == 1:
        dc = float(np.mean(audio.mono))
        if (
            abs(dc) < settings.dc_offset_threshold
        ):  # 0.05% FS — above 24-bit noise floor
            return []
        return [
            ProblemItem(
                type="dc_offset",
                severity="minor",
                message=f"DC offset detected: {dc:.6f} (mean sample value).",
                details={"dc_offset": round(dc, 8)},
            )
        ]

    # Stereo: flag if EITHER channel exceeds the threshold. Report the channel
    # with the largest magnitude DC (the worst offender).
    left_dc = float(np.mean(audio.left))
    right_dc = float(np.mean(audio.right))
    if (
        abs(left_dc) < settings.dc_offset_threshold
        and abs(right_dc) < settings.dc_offset_threshold
    ):
        return []
    if abs(left_dc) >= abs(right_dc):
        dc, channel = left_dc, "left"
    else:
        dc, channel = right_dc, "right"
    return [
        ProblemItem(
            type="dc_offset",
            severity="minor",
            message=(
                f"DC offset detected: {dc:.6f} (mean sample value, {channel} channel)."
            ),
            details={"dc_offset": round(dc, 8), "channel": channel},
        )
    ]


def _detect_inter_sample_peaks(
    audio: AudioData, settings: AnalysisSettings
) -> list[ProblemItem]:
    """Detect inter-sample peaks exceeding the overshoot threshold. PROB-03."""
    # Reuse the per-file true-peak computation memoized by channel_true_peaks
    # (shared with analyze_loudness) instead of running the x4-oversampled FIR
    # a second time (P-02, P-06).
    from phantom._truepeak import channel_true_peaks

    eps = np.finfo(np.float32).eps
    channel_results = [(sp, tp) for (sp, tp) in channel_true_peaks(audio) if sp >= eps]

    if not channel_results:
        return []

    # Compute overshoot per channel, report worst case
    worst_overshoot_db = 0.0
    worst_sample_peak = 0.0
    worst_true_peak = 0.0
    for sp, tp in channel_results:
        overshoot = float(20 * np.log10((tp + eps) / (sp + eps)))
        if overshoot > worst_overshoot_db:
            worst_overshoot_db = overshoot
            worst_sample_peak = sp
            worst_true_peak = tp

    overshoot_db = worst_overshoot_db
    sample_peak = worst_sample_peak
    true_peak = worst_true_peak

    if overshoot_db <= settings.isp_overshoot_threshold_db:
        return []

    true_peak_dbtp = float(20 * np.log10(true_peak + eps))
    severity = (
        "significant" if true_peak_dbtp > settings.isp_severe_dbtp else "moderate"
    )

    return [
        ProblemItem(
            type="inter_sample_peak",
            severity=severity,
            message=(
                f"Inter-sample peaks detected: true peak is {overshoot_db:.1f} dB "
                f"above sample peak ({true_peak_dbtp:.1f} dBTP)."
            ),
            details={
                "true_peak_dbtp": round(true_peak_dbtp, 2),
                "sample_peak_dbfs": round(float(20 * np.log10(sample_peak + eps)), 2),
                "overshoot_db": round(overshoot_db, 2),
            },
        )
    ]


def _noise_floor_estimate(
    block_rms_db: list[float], settings: AnalysisSettings
) -> float | None:
    """Return the P10 noise floor when it is measurable, else None.

    Shared by the noise-floor and SNR detectors (PROB-04/05), which are
    ~half identical: both need the P10 block-RMS percentile and both must
    reject signals whose block levels are too uniform to separate noise
    from signal. Returns ``None`` when there is no meaningful estimate
    (too few blocks, or dynamic spread below
    ``settings.dynamic_spread_min_db``).
    """
    if len(block_rms_db) < 4:
        return None

    noise_floor_db = float(np.percentile(block_rms_db, 10))

    # If the signal has low dynamic range (uniform level), block RMS percentile
    # reflects the signal level itself, not actual noise. Only flag noise floor
    # when there is enough level variation to distinguish noise from signal.
    dynamic_spread = float(np.percentile(block_rms_db, 90) - noise_floor_db)
    if dynamic_spread < settings.dynamic_spread_min_db:
        return None

    return noise_floor_db


def _detect_noise_and_snr(
    block_rms_db: list[float],
    signal_rms: float,
    settings: AnalysisSettings,
) -> list[ProblemItem]:
    """Detect elevated noise floor and poor SNR (PROB-04, PROB-05).

    Formerly two functions that each re-ran the block-RMS loop and guarded
    it identically. Both inputs now come from AudioData's memoized
    ``block_rms_db`` and ``mono_rms`` (A.2, review F4), so the merged
    detector adds no array recomputation. Item order is preserved (noise
    floor before SNR), so within-severity output order is unchanged.
    """
    noise_floor_db = _noise_floor_estimate(block_rms_db, settings)
    if noise_floor_db is None:
        return []

    items: list[ProblemItem] = []

    # -- Noise floor (PROB-04) --
    if noise_floor_db >= settings.noise_floor_moderate_db:
        severity = "moderate"
        msg = (
            f"Elevated noise floor: {noise_floor_db:.1f} dBFS "
            "(above -50 dBFS threshold)."
        )
    elif noise_floor_db >= settings.noise_floor_minor_db:
        severity = "minor"
        msg = (
            f"Noise floor at {noise_floor_db:.1f} dBFS "
            "(acceptable but not professional-grade)."
        )
    else:
        severity, msg = None, None  # Below -60 dBFS is professional quality

    if severity is not None:
        items.append(
            ProblemItem(
                type="noise_floor",
                severity=severity,
                message=msg,
                details={"noise_floor_dbfs": round(noise_floor_db, 1)},
            )
        )

    # -- SNR (PROB-05) --
    # Upper-bound approximation: overall RMS includes noise, so true SNR
    # is lower.
    signal_rms_db = float(20.0 * np.log10(signal_rms + 1e-10))
    snr_db = signal_rms_db - noise_floor_db

    if snr_db < settings.snr_professional_db:
        if snr_db < settings.snr_poor_db:
            severity = "significant"
            quality = "poor"
        else:
            severity = "minor"
            quality = "acceptable"

        items.append(
            ProblemItem(
                type="snr",
                severity=severity,
                message=(
                    f"SNR is {snr_db:.1f} dB ({quality}). "
                    f"Signal RMS: {signal_rms_db:.1f} dBFS, "
                    f"noise floor: {noise_floor_db:.1f} dBFS."
                ),
                details={
                    "snr_db": round(snr_db, 1),
                    "signal_rms_dbfs": round(signal_rms_db, 1),
                    "noise_floor_dbfs": round(noise_floor_db, 1),
                    "quality": quality,
                },
            )
        )

    return items


def _detect_hum(mono: np.ndarray, sample_rate: int) -> list[ProblemItem]:
    """Detect mains hum at 50/60Hz and harmonics. PROB-06."""
    duration = len(mono) / sample_rate
    if duration < 2.0:
        # Audio shorter than 2s has insufficient data for reliable PSD
        # measurement by HumDetector — return empty results rather than
        # risking Essentia parameter conflicts at boundary durations.
        return []

    time_window = min(duration / 2, 10.0)
    hd = es.HumDetector(
        sampleRate=sample_rate,
        minimumFrequency=22.5,
        maximumFrequency=400,
        minimumDuration=max(0.5, duration * 0.1),
        numberHarmonics=5,
        timeWindow=time_window,
    )
    _, frequencies, saliences, _starts, _ends = hd(mono)

    if len(frequencies) == 0:
        return []

    # Filter for mains hum (50Hz or 60Hz +/- 5Hz tolerance)
    hum_freqs: list[tuple[float, float]] = []
    for f, s in zip(frequencies, saliences):
        matched = False
        for mains in (50, 60):
            if matched:
                break
            for harmonic in range(1, 6):
                target = mains * harmonic
                if abs(f - target) < 5:
                    hum_freqs.append((float(f), float(s)))
                    matched = True
                    break

    if not hum_freqs:
        return []

    primary_freq = hum_freqs[0][0]
    primary_salience = hum_freqs[0][1]

    return [
        ProblemItem(
            type="hum",
            severity="significant",
            message=(
                f"Mains hum detected at {primary_freq:.1f} Hz "
                f"(salience: {primary_salience:.2f}). "
                f"Found {len(hum_freqs)} hum component(s)."
            ),
            details={
                "primary_frequency_hz": round(primary_freq, 1),
                "primary_salience": round(primary_salience, 3),
                "num_components": len(hum_freqs),
                "frequencies_hz": [round(f, 1) for f, _ in hum_freqs],
            },
        )
    ]


# ---------------------------------------------------------------------------
# Private detectors -- frequency domain
# ---------------------------------------------------------------------------


def _band_energy_db(mono: np.ndarray, sr: int, low_hz: float, high_hz: float) -> float:
    """Compute RMS energy in dBFS for a frequency band using Butterworth bandpass."""
    nyq = sr / 2.0
    if low_hz >= nyq:
        return -120.0  # Band entirely above Nyquist
    hi_clamped = min(high_hz, nyq * 0.99)
    lo_norm = low_hz / nyq
    hi_norm = hi_clamped / nyq
    sos = sig.butter(4, [lo_norm, hi_norm], btype="band", output="sos")
    filtered = sig.sosfilt(sos, mono)
    rms = float(np.sqrt(np.mean(filtered**2)))
    return float(20.0 * np.log10(rms + 1e-10))


def _spectral_flatness(mono: np.ndarray, frame_size: int = 4096) -> float:
    """Compute spectral flatness (Wiener entropy) using windowed frames.

    Returns a value between 0.0 (pure tone) and 1.0 (white noise).
    Uses framed analysis consistent with other spectral computations.
    """
    hop = frame_size // 2
    window = np.hanning(frame_size)
    flatnesses = []

    for i in range(0, len(mono) - frame_size + 1, hop):
        frame = mono[i : i + frame_size].astype(np.float64) * window
        spec = np.abs(rfft(frame)) ** 2
        spec = spec[1:]  # exclude DC
        log_mean = float(np.mean(np.log(spec + 1e-10)))
        geo_mean = np.exp(log_mean)
        arith_mean = float(np.mean(spec)) + 1e-10
        flatnesses.append(geo_mean / arith_mean)

    return float(np.mean(flatnesses)) if flatnesses else 0.0


def _band_excess_db(
    mono: np.ndarray,
    sample_rate: int,
    low_hz: float,
    high_hz: float,
) -> tuple[float, float, float]:
    """Compute bandwidth-normalised band excess in dB.

    Returns (band_db, overall_db, excess_db).
    Excess is relative to what a flat spectrum would have in this band.
    """
    nyq = sample_rate / 2.0
    overall_rms = float(np.sqrt(np.mean(mono**2)))
    overall_db = float(20.0 * np.log10(overall_rms + 1e-10))
    band_db = _band_energy_db(mono, sample_rate, low_hz, high_hz)
    bw_fraction = (min(high_hz, nyq) - low_hz) / nyq
    expected_db = overall_db + float(10.0 * np.log10(bw_fraction + 1e-10))
    excess_db = band_db - expected_db
    return band_db, overall_db, excess_db


def _detect_band_excess(
    mono: np.ndarray,
    sample_rate: int,
    low_hz: float,
    high_hz: float,
    problem_type: str,
    label: str,
    freq_label: str,
    *,
    spectral_flatness: float | None = None,
    settings: AnalysisSettings,
) -> list[ProblemItem]:
    """Detect excessive energy in a frequency band. PROB-07/08/09.

    Parametric replacement for the former _detect_sibilance, _detect_mud,
    and _detect_harshness functions. All three were structurally identical,
    differing only in frequency range, problem type string, label, and
    frequency label for the message.

    Args:
        mono: Mono audio signal as numpy array.
        sample_rate: Sample rate in Hz.
        low_hz: Lower bound of the frequency band.
        high_hz: Upper bound of the frequency band.
        problem_type: Problem type string (e.g. "sibilance", "mud", "harshness").
        label: Human-readable label for the problem (e.g. "sibilance", "mud", "harshness").
        freq_label: Frequency range label for the message (e.g. "5-10kHz", "200-500Hz").
        spectral_flatness: Pre-computed spectral flatness value. When None,
            computes own via _spectral_flatness(mono). Passed by detect_problems
            to avoid redundant FFT computation across 3 band-excess calls.

    Returns:
        List containing a single ProblemItem if excess detected, empty list otherwise.
    """
    if spectral_flatness is None:
        spectral_flatness = _spectral_flatness(mono)
    if spectral_flatness < settings.spectral_flatness_min:
        return []

    band_db, overall_db, excess_db = _band_excess_db(
        mono,
        sample_rate,
        low_hz,
        high_hz,
    )

    if excess_db <= settings.band_excess_threshold_db:
        return []

    return [
        ProblemItem(
            type=problem_type,
            severity="moderate",
            message=(
                f"Excessive {label}: {freq_label} band energy is {excess_db:.1f} dB "
                f"above expected level."
            ),
            details={
                "band_energy_db": round(band_db, 1),
                "overall_energy_db": round(overall_db, 1),
                "excess_db": round(excess_db, 1),
            },
        )
    ]


def _average_power_spectrum(
    mono: np.ndarray,
    frame_size: int,
    sample_rate: int,
) -> tuple[np.ndarray | None, np.ndarray | None]:
    """Compute average power spectrum over overlapping Hann-windowed frames.

    Returns (avg_spectrum, freqs) or (None, None) if the signal has
    fewer samples than one frame.
    """
    if len(mono) < frame_size:
        return None, None

    hop = frame_size // 2
    window = np.hanning(frame_size)
    n_frames = 0
    spectrum_sum = np.zeros(frame_size // 2 + 1)

    for i in range(0, len(mono) - frame_size + 1, hop):
        frame = mono[i : i + frame_size].astype(np.float64)
        windowed = frame * window
        fft_result = rfft(windowed)
        spectrum_sum += np.abs(fft_result) ** 2
        n_frames += 1

    if n_frames == 0:
        return None, None

    avg_spectrum = spectrum_sum / n_frames
    freqs = rfftfreq(frame_size, 1.0 / sample_rate)
    return avg_spectrum, freqs


def _detect_resonances(
    mono: np.ndarray,
    sample_rate: int,
    *,
    power_spectrum: tuple[np.ndarray, np.ndarray] | None = None,
    settings: AnalysisSettings,
) -> list[ProblemItem]:
    """Detect narrow resonant peaks (room modes). PROB-10.

    Uses a median-filtered spectral baseline to distinguish genuine
    resonances from the signal's fundamental frequencies. This avoids
    false positives on tonal signals (pure sines, harmonic content).

    Args:
        mono: Mono audio signal as numpy array.
        sample_rate: Sample rate in Hz.
        power_spectrum: Pre-computed (avg_spectrum, freqs) tuple from
            _average_power_spectrum(mono, spectrum_frame_size, sample_rate).
            When None, computes own at the settings frame size. Passed by
            detect_problems to share FFT with _detect_lossy_codec.
    """
    frame_size = settings.spectrum_frame_size

    if power_spectrum is None:
        result = _average_power_spectrum(mono, frame_size, sample_rate)
        if result[0] is None:
            return []
        avg_spectrum, freqs = result
    else:
        avg_spectrum, freqs = power_spectrum
        if avg_spectrum is None:
            return []

    avg_db = 10.0 * np.log10(avg_spectrum + 1e-10)
    freq_resolution = float(sample_rate) / frame_size

    # Skip resonance detection if the signal lacks broadband energy.
    # Pure tonal signals (sine waves) have very low median spectral level
    # because energy is concentrated in a few bins. Resonance detection
    # requires a noise floor baseline to identify anomalous peaks against.
    median_level = float(np.median(avg_db))
    if median_level < settings.resonance_median_floor_db:
        return []

    # Find narrow peaks with significant prominence
    peaks, props = sig.find_peaks(
        avg_db, prominence=settings.resonance_prominence_db, width=(1, 20)
    )

    # Filter: only keep peaks in 30-5000 Hz range with Q > 5
    resonances: list[dict] = []
    for idx, peak in enumerate(peaks):
        freq = float(freqs[peak])
        if freq < 30 or freq > 5000:
            continue
        bw_hz = float(props["widths"][idx]) * freq_resolution
        q = freq / (bw_hz + 1e-10)
        if q <= 5:
            continue
        resonances.append(
            {
                "frequency_hz": round(freq, 1),
                "prominence_db": round(float(props["prominences"][idx]), 1),
                "q_factor": round(q, 1),
            }
        )

    if not resonances:
        return []

    # Sort by prominence (strongest first)
    resonances.sort(key=lambda r: r["prominence_db"], reverse=True)

    return [
        ProblemItem(
            type="resonant_peak",
            severity="significant",
            message=(
                f"Detected {len(resonances)} resonant peak(s). "
                f"Strongest at {resonances[0]['frequency_hz']:.0f} Hz "
                f"({resonances[0]['prominence_db']:.1f} dB prominence, "
                f"Q={resonances[0]['q_factor']:.0f})."
            ),
            details={
                "num_resonances": len(resonances),
                "resonances": resonances,
            },
        )
    ]


def _detect_lossy_codec(
    mono: np.ndarray,
    sample_rate: int,
    *,
    power_spectrum: tuple[np.ndarray, np.ndarray] | None = None,
    settings: AnalysisSettings,
) -> list[ProblemItem]:
    """Detect lossy codec artifacts via 16kHz spectral shelf. PROB-13.

    Args:
        mono: Mono audio signal as numpy array.
        sample_rate: Sample rate in Hz.
        power_spectrum: Pre-computed (avg_spectrum, freqs) tuple from
            _average_power_spectrum(mono, spectrum_frame_size, sample_rate).
            When None, computes own at the settings frame size. Passed by
            detect_problems to share FFT with _detect_resonances.
    """
    if sample_rate < 44100:
        return []  # Need Nyquist >= 22kHz

    frame_size = settings.spectrum_frame_size

    if power_spectrum is None:
        result = _average_power_spectrum(mono, frame_size, sample_rate)
        if result[0] is None:
            return []
        avg_spectrum, freqs = result
    else:
        avg_spectrum, freqs = power_spectrum
        if avg_spectrum is None:
            return []

    # Compare energy in 14-16kHz band vs 16-20kHz band
    mask_below = (freqs >= 14000) & (freqs < 16000)
    mask_above = (freqs >= 16000) & (freqs <= 20000)

    if not np.any(mask_below) or not np.any(mask_above):
        return []

    energy_below = float(10.0 * np.log10(np.mean(avg_spectrum[mask_below]) + 1e-10))
    energy_above = float(10.0 * np.log10(np.mean(avg_spectrum[mask_above]) + 1e-10))
    shelf_drop = energy_below - energy_above

    if shelf_drop < settings.lossy_shelf_drop_db:
        return []

    return [
        ProblemItem(
            type="lossy_codec",
            severity="dealbreaker",
            message=(
                f"Possible lossy codec artifact: {shelf_drop:.1f} dB spectral shelf "
                f"drop above 16kHz."
            ),
            details={
                "shelf_drop_db": round(shelf_drop, 1),
                "energy_14_16khz_db": round(energy_below, 1),
                "energy_16_20khz_db": round(energy_above, 1),
            },
        )
    ]
