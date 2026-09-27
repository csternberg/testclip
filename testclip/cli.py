"""Command-line interface for testclip."""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

from . import __version__
from .encode import EncodeError
from .encode import run as run_encode
from .naming import assign_filenames
from .prereqs import (
    PrerequisiteError,
    check_codec_available,
    check_ffmpeg_binary,
    check_output_dir,
    get_available_encoders,
)
from .resolutions import PRESETS, ResolutionError, parse_resolution
from .spec import build_matrix
from .video_filters import PATTERN_DESCRIPTIONS

PATTERNS = list(PATTERN_DESCRIPTIONS)
CODECS = ["h264", "h265", "vp9", "prores", "raw"]
CONTAINERS = ["mp4", "mkv", "webm", "mov", "avi"]
AUDIO_MODES = ["none", "tone", "noise", "beep", "melody"]
NOTE_SCALES = ["chromatic", "major", "minor", "pentatonic"]


def _csv_choice(raw: str, choices: list[str], label: str) -> list[str]:
    values = [v.strip().lower() for v in raw.split(",") if v.strip()]
    if not values:
        raise argparse.ArgumentTypeError(f"No {label} given.")
    bad = [v for v in values if v not in choices]
    if bad:
        raise argparse.ArgumentTypeError(
            f"Unknown {label}: {', '.join(bad)}. Valid options: {', '.join(choices)}"
        )
    return values


def _csv_resolutions(raw: str) -> list[tuple[int, int]]:
    try:
        return [parse_resolution(v) for v in raw.split(",")]
    except ResolutionError as exc:
        raise argparse.ArgumentTypeError(str(exc))


def _csv_ints(raw: str, label: str) -> list[int]:
    values = []
    for v in raw.split(","):
        v = v.strip()
        try:
            n = int(v)
        except ValueError:
            raise argparse.ArgumentTypeError(f"Invalid {label} '{v}': must be an integer.")
        if n <= 0:
            raise argparse.ArgumentTypeError(f"Invalid {label} '{v}': must be positive.")
        values.append(n)
    return values


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="testclip",
        description="Generate one or more synthetic test video clips using ffmpeg.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--version", action="version", version=f"testclip {__version__}")
    p.add_argument(
        "--list-patterns", action="store_true",
        help="List available --pattern values with descriptions and exit.",
    )

    content = p.add_argument_group("content")
    content.add_argument(
        "--pattern", type=lambda s: _csv_choice(s, PATTERNS, "pattern"), default=None,
        help="Comma-separated pattern(s): " + ", ".join(PATTERNS),
    )
    content.add_argument(
        "--color", default="black", help="Fill color, used only with --pattern color."
    )
    content.add_argument(
        "--burn-in-timecode", action="store_true",
        help="Overlay a frame counter + timestamp on top of any pattern.",
    )

    geometry = p.add_argument_group("geometry / timing")
    geometry.add_argument("--duration", type=float, default=5.0, help="Clip length in seconds.")
    geometry.add_argument(
        "--resolution", type=_csv_resolutions, default="1280x720",
        help="Comma-separated WxH or preset(s): " + ", ".join(PRESETS),
    )
    geometry.add_argument(
        "--fps", type=lambda s: _csv_ints(s, "fps"), default="30",
        help="Comma-separated frame rate(s).",
    )

    enc = p.add_argument_group("encoding")
    enc.add_argument(
        "--codec", type=lambda s: _csv_choice(s, CODECS, "codec"), default="h264",
        help="Comma-separated codec(s): " + ", ".join(CODECS),
    )
    enc.add_argument(
        "--container", choices=CONTAINERS, default=None,
        help="Output container; default is derived from --codec.",
    )
    enc.add_argument(
        "--pixel-format", default=None,
        help="Pixel format; default is codec-appropriate (e.g. yuv420p).",
    )
    enc.add_argument(
        "--crf", type=int, default=None,
        help="Constant rate factor (quality); default is codec-specific.",
    )
    enc.add_argument(
        "--bitrate", default=None,
        help="Target video bitrate, e.g. 2M. Overrides --crf when set.",
    )

    audio = p.add_argument_group("audio")
    audio.add_argument(
        "--audio", type=lambda s: _csv_choice(s, AUDIO_MODES, "audio mode"), default="none",
        help="Comma-separated audio mode(s): " + ", ".join(AUDIO_MODES),
    )
    audio.add_argument(
        "--audio-freq", type=float, default=None,
        help="Tone/beep frequency in Hz (default 440 for tone, 1000 for beep).",
    )
    audio.add_argument(
        "--beep-interval", type=float, default=1.0, help="Seconds between beeps, for --audio beep."
    )
    audio.add_argument(
        "--note-duration", type=float, default=0.25,
        help="Seconds per note/rest slot, for --audio melody.",
    )
    audio.add_argument(
        "--note-scale", choices=NOTE_SCALES, default="major",
        help="Pitch pool for --audio melody.",
    )
    audio.add_argument(
        "--root-freq", type=float, default=440.0,
        help="Base note frequency in Hz, for --audio melody.",
    )
    audio.add_argument(
        "--rest-probability", type=float, default=0.15,
        help="Chance a melody slot is silence, for --audio melody.",
    )

    batch = p.add_argument_group("batch / output")
    batch.add_argument(
        "--count", type=int, default=1, help="Number of clips per parameter combination."
    )
    batch.add_argument(
        "--name", default=None,
        help="Base filename (default: auto-generated, e.g. test-clip_smptebars_01.mp4).",
    )
    batch.add_argument(
        "--output-dir", default="./output", help="Directory to write clips into."
    )
    batch.add_argument(
        "--overwrite", action="store_true",
        help="Reuse/overwrite existing filenames instead of incrementing past them.",
    )
    batch.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for reproducible noise/melody content.",
    )
    batch.add_argument(
        "--dry-run", action="store_true",
        help="Print planned filenames and ffmpeg commands without encoding.",
    )

    verbosity = p.add_mutually_exclusive_group()
    verbosity.add_argument(
        "--verbose", action="store_true", help="Print ffmpeg commands as they run."
    )
    verbosity.add_argument(
        "--quiet", action="store_true", help="Only print errors and the final summary."
    )

    return p


