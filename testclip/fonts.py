"""Best-effort discovery of a usable font file for ffmpeg's drawtext filter.

Some ffmpeg builds (notably Windows gyan.dev builds) have fontconfig compiled
in but no fontconfig config file present, so drawtext's default font lookup
fails outright. Passing an explicit fontfile= sidesteps that entirely.
"""
from __future__ import annotations

import platform
from functools import lru_cache
from pathlib import Path

_CANDIDATES = {
    "Windows": [
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\consola.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
    ],
    "Darwin": [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "Linux": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
    ],
}


@lru_cache(maxsize=1)
def find_font_file() -> str | None:
    for candidate in _CANDIDATES.get(platform.system(), []):
        if Path(candidate).is_file():
            return candidate
    return None
