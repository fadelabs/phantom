"""Source separation via Demucs.

Provides separate_stems() for splitting a stereo mix into individual stems
(vocals, drums, bass, other) using Meta's Hybrid Transformer Demucs model.

Demucs is an optional dependency. The function raises DependencyMissingError
with install instructions if Demucs is not available.
"""

from __future__ import annotations

import hashlib
import os

from pydantic import BaseModel

from phantom.exceptions import AnalysisError, AudioLoadError, DependencyMissingError
from phantom._utils import validate_input_path, validate_output_path


class SeparationResult(BaseModel):
    """Result of stem separation."""

    stems: dict[str, str]


def separate_stems(input_path: str, output_dir: str) -> SeparationResult:
    """Separate a stereo mix into individual stems using Demucs.

    Uses the htdemucs model to split audio into vocals, drums, bass, and
    other stems. Each stem is saved as a WAV file in the output directory.

    Demucs is an optional dependency. If not installed, a
    DependencyMissingError is raised with install instructions.

    Note: First use downloads the htdemucs model (~80 MB). Subsequent
    calls use the cached model.

    Args:
        input_path: Path to the input WAV file to separate.
        output_dir: Directory where stem WAV files will be written.
            Created if it does not exist.

    Returns:
        SeparationResult model with stems dict mapping stem names to
        output file paths:
        {"vocals": "/out/vocals.wav", "drums": "/out/drums.wav",
         "bass": "/out/bass.wav", "other": "/out/other.wav"}

    Raises:
        DependencyMissingError: If Demucs is not installed (per D-06).
        PathSecurityError: If output_dir is outside PHANTOM_OUTPUT_DIR (when set).
        FileNotFoundError: If input file does not exist.
        AnalysisError: If separation processing fails.
    """
    # Step 0: Validate paths against security restrictions (D-09, D-10)
    output_dir = validate_output_path(output_dir)
    input_path = validate_input_path(input_path)

    # Step 1: Guard -- import demucs inside function body (per D-06, SEP-02)
    try:
        from demucs.pretrained import get_model
        from demucs.apply import apply_model
        from demucs.audio import AudioFile
        import torch
        import soundfile as sf
    except ImportError:
        raise DependencyMissingError(
            package="Demucs",
            extra="separation",
            detail=(
                "Demucs provides AI-powered source separation into "
                "vocals, drums, bass, and other stems."
            ),
        )

    # Step 2: Validate input file exists
    if not os.path.isfile(input_path):
        raise AudioLoadError(f"Input file not found: {os.path.basename(input_path)}")

    # Step 3: Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Step 4: Load model and audio (per D-03: htdemucs only)
        model = get_model("htdemucs")
        model.cpu()

        wav = AudioFile(input_path).read(
            streams=0,
            samplerate=model.samplerate,
            channels=model.audio_channels,
        )
        ref = wav.mean(0)
        wav = (wav - ref.mean()) / ref.std()

        # Step 5: Run separation
        with torch.no_grad():
            sources = apply_model(model, wav[None], progress=False)
        sources = sources[0]
        sources = sources * ref.std() + ref.mean()

        # Step 6: Save each stem as WAV (per D-01, D-02)
        result = {}
        for i, stem_name in enumerate(model.sources):
            safe_name = os.path.basename(stem_name)
            if not safe_name or safe_name.startswith("."):
                safe_name = f"stem_{int(hashlib.md5(stem_name.encode()).hexdigest()[:8], 16) % 10000}"
            stem_path = os.path.join(output_dir, f"{safe_name}.wav")
            real_stem = os.path.realpath(stem_path)
            real_outdir = os.path.realpath(output_dir)
            if (
                not real_stem.startswith(real_outdir + os.sep)
                and real_stem != real_outdir
            ):
                raise AnalysisError(
                    f"Stem name '{stem_name}' would write outside output directory"
                )
            stem_audio = sources[i].cpu().numpy().T
            sf.write(stem_path, stem_audio, model.samplerate)
            result[stem_name] = stem_path

        return SeparationResult(stems=result)

    except DependencyMissingError:
        raise
    except FileNotFoundError:
        raise
    except AnalysisError:
        raise
    except Exception as exc:
        raise AnalysisError(f"Source separation failed: {exc}") from exc
