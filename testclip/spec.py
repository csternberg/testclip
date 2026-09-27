"""Defines a single clip's parameters and expands CLI args into a batch."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product


@dataclass
class ClipSpec:
    pattern: str
    width: int
    height: int
    fps: int
    duration: float
    codec: str
    container: str
    pixel_format: str
    crf: int | None
    bitrate: str | None
    color: str
    audio_mode: str
    audio_freq: float | None
    seed: int | None
    beep_interval: float
    note_duration: float
    note_scale: str
    root_freq: float
    rest_probability: float
    burn_in_timecode: bool
    index: int = 0


CODEC_DEFAULT_CONTAINER = {
    "h264": "mp4",
    "h265": "mp4",
    "vp9": "webm",
    "prores": "mov",
    "raw": "avi",
}

CODEC_DEFAULT_CRF = {
    "h264": 23,
    "h265": 28,
    "vp9": 31,
    "prores": None,
    "raw": None,
}

CODEC_DEFAULT_PIXFMT = {
    "h264": "yuv420p",
    "h265": "yuv420p",
    "vp9": "yuv420p",
    "prores": "yuv422p10le",
    "raw": "yuv420p",
}


def build_matrix(args, resolutions) -> list[ClipSpec]:
    combos = product(args.pattern, resolutions, args.fps, args.codec, args.audio)
    specs = []
    for pattern, (w, h), fps, codec, audio_mode in combos:
        container = args.container or CODEC_DEFAULT_CONTAINER[codec]
        pixel_format = args.pixel_format or CODEC_DEFAULT_PIXFMT[codec]
        crf = args.crf if args.crf is not None else CODEC_DEFAULT_CRF[codec]
        for i in range(args.count):
            specs.append(
                ClipSpec(
                    pattern=pattern,
                    width=w,
                    height=h,
                    fps=fps,
                    duration=args.duration,
                    codec=codec,
                    container=container,
                    pixel_format=pixel_format,
                    crf=crf,
                    bitrate=args.bitrate,
                    color=args.color,
                    audio_mode=audio_mode,
                    audio_freq=args.audio_freq,
                    seed=args.seed,
                    beep_interval=args.beep_interval,
                    note_duration=args.note_duration,
                    note_scale=args.note_scale,
                    root_freq=args.root_freq,
                    rest_probability=args.rest_probability,
                    burn_in_timecode=args.burn_in_timecode,
                    index=i,
                )
            )
    return specs
