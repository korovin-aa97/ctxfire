"""Git-aware, local-only file discovery."""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal

# The only child process is a resolved Git executable with fixed argv and no shell.


@dataclass(frozen=True)
class Inventory:
    paths: tuple[str, ...]
    method: str
    skipped_symlinks: tuple[str, ...]
    skipped_non_files: tuple[str, ...]


PathKind = Literal["file", "symlink", "non-file"]


def path_kind(root: Path, relative: str) -> PathKind:
    """Classify a root-relative path without accepting a symlink ancestor."""

    candidate = root
    for part in PurePosixPath(relative).parts:
        candidate /= part
        if candidate.is_symlink():
            return "symlink"
    return "file" if candidate.is_file() else "non-file"


def _git_inventory(root: Path) -> tuple[str, ...] | None:
    git_executable = shutil.which("git")
    if git_executable is None:
        return None
    # root is passed as one argv value and cannot introduce command options.
    probe = subprocess.run(  # nosec B603
        [git_executable, "-C", str(root), "rev-parse", "--show-toplevel"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if probe.returncode != 0 or Path(probe.stdout.strip()).resolve() != root:
        return None
    # The argument vector is fixed; repository content is never executed.
    try:
        result = subprocess.run(  # nosec B603
            [
                git_executable,
                "-C",
                str(root),
                "ls-files",
                "-z",
                "--cached",
                "--others",
                "--exclude-standard",
                "--deduplicate",
            ],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as error:
        raise OSError(f"Git file discovery failed for project root: {root}") from error
    return tuple(
        sorted(
            item.decode("utf-8", "surrogateescape") for item in result.stdout.split(b"\0") if item
        )
    )


def inventory(root: Path) -> Inventory:
    """Return regular files eligible for scanning, never following symlinks."""

    git_paths = _git_inventory(root)
    fallback_symlinks: list[str] = []
    if git_paths is None:
        candidates: list[str] = []
        for directory, directories, files in os.walk(root, followlinks=False):
            base = Path(directory)
            ignored_directories = {
                ".git",
                ".hg",
                ".svn",
                "node_modules",
                ".venv",
                "venv",
                "dist",
                "build",
                "__pycache__",
            }
            kept_directories: list[str] = []
            for item in sorted(directories):
                relative = (base / item).relative_to(root).as_posix()
                if (base / item).is_symlink():
                    fallback_symlinks.append(relative)
                elif item not in ignored_directories:
                    kept_directories.append(item)
            directories[:] = kept_directories
            candidates.extend((base / name).relative_to(root).as_posix() for name in sorted(files))
        raw_paths = tuple(sorted(candidates))
        method = "filesystem-fallback"
    else:
        raw_paths = git_paths
        method = "git-index+untracked-nonignored"

    paths: list[str] = []
    symlinks = fallback_symlinks
    non_files: list[str] = []
    for relative in raw_paths:
        kind = path_kind(root, relative)
        if kind == "symlink":
            symlinks.append(relative)
        elif kind == "file":
            paths.append(relative)
        else:
            non_files.append(relative)
    return Inventory(tuple(paths), method, tuple(symlinks), tuple(non_files))
