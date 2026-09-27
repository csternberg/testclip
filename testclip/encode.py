"""Assembles and runs the ffmpeg command for a single ClipSpec."""
from __future__ import annotations

import sys
from pathlib import Path

import ffmpeg

from .fonts import find_font_file

from .audio_filters import build_audio_source
from .video_filters import build_video_source

AUDIO_CODEC_BY_CONTAINER = {
    "mp4": "aac",
    "mov": "pcm_s16le",
    "mkv": "aac",
    "webm": "libopus",
    "avi": "pcm_s16le",
}

VIDEO_ENCODER = {
    "h264": "libx264",
    "h265": "libx265",
    "vp9": "libvpx-vp9",
    "prores": "prores_ks",
    "raw": "rawvideo",
}


class EncodeError(RuntimeError):
    pass


def _with_burn_in(graph: str) -> str:
    drawtext = (
        r",drawtext=text='Frame\: %{n}  |  %{pts\:hms}'"
        r":x=10:y=10:fontsize=28:fontcolor=white"
        r":box=1:boxcolor=black@0.5:boxborderw=6"
    )
    font_file = find_font_file()
    if font_file:
        # Escape drive-letter colon and backslashes for ffmpeg filter syntax.
        escaped = font_file.replace("\\", "/").replace(":", r"\:")
        drawtext += f":fontfile='{escaped}'"
    return graph + drawtext


def build_command(spec, output_path: Path):
    video_graph = build_video_source(
        spec.pattern, spec.width, spec.height, spec.fps, spec.duration,
        color=spec.color, seed=spec.seed,
    )
    if spec.burn_in_timecode:
        video_graph = _with_burn_in(video_graph)

    video_in = ffmpeg.input(video_graph, f="lavfi")

    audio_graph = build_audio_source(
        spec.audio_mode, spec.duration, spec.audio_freq, seed=spec.seed,
        beep_interval=spec.beep_interval, note_duration=spec.note_duration,
        note_scale=spec.note_scale, root_freq=spec.root_freq,
        rest_probability=spec.rest_probability,
    )

    output_kwargs = {
        "vcodec": VIDEO_ENCODER[spec.codec],
        "pix_fmt": spec.pixel_format,
        "r": spec.fps,
        "t": spec.duration,
    }
    if spec.bitrate:
        output_kwargs["b:v"] = spec.bitrate
    elif spec.crf is not None:
        output_kwargs["crf"] = spec.crf
        if spec.codec == "vp9":
            output_kwargs["b:v"] = "0"  # required for libvpx-vp9 constant-quality mode
    if spec.codec == "prores":
        output_kwargs["profile:v"] = 2  # "standard"

    if audio_graph:
        audio_in = ffmpeg.input(audio_graph, f="lavfi")
        output_kwargs["acodec"] = AUDIO_CODEC_BY_CONTAINER.get(spec.container, "aac")
        streams = (video_in, audio_in)
    else:
        streams = (video_in,)

    return ffmpeg.output(*streams, str(output_path), **output_kwargs).overwrite_output()


def run(spec, output_path: Path, dry_run: bool = False, verbose: bool = False) -> None:
    cmd = build_command(spec, output_path)
    if dry_run or verbose:
        print("  $ " + " ".join(ffmpeg.compile(cmd)), file=sys.stderr)
    if dry_run:
        return
    try:
        ffmpeg.run(cmd, capture_stdout=True, capture_stderr=True)
    except ffmpeg.Error as exc:
        stderr = exc.stderr.decode(errors="replace") if exc.stderr else ""
        tail = "\n".join(stderr.strip().splitlines()[-15:])
        raise EncodeError(f"ffmpeg failed encoding '{output_path.name}':\n{tail}") from exc
