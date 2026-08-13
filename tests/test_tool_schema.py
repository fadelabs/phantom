"""Test that the MCP tool schema is a stable client-facing contract.

Snapshot test, written FIRST against unmodified source, before any refactor
of the tool wrappers. FastMCP derives each tool's input schema and description
from the function signature and docstring, so a registry loop that generates
wrappers could silently change parameter names or schemas that MCP clients
depend on. This test makes any such change fail loudly.

Scope: this snapshot gates the REQUEST side only -- tool name, title,
description, and input schema (parameter names, types, required/optional,
defaults, anyOf/items). Confidence that tool RESPONSE shapes are unchanged
comes from test_server.py and test_server_integration.py staying green; those
suites assert key presence on returned data, not full shape. This snapshot
claims no more than the request side.

--------------------------------- Snapshot policy ----------------------------

BREAKING -- stop and report, never update the snapshot to match:
  * a tool disappearing or appearing
  * any change to name
  * any change to input_schema (parameter names, types, required, default,
    anyOf/items)

ADDITIVE -- update the snapshot deliberately, in its own commit, and say so
in the commit message:
  * title going None -> a value
  * a description improving

MCP clients key on name and inputSchema. A title appearing or a description
improving cannot break a caller; a renamed parameter silently can.
-------------------------------------------------------------------------------
"""

from __future__ import annotations

import asyncio

from phantom.server import mcp

