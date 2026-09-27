"""Resolution presets and parsing."""

PRESETS = {
    "480p": (854, 480),
    "720p": (1280, 720),
    "1080p": (1920, 1080),
    "1440p": (2560, 1440),
    "4k": (3840, 2160),
}


class ResolutionError(ValueError):
    pass


def parse_resolution(value: str) -> tuple[int, int]:
    value = value.strip().lower()
    if value in PRESETS:
        return PRESETS[value]
    if "x" not in value:
        raise ResolutionError(
            f"Invalid resolution '{value}'. Use WIDTHxHEIGHT (e.g. 1920x1080) "
            f"or a preset: {', '.join(PRESETS)}"
        )
    w_str, _, h_str = value.partition("x")
    try:
        w, h = int(w_str), int(h_str)
    except ValueError:
        raise ResolutionError(f"Invalid resolution '{value}'. Width/height must be integers.")
    if w <= 0 or h <= 0:
        raise ResolutionError(f"Invalid resolution '{value}'. Width/height must be positive.")
    if w % 2 or h % 2:
        raise ResolutionError(
            f"Invalid resolution '{value}'. Width and height must be even numbers "
            f"(required by most video codecs)."
        )
    return w, h
