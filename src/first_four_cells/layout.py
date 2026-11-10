"""Resolve the canonical and the twice-extracted Nantes folder layouts."""

from pathlib import Path


def source_folder(root: Path, name: str, suffix: str) -> Path:
    choices = [
        directory
        for base in (root, root / "raw")
        for directory in (base / name, base / name / name)
        if directory.is_dir() and next(directory.glob("*" + suffix), None)
    ]
    if len(choices) != 1:
        raise ValueError(f"Expected one {name} folder under {root}; found {choices}")
    return choices[0]
