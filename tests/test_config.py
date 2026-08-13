"""The env-var registry in phantom._config must cover exactly the env vars
the code reads, so `phantom doctor`'s table can't drift from the runtime.
"""

from __future__ import annotations

import re
from pathlib import Path

from phantom._config import ENV_VARS

SRC = Path(__file__).resolve().parents[1] / "src" / "phantom"

# Every way src/phantom reads a PHANTOM_* env var by literal name:
#   os.environ.get("PHANTOM_X"), os.getenv("PHANTOM_X"),
#   _get_env_int("PHANTOM_X"), _get_env_float("PHANTOM_X")
_ENV_READ = re.compile(
    r"(?:os\.environ\.get|os\.getenv|_get_env_int|_get_env_float)"
    r'\(\s*"(PHANTOM_[A-Z_]+)"'
)


def _env_read_literals() -> set[str]:
    literals: set[str] = set()
    for path in SRC.rglob("*.py"):
        literals.update(_ENV_READ.findall(path.read_text(encoding="utf-8")))
    return literals


def test_registry_matches_env_reads_in_source() -> None:
    """Every env-read literal in src appears in ENV_VARS, and vice versa."""
    registered = {var.name for var in ENV_VARS}
    read = _env_read_literals()

    assert read == registered, (
        "phantom._config.ENV_VARS has drifted from the env vars the code reads.\n"
        f"Read but not registered: {sorted(read - registered)}\n"
        f"Registered but never read: {sorted(registered - read)}"
    )


def test_registry_names_unique() -> None:
    """No env var is declared twice in the registry."""
    names = [var.name for var in ENV_VARS]
    assert len(names) == len(set(names))
