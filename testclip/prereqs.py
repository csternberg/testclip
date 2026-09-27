"""Startup checks: ffmpeg availability, encoder support, output dir writability."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class PrerequisiteError(RuntimeError):
    pass


def check_ffmpeg_binary() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise PrerequisiteError(
            "ffmpeg was not found on PATH.\n"
            "Install it and make sure it's on PATH:\n"
            "  Windows (winget):  winget install Gyan.FFmpeg\n"
            "  Windows (choco):   choco install ffmpeg\n"
            "  macOS (brew):      brew install ffmpeg\n"
            "  Linux (apt):       sudo apt install ffmpeg"
        )
    return path


def get_available_encoders() -> set[str]:
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            capture_output=True, text=True, check=True, timeout=15,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        raise PrerequisiteError(f"Failed to query ffmpeg encoders: {exc}")
    encoders = set()
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and (line.startswith(" V") or line.startswith(" A")):
            encoders.add(parts[1])
    return encoders


CODEC_ENCODERS = {
    "h264": "libx264",
    "h265": "libx265",
    "vp9": "libvpx-vp9",
    "prores": "prores_ks",
    "raw": "rawvideo",
}


def check_codec_available(codec: str, available_encoders: set[str]) -> None:
    encoder = CODEC_ENCODERS[codec]
    if encoder not in available_encoders:
        raise PrerequisiteError(
            f"The '{codec}' codec requires the '{encoder}' encoder, which this ffmpeg "
            f"build does not have. Run 'ffmpeg -encoders' to see what's available, or "
            f"install a full ffmpeg build (e.g. the gyan.dev 'full' build on Windows)."
        )


def check_output_dir(path: Path) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise PrerequisiteError(f"Cannot create output directory '{path}': {exc}")
    probe = path / ".testclip_write_check"
    try:
        probe.write_text("ok")
        probe.unlink()
    except OSError as exc:
        raise PrerequisiteError(f"Output directory '{path}' is not writable: {exc}")
