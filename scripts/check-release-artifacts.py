"""Validate release archive contents without extracting them to the filesystem."""

import re
import sys
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

SOURCE_FILES = {
    "README.md",
    "LICENSE",
    "pyproject.toml",
    "uv.lock",
    "PKG-INFO",
    ".gitignore",
}
SOURCE_PREFIXES = ("src/phantom/", "packages/phantom-audio-separation/src/")
SOURCE_FILES.update(
    {
        "packages/phantom-audio-separation/README.md",
        "packages/phantom-audio-separation/pyproject.toml",
    }
)
LOCAL_PATH = re.compile(rb"/(?:Users|home)/[A-Za-z0-9_.-]+/")


def check(name: str, contents: bytes, *, wheel: bool) -> None:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Unsafe archive path: {name}")
    relative = name if wheel else "/".join(path.parts[1:])
    if wheel:
        allowed = relative.startswith("phantom/") or (
            path.parts
            and path.parts[0].startswith("phantom_audio-")
            and path.parts[0].endswith(".dist-info")
        )
    else:
        allowed = relative in SOURCE_FILES or relative.startswith(SOURCE_PREFIXES)
    if not allowed:
        raise ValueError(f"Unexpected release file: {name}")
    if relative != ".gitignore" and any(
        part.startswith(".") or part == "__pycache__" for part in path.parts
    ):
        raise ValueError(f"Local/hidden file in release: {name}")
    if LOCAL_PATH.search(contents):
        raise ValueError(f"Local home path in release file: {name}")


def validate(archive: Path) -> None:
    count = 0
    if archive.suffix == ".whl":
        with zipfile.ZipFile(archive) as wheel:
            for member in wheel.infolist():
                if not member.is_dir():
                    check(member.filename, wheel.read(member), wheel=True)
                    count += 1
    else:
        with tarfile.open(archive, "r:gz") as source:
            for member in source.getmembers():
                if member.isdir():
                    continue
                if not member.isfile():
                    raise ValueError(f"Non-regular release entry: {member.name}")
                stream = source.extractfile(member)
                if stream is None:
                    raise ValueError(f"Unreadable release entry: {member.name}")
                check(member.name, stream.read(), wheel=False)
                count += 1
    if count == 0:
        raise ValueError(f"Empty release archive: {archive.name}")
    print(f"{archive.name}: {count} files passed release-content checks")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Pass the exact wheel and source archive paths to check.")
    for argument in sys.argv[1:]:
        validate(Path(argument))
