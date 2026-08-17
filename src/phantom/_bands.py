"""Octave-band energy primitive shared by spectral and masking analysis (B.6).

``analyze_spectrum`` converts the per-band linear energies to dB for its
``octave_band_energy_db`` field; ``masking`` consumes the linear energies
directly for its overlap scoring. The 4096/2048 Hann + Essentia
``FrequencyBands`` loop lives here so both consumers share one
implementation (P-09), instead of masking reaching into ``spectral`` for
an underscore-prefixed helper.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import essentia.standard as es
from pydantic import BaseModel, ConfigDict, Field, create_model, model_serializer

from phantom._settings import AnalysisSettings

# Standard octave band center frequencies (Hz).
OCTAVE_CENTERS = [31.25, 62.5, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]

# Band edge frequencies for octave band analysis.
# Lower edge = center / sqrt(2), upper edge = center * sqrt(2).
_SQRT2 = np.sqrt(2)
OCTAVE_EDGES = [OCTAVE_CENTERS[0] / _SQRT2] + [c * _SQRT2 for c in OCTAVE_CENTERS]

# Band label keys for the output dict.
_BAND_LABELS = [f"{int(c)}_hz" if c >= 1 else f"{c}_hz" for c in OCTAVE_CENTERS]

# (field_name, serialized_key) pairs for the typed octave-band maps (C.2).
# Field names are Python identifiers; serialized keys stay the "250_hz"
# vocabulary the MCP responses and profiles use.
OCTAVE_BAND_KEY_PAIRS: tuple[tuple[str, str], ...] = tuple(
    (f"band_{label}", label) for label in _BAND_LABELS
)


class FlatMapModel(BaseModel):
    """Base for typed per-band maps that serialize as flat dicts (C.2).

    Subclasses declare one typed field per serialized key (band maps alias
    their fields to the "250_hz" vocabulary; ProblemDetails fields use the
    bare problem keys). The plain model serializer emits
    ``{serialized_key: value}`` for each set field, dropping unset (None)
    fields and merging ``extra`` entries, so ``model_dump()`` of the owning
    result model is byte-identical to the raw string-keyed dicts these
    models replace -- including partial maps (a band filtered out at low
    sample rates) and non-canonical keys (custom profile band vocabularies
    pass through as extras). Subclasses may override ``extra`` (details
    forbids unknown keys).

    Dict-style access keeps existing consumers working: ``__getitem__``
    reads by serialized key, ``__eq__`` compares against the dict the model
    serializes to (both directions), and ``keys``/``values``/``items``/
    ``get``/``in``/``iter``/``len`` iterate the flat view. The one accepted
    break from the raw-dict era is ``isinstance(x, dict)`` -- these are
    typed models. Attribute access remains the primary typed interface.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    @classmethod
    def _key_for(cls, field_name: str) -> str:
        return cls.model_fields[field_name].alias or field_name

    def _flat(self) -> dict[str, Any]:
        """Read view: alias-keyed set fields plus extras, values as-is.

        Values keep their typed form (e.g. DeviationResult instances), so
        iteration exposes the schema; serialization reduces them to plain
        dicts (see :meth:`_serialize_flat`).
        """
        out: dict[str, Any] = {}
        for name in type(self).model_fields:
            value = getattr(self, name)
            if value is not None:
                out[self._key_for(name)] = value
        for key, value in (self.__pydantic_extra__ or {}).items():
            out[key] = value
        return out

    @model_serializer
    def _serialize_flat(self) -> dict[str, Any]:
        """Plain-dict serialization, byte-identical to the raw maps these
        models replace: nested models are reduced to their own dumps so both
        python-mode model_dump() and JSON output stay flat."""
        return {key: _reduce_value(value) for key, value in self._flat().items()}

    # -- dict-style reads ----------------------------------------------
    def items(self):
        return self._flat().items()

    def keys(self):
        return self._flat().keys()

    def values(self):
        return self._flat().values()

    def get(self, key: str, default: Any = None) -> Any:
        return self._flat().get(key, default)

    def __getitem__(self, key: str) -> Any:
        """Read by serialized key, dict-style.

        Returns the typed value; absent keys raise ``KeyError`` exactly as a
        dict would.
        """
        return self._flat()[key]

    def __eq__(self, other: object) -> bool:
        """Equality against the serialized flat view.

        A map equals the dict it serializes to, in both directions, so
        existing comparisons like ``item.details == {"dc_offset": 0.05}``
        keep working (nested models are reduced, matching model_dump).
        FlatMapModel instances compare by the same view.
        """
        if isinstance(other, dict):
            return self._serialize_flat() == other
        if isinstance(other, FlatMapModel):
            return self._serialize_flat() == other._serialize_flat()
        return NotImplemented

    def __contains__(self, key: object) -> bool:
        return key in self._flat()

    def __iter__(self):
        return iter(self._flat())

    def __len__(self) -> int:
        return len(self._flat())