def _print_pattern_list() -> None:
    width = max(len(name) for name in PATTERN_DESCRIPTIONS)
    for name, desc in PATTERN_DESCRIPTIONS.items():
        print(f"  {name:<{width}}  {desc}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_patterns:
        _print_pattern_list()
        return 0

    if not args.pattern:
        parser.error("--pattern is required (see --list-patterns).")
    if args.duration <= 0:
        parser.error("--duration must be positive.")
    if args.count <= 0:
        parser.error("--count must be positive.")
    if not (0.0 <= args.rest_probability <= 1.0):
        parser.error("--rest-probability must be between 0.0 and 1.0.")

    try:
        check_ffmpeg_binary()
        available_encoders = get_available_encoders()
        for codec in args.codec:
            check_codec_available(codec, available_encoders)
        output_dir = Path(args.output_dir)
        check_output_dir(output_dir)
    except PrerequisiteError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.seed is None:
        args.seed = random.randrange(2**31)
    if not args.quiet:
        print(f"Using seed: {args.seed}")

    specs = build_matrix(args, args.resolution)
    paths = assign_filenames(specs, output_dir, args.name, args.overwrite)

    if not args.quiet:
        verb = "Would generate" if args.dry_run else "Planned"
        print(f"{verb} {len(specs)} clip(s) in '{output_dir}':")
        for path in paths:
            print(f"  {path.name}")

    succeeded = 0
    failed: list[str] = []
    for spec, path in zip(specs, paths):
        if not args.quiet:
            print(f"{'Would encode' if args.dry_run else 'Encoding'} {path.name} ...")
        try:
            run_encode(spec, path, dry_run=args.dry_run, verbose=args.verbose)
            succeeded += 1
        except EncodeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            failed.append(path.name)
        except KeyboardInterrupt:
            print("\nInterrupted -- cleaning up partial file.", file=sys.stderr)
            if path.exists():
                path.unlink(missing_ok=True)
            raise

    if not args.dry_run and not args.quiet:
        print(f"\nDone: {succeeded} succeeded, {len(failed)} failed.")
        for name in failed:
            print(f"  failed: {name}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
