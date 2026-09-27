"""Filename generation: descriptive defaults, or --name, with collision-safe indexing.

Default naming is `test-clip_<pattern>_<xx>.<ext>`. When a batch varies a
parameter (resolution, fps, duration, codec, or audio) across its clips, that
parameter is folded into the base name automatically so the files stay
distinguishable, e.g. `test-clip_noise_1920x1080_60fps_01.mp4`.

Without --overwrite, indexing always continues past whatever already exists
in the output directory, so a rerun never clobbers earlier clips. With
--overwrite, each base name restarts at 01 so repeated runs reuse the same
filenames.
"""
from __future__ import annotations

import re
from pathlib import Path


def _varying_fields(specs) -> set[str]:
    varying = set()
    checks = {
        "resolution": lambda s: (s.width, s.height),
        "fps": lambda s: s.fps,
        "duration": lambda s: s.duration,
        "codec": lambda s: s.codec,
        "audio": lambda s: s.audio_mode,
    }
    for name, getter in checks.items():
        if len({getter(s) for s in specs}) > 1:
            varying.add(name)
    return varying


def _base_name(spec, varying: set[str], explicit_name: str | None) -> str:
    if explicit_name:
        return explicit_name
    parts = ["test-clip", spec.pattern]
    if "resolution" in varying:
        parts.append(f"{spec.width}x{spec.height}")
    if "fps" in varying:
        parts.append(f"{spec.fps}fps")
    if "duration" in varying:
        parts.append(f"{spec.duration:g}s")
    if "codec" in varying:
        parts.append(spec.codec)
    if "audio" in varying and spec.audio_mode != "none":
        parts.append(spec.audio_mode)
    return "_".join(parts)


def _existing_max_index(output_dir: Path, base: str, ext: str) -> int:
    pattern = re.compile(rf"^{re.escape(base)}_(\d+)\.{re.escape(ext)}$")
    max_idx = 0
    for entry in output_dir.glob(f"{base}_*.{ext}"):
        match = pattern.match(entry.name)
        if match:
            max_idx = max(max_idx, int(match.group(1)))
    return max_idx


def assign_filenames(
    specs, output_dir: Path, explicit_name: str | None, overwrite: bool
) -> list[Path]:
    varying = _varying_fields(specs)
    next_index: dict[tuple[str, str], int] = {}
    paths = []

    for spec in specs:
        base = _base_name(spec, varying, explicit_name)
        ext = spec.container
        key = (base, ext)

        if key not in next_index:
            next_index[key] = 1 if overwrite else _existing_max_index(output_dir, base, ext) + 1

        idx = next_index[key]
        next_index[key] += 1
        paths.append(output_dir / f"{base}_{idx:02d}.{ext}")

    return paths