def _reduce_value(value: Any) -> Any:
    """Plain-dict reduction for nested models inside serialized maps."""
    return value.model_dump() if isinstance(value, BaseModel) else value


def octave_band_map_model(name: str, value_type: type) -> type[FlatMapModel]:
    """Build a typed octave-band map model with the canonical-key aliases.

    Every map is the same shape -- one field per octave band, each carrying
    its ``"250_hz"``-style serialized key as the alias -- so the ten-band
    vocabulary is defined once (``OCTAVE_BAND_KEY_PAIRS``) and reused for
    every value type: float dB energies (spectral), DeviationResult
    (comparisons), MetricDiff (matching). Serialization behavior is
    identical across all of them (see :class:`FlatMapModel`).

    Args:
        name: Model class name (for reprs and error messages).
        value_type: Per-band value model (``float`` for scalar dB maps).

    Returns:
        A generated ``FlatMapModel`` subclass with the given class name.
    """
    fields = {
        field_name: (
            value_type | None,
            Field(None, alias=key, serialization_alias=key),
        )
        for field_name, key in OCTAVE_BAND_KEY_PAIRS
    }
    return create_model(name, __base__=FlatMapModel, **fields)


OctaveBandEnergyDb = octave_band_map_model("OctaveBandEnergyDb", float)


def _octave_band_energies(
    mono: np.ndarray, sample_rate: int, settings: AnalysisSettings
) -> np.ndarray:
    """Average linear energy per octave band via Essentia FrequencyBands (P-09).

    Runs a Hann-windowed FrequencyBands loop over ``OCTAVE_EDGES`` and
    averages the per-frame band energies across all frames. Shared by
    ``spectral.analyze_spectrum`` (which converts the result to dB) and
    ``masking`` (which consumes the linear energies directly) so the identical
    loop is not duplicated.

    Frame/hop sizes are AnalysisSettings-tunable (C.1); defaults 4096/2048
    reproduce the original pass exactly.

    Args:
        mono: 1D float32 numpy array of audio samples.
        sample_rate: Sample rate in Hz.
        settings: Effective analysis settings (the requiring caller resolves
            them).

    Returns:
        1D numpy array of shape ``(len(OCTAVE_CENTERS),)`` with the average
        linear energy per octave band. Returns all-zeros when the signal is
        shorter than one frame (insufficient data to resolve any band -- the
        acoustically correct answer).
    """
    frame_size = settings.octave_frame_size
    hop_size = settings.octave_hop_size

    # Audio shorter than one FFT frame cannot produce meaningful band energies.
    if len(mono) < frame_size:
        return np.zeros(len(OCTAVE_CENTERS))

    windowing = es.Windowing(type="hann", size=frame_size)
    spectrum = es.Spectrum(size=frame_size)
    freq_bands = es.FrequencyBands(frequencyBands=OCTAVE_EDGES, sampleRate=sample_rate)

    band_energies_list = []
    for frame in es.FrameGenerator(mono, frameSize=frame_size, hopSize=hop_size):
        win = windowing(frame)
        spec = spectrum(win)
        bands = freq_bands(spec)
        band_energies_list.append(bands)

    if not band_energies_list:
        return np.zeros(len(OCTAVE_CENTERS))

    return np.mean(band_energies_list, axis=0)