EXPECTED_MCP_CONTRACT = {
    "analyze_dynamics": {
        "description": "Measure dynamics: RMS, peak, crest factor, "
        "dynamic range, dynamic complexity.",
        "input_schema": {
            "additionalProperties": False,
            "properties": {"file_path": {"type": "string"}},
            "required": ["file_path"],
            "type": "object",
        },
        "title": None,
    },
    "analyze_loudness": {
        "description": "Measure EBU R128 loudness: integrated "
        "LUFS, true peak dBTP, loudness range, "
        "short-term and momentary LUFS.",
        "input_schema": {
            "additionalProperties": False,
            "properties": {"file_path": {"type": "string"}},
            "required": ["file_path"],
            "type": "object",
        },
        "title": None,
    },
    "analyze_masking": {
        "description": "Analyze frequency masking between two stems "
        "with per-octave-band severity.",
        "input_schema": {
            "additionalProperties": False,
            "properties": {
                "file_path_a": {"type": "string"},
                "file_path_b": {"type": "string"},
            },
            "required": ["file_path_a", "file_path_b"],
            "type": "object",
        },
        "title": None,
    },
    "analyze_phase": {
        "description": "Check phase coherence: overall and per-band "
        "correlation, polarity detection.",
        "input_schema": {
            "additionalProperties": False,
            "properties": {"file_path": {"type": "string"}},
            "required": ["file_path"],
            "type": "object",
        },
        "title": None,
    },
    "analyze_spectrum": {
        "description": "Analyze frequency spectrum: centroid, "
        "rolloff, flatness, contrast, dissonance, "
        "octave band energy.",
        "input_schema": {
            "additionalProperties": False,
            "properties": {"file_path": {"type": "string"}},
            "required": ["file_path"],
            "type": "object",
        },
        "title": None,
    },
    "analyze_stereo": {
        "description": "Analyze stereo field: correlation, width, "
        "mid/side ratio, L/R balance, panorama "
        "distribution.",
        "input_schema": {
            "additionalProperties": False,
            "properties": {"file_path": {"type": "string"}},
            "required": ["file_path"],
            "type": "object",
        },
        "title": None,
    },
    "apply_processing": {
        "description": "Apply custom audio processing chain. "
        "Requires phantom-audio[processing].",
        "input_schema": {
            "additionalProperties": False,
            "properties": {
                "file_path": {"type": "string"},
                "operations": {
                    "items": {"additionalProperties": True, "type": "object"},
                    "type": "array",
                },
                "output_path": {"type": "string"},
            },
            "required": ["file_path", "operations", "output_path"],
            "type": "object",
        },
        "title": None,
    },
    "batch_diagnostic": {
        "description": "Run full diagnostic on multiple stems. "
        "Flags sample rate mismatches as "
        "dealbreaker severity.",
        "input_schema": {
            "additionalProperties": False,
            "properties": {
                "file_paths": {"items": {"type": "string"}, "type": "array"}
            },
            "required": ["file_paths"],
            "type": "object",
        },
        "title": None,
    },
    "compare_phase": {
        "description": "Compare phase between two audio files: "
        "cross-correlation, delay detection, polarity "
        "check.",
        "input_schema": {
            "additionalProperties": False,
            "properties": {
                "file_path_a": {"type": "string"},
                "file_path_b": {"type": "string"},
            },
            "required": ["file_path_a", "file_path_b"],
            "type": "object",
        },
        "title": None,
    },
    "compare_to_profile": {
        "description": "Compare audio against a genre reference "
        "profile for loudness, frequency, "
        "dynamics, and stereo deviations.",
        "input_schema": {
            "additionalProperties": False,
            "properties": {
                "file_path": {"type": "string"},
                "profile_name": {"type": "string"},
            },
            "required": ["file_path", "profile_name"],
            "type": "object",
        },
        "title": None,
    },
    "compare_to_reference": {
        "description": "Compare audio against a reference WAV "
        "file with normalized spectral curves.",
        "input_schema": {
            "additionalProperties": False,
            "properties": {
                "file_path": {"type": "string"},
                "reference_path": {"type": "string"},
            },
            "required": ["file_path", "reference_path"],
            "type": "object",
        },
        "title": None,
    },
    "detect_problems": {
        "description": "Scan for audio problems: clipping, DC "
        "offset, ISP, noise, hum, sibilance, mud, "
        "harshness, resonances.",
        "input_schema": {
            "additionalProperties": False,
            "properties": {"file_path": {"type": "string"}},
            "required": ["file_path"],
            "type": "object",
        },
        "title": None,
    },
    "fix_audio": {
        "description": "Fix detected audio problems using corrective "
        "processing. Requires phantom-audio[processing].",
        "input_schema": {
            "additionalProperties": False,
            "properties": {
                "file_path": {"type": "string"},
                "output_path": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "default": None,
                },
                "problems": {
                    "anyOf": [
                        {"items": {"type": "string"}, "type": "array"},
                        {"type": "null"},
                    ],
                    "default": None,
                },
            },
            "required": ["file_path"],
            "type": "object",
        },
        "title": None,
    },
    "full_diagnostic": {
        "description": "Run all six analysis types on a single "
        "audio file: spectral, loudness, dynamics, "
        "stereo, phase, and problems.",
        "input_schema": {
            "additionalProperties": False,
            "properties": {"file_path": {"type": "string"}},
            "required": ["file_path"],
            "type": "object",
        },
        "title": None,
    },
    "list_profiles": {
        "description": "List all available genre reference profile names.",
        "input_schema": {
            "additionalProperties": False,
            "properties": {},
            "type": "object",
        },
        "title": None,
    },
    "load_profile": {
        "description": "Load a genre reference profile by name. "
        "Returns profile data as JSON.",
        "input_schema": {
            "additionalProperties": False,
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
            "type": "object",
        },
        "title": None,
    },
    "match_to_reference": {
        "description": "Match target audio to reference "
        "spectral/loudness/width characteristics "
        "via Matchering. Requires "
        "phantom-audio[matching].",
        "input_schema": {
            "additionalProperties": False,
            "properties": {
                "output_path": {"type": "string"},
                "reference_path": {"type": "string"},
                "target_path": {"type": "string"},
            },
            "required": ["target_path", "reference_path", "output_path"],
            "type": "object",
        },
        "title": None,
    },
    "multi_stem_masking": {
        "description": "Analyze frequency masking across all "
        "stem pairs. Returns pairs ranked by "
        "masking severity.",
        "input_schema": {
            "additionalProperties": False,
            "properties": {
                "file_paths": {"items": {"type": "string"}, "type": "array"}
            },
            "required": ["file_paths"],
            "type": "object",
        },
        "title": None,
    },
    "read_live_metrics": {
        "description": "Read the Phantom Studio plugin's live "
        "meter snapshot (loudness, true peak, "
        "stereo, band energy, verdicts). Omit "
        "instance_id for the most recent instance.",
        "input_schema": {
            "additionalProperties": False,
            "properties": {
                "instance_id": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "default": None,
                }
            },
            "type": "object",
        },
        "title": None,
    },
    "separate_stems": {
        "description": "Separate audio into stems (vocals, drums, "
        "bass, other) via Demucs. Requires "
        "phantom-audio[separation].",
        "input_schema": {
            "additionalProperties": False,
            "properties": {
                "file_path": {"type": "string"},
                "output_dir": {"type": "string"},
            },
            "required": ["file_path", "output_dir"],
            "type": "object",
        },
        "title": None,
    },
}


def _registered_tool_contracts() -> dict[str, dict]:
    """Return {tool_name: {title, description, input_schema}} for all tools."""
    tools = asyncio.run(mcp.list_tools())
    return {
        t.name: {
            "title": t.title,
            "description": t.description,
            "input_schema": t.parameters,
        }
        for t in tools
    }


def test_no_tool_added_or_removed() -> None:
    """Tool presence is part of the contract: no silent add or removal.

    Covers a registry loop accidentally registering a 7th dimension, a wrapper
    being dropped, or a tool being renamed.
    """
    actual = _registered_tool_contracts()
    assert set(actual) == set(EXPECTED_MCP_CONTRACT)


def test_tool_contract_matches_snapshot() -> None:
    """Every registered tool's request contract must match the snapshot.

    Name is checked above; title, description, and input_schema (parameter
    names, types, required, defaults, anyOf/items) are checked here.
    """
    assert _registered_tool_contracts() == EXPECTED_MCP_CONTRACT
