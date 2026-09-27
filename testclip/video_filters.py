"""Builds ffmpeg lavfi filtergraph strings for each video test pattern.

Every builder returns a single, self-contained filtergraph description
suitable for `ffmpeg -f lavfi -i "<graph>"`. Each graph ends on exactly one
unlabeled/unconsumed output pad, so a burnt-in timecode overlay can always be
appended with a trailing `,drawtext=...`.
"""
from __future__ import annotations

PATTERN_DESCRIPTIONS = {
    "color": "Flat solid color fill (see --color)",
    "smptebars": "Classic SMPTE broadcast color bars",
    "gradient": "Smooth animated color gradient",
    "checkerboard": "Static black/white checkerboard grid",
    "noise": "Random static/noise",
    "ball": "A ball bouncing around the frame (motion/seek test)",
    "plasma": "Animated sinusoidal 'plasma' pattern (compression stress test)",
    "timecode": "Moving test pattern with built-in frame/resolution markers",
}


def _esc(value: str) -> str:
    return value.replace(":", r"\:").replace("'", r"\'")


def build_video_source(
    pattern: str,
    width: int,
    height: int,
    fps: int,
    duration: float,
    color: str = "black",
    seed: int | None = None,
) -> str:
    size = f"{width}x{height}"
    seed_val = seed if seed is not None else 0

    if pattern == "color":
        return f"color=c={_esc(color)}:s={size}:r={fps}:d={duration}"

    if pattern == "smptebars":
        src = "smptehdbars" if width >= 1280 else "smptebars"
        return f"{src}=s={size}:r={fps}:d={duration}"

    if pattern == "gradient":
        return f"gradients=s={size}:r={fps}:d={duration}:speed=0.02"

    if pattern == "checkerboard":
        tile = max(8, min(width, height) // 10)
        return (
            f"color=c=black:s={size}:r={fps}:d={duration},"
            f"geq=lum='if(eq(mod(floor(X/{tile})+floor(Y/{tile})\\,2)\\,0)\\,255\\,0)':"
            f"cb=128:cr=128"
        )

    if pattern == "noise":
        return (
            f"color=c=black:s={size}:r={fps}:d={duration},"
            f"noise=alls=100:allf=t+u:all_seed={seed_val}"
        )

    if pattern == "ball":
        bs = max(20, min(width, height) // 12)
        return (
            f"color=c=black:s={size}:r={fps}:d={duration}[bg];"
            f"color=c=red:s={bs}x{bs}:r={fps}:d={duration},"
            f"format=rgba,"
            f"geq=r=255:g=0:b=0:"
            f"a='if(lte(pow(X-W/2\\,2)+pow(Y-H/2\\,2)\\,pow(W/2\\,2))\\,255\\,0)'"
            f"[ball];"
            f"[bg][ball]overlay="
            f"x='abs(mod(t*220\\,2*({width}-{bs}))-({width}-{bs}))':"
            f"y='abs(mod(t*160\\,2*({height}-{bs}))-({height}-{bs}))'"
        )

    if pattern == "plasma":
        return (
            f"color=c=black:s={size}:r={fps}:d={duration},"
            f"geq="
            f"lum='128+127*sin(X/24+T*2)+64*sin(Y/18-T*1.5)':"
            f"cb='128+64*sin((X+Y)/32+T)':"
            f"cr='128+64*cos((X-Y)/32-T)'"
        )

    if pattern == "timecode":
        return f"testsrc2=s={size}:r={fps}:d={duration}"

    raise ValueError(f"Unknown pattern: {pattern}")
