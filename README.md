# testclip

A small command-line utility for generating synthetic test video clips with
[ffmpeg](https://ffmpeg.org/) — color bars, gradients, noise, a bouncing ball,
plasma patterns, burnt-in timecodes, and procedurally generated "melody"
audio, across whatever resolutions/framerates/codecs you need to test
against.

## Prerequisites

- **ffmpeg** on your `PATH`, with the encoders you plan to use
  (`libx264`, `libx265`, `libvpx-vp9`, `prores_ks` are all part of most full
  builds). `testclip` checks for this at startup and tells you what's missing.
  - Windows: `winget install Gyan.FFmpeg` or `choco install ffmpeg`
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt install ffmpeg`
- **Python 3.10+**

## Install

```bash
pip install -r requirements.txt
```

or, for the `testclip` console command:

```bash
pip install -e .
```

## Usage

```bash
python -m testclip --pattern smptebars
```

(or just `testclip --pattern smptebars` if installed with `pip install -e .`)

List available patterns:

```bash
python -m testclip --list-patterns
```

Full option reference:

```bash
python -m testclip --help
```

## Examples

Five-second SMPTE bars at the defaults (1280x720, 30fps, h264/mp4):

```bash
python -m testclip --pattern smptebars
```

A batch covering every pattern at two resolutions, with a burnt-in frame
counter for seek/sync testing:

```bash
python -m testclip --pattern color,smptebars,gradient,checkerboard,noise,ball,plasma,timecode \
    --resolution 720p,1080p --burn-in-timecode
```

A 30-second H.265 clip with a procedurally generated melody track:

```bash
python -m testclip --pattern gradient --duration 30 --codec h265 \
    --audio melody --note-scale pentatonic --seed 42
```

Three noisy clips with reproducible static and a beep track:

```bash
python -m testclip --pattern noise --count 3 --audio beep --beep-interval 0.5 --seed 7
```

Preview the exact ffmpeg commands without encoding anything:

```bash
python -m testclip --pattern plasma --dry-run --verbose
```

## Options

### Content

| Flag | Description |
| --- | --- |
| `--pattern <list>` | Comma-separated pattern(s). Required. See `--list-patterns`. |
| `--color <name\|hex>` | Fill color, only used with `--pattern color`. Default `black`. |
| `--burn-in-timecode` | Overlay a frame counter + timestamp on top of any pattern. |

Patterns: `color`, `smptebars`, `gradient`, `checkerboard`, `noise`, `ball`,
`plasma`, `timecode` (a moving pattern with built-in frame/resolution markers).

### Geometry / timing

| Flag | Description |
| --- | --- |
| `--duration <seconds>` | Clip length. Default `5`. |
| `--resolution <list>` | Comma-separated `WxH` or presets (`480p`, `720p`, `1080p`, `1440p`, `4k`). Default `1280x720`. |
| `--fps <list>` | Comma-separated frame rate(s). Default `30`. |

### Encoding

| Flag | Description |
| --- | --- |
| `--codec <list>` | `h264`, `h265`, `vp9`, `prores`, `raw`. Default `h264`. |
| `--container <fmt>` | `mp4`, `mkv`, `webm`, `mov`, `avi`. Default is derived from `--codec`. |
| `--pixel-format <fmt>` | Default is codec-appropriate (e.g. `yuv420p`). |
| `--crf <n>` | Constant rate factor (quality). Default is codec-specific. |
| `--bitrate <rate>` | Target video bitrate, e.g. `2M`. Overrides `--crf` when set. |

### Audio

| Flag | Description |
| --- | --- |
| `--audio <list>` | `none`, `tone`, `noise`, `beep`, `melody`. Default `none`. |
| `--audio-freq <hz>` | Tone/beep frequency. Default `440` for tone, `1000` for beep. |
| `--beep-interval <sec>` | Seconds between beeps (`--audio beep`). Default `1.0`. |
| `--note-duration <sec>` | Seconds per note/rest slot (`--audio melody`). Default `0.25`. |
| `--note-scale <scale>` | `chromatic`, `major`, `minor`, `pentatonic`. Default `major`. |
| `--root-freq <hz>` | Base note frequency (`--audio melody`). Default `440`. |
| `--rest-probability <0-1>` | Chance a melody slot is silence. Default `0.15`. |

`melody` is fully synthetic — procedurally generated tone/rest sequences via
ffmpeg's `sine`/`anullsrc` sources, not real music. No samples, no licensing
concerns, and every note boundary is an exact, reproducible timestamp, which
is handy for A/V sync testing.

### Batch / output

| Flag | Description |
| --- | --- |
| `--count <n>` | Number of clips per parameter combination. Default `1`. |
| `--name "<name>"` | Explicit base filename (disables auto-naming; an index suffix is still appended). |
| `--output-dir <path>` | Default `./output`. |
| `--overwrite` | Reuse/overwrite existing filenames instead of incrementing past them. |
| `--seed <n>` | Random seed, for reproducible noise/melody content. |
| `--dry-run` | Print planned filenames and ffmpeg commands without encoding. |
| `--verbose` / `--quiet` | Print ffmpeg commands as they run / only print errors and the summary. |

Any of `--pattern`, `--resolution`, `--fps`, `--codec`, `--audio` accepts a
comma-separated list, which expands into the full cartesian product — e.g.
`--pattern noise,gradient --resolution 720p,1080p` produces 4 clips.

## Naming

Default filenames look like `test-clip_<pattern>_<xx>.<ext>`, where `xx` is a
zero-padded counter. If a batch run varies a parameter (resolution, fps,
duration, codec, or audio mode) across its clips, that parameter is folded
into the name automatically so the files stay distinguishable, e.g.
`test-clip_noise_1920x1080_60fps_01.mp4`. A single-parameter run stays plain,
e.g. `test-clip_smptebars_01.mp4`.

Without `--overwrite`, the counter always continues past whatever's already
in the output directory, so reruns never clobber earlier clips. With
`--overwrite`, each base name restarts at `01`, so repeated runs reuse the
same set of filenames.

## Error handling

- Checks for the `ffmpeg` binary and the specific encoder each requested
  `--codec` needs before generating anything, with install hints if missing.
- Validates the full parameter matrix up front rather than failing partway
  through a batch.
- If one clip in a batch fails to encode, `testclip` reports the ffmpeg error
  and continues with the rest, then exits non-zero with a summary of
  successes/failures.
- Ctrl-C cleans up the partially-written output file instead of leaving a
  truncated video behind.
