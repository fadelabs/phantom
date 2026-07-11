# phantom-audio-separation

Demucs-based stem separation plugin for [phantom-audio](https://github.com/fadelabs/phantom).

Splits a stereo mix into individual stems (vocals, drums, bass, other) using
Meta's Hybrid Transformer Demucs model. This package carries the heavyweight
PyTorch + Demucs dependency tree (~2.5 GB) so the core `phantom-audio`
analysis library stays lean and independent of PyTorch's release cadence and
platform-support matrix.

## Install

```bash
# Recommended: via the phantom-audio meta-extra
uv tool install "phantom-audio[separation]" --python 3.13

# Or directly
uv pip install phantom-audio-separation
```

## Usage

Once installed, `phantom-audio` discovers this plugin automatically through
the `phantom.separation` entry-point group -- no configuration needed. The
existing APIs keep working unchanged:

```python
from phantom import separate_stems

result = separate_stems("mix.wav", "./stems")
print(result.stems)  # {"vocals": ".../vocals.wav", "drums": ..., ...}
```

Or from the CLI / MCP server:

```bash
phantom separate mix.wav --output ./stems/
```

`phantom doctor` reports `phantom-audio-separation` as OK only when the
plugin is installed and importable.

> **Note:** First use downloads the htdemucs model (~80 MB). Subsequent
> calls use the cached model.

## License

AGPL-3.0-or-later, same as phantom-audio. See the
[repository LICENSE](https://github.com/fadelabs/phantom/blob/main/LICENSE).
