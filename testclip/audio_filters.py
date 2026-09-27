"""Builds ffmpeg lavfi audio source strings for each --audio mode."""
from __future__ import annotations

import random

SAMPLE_RATE = 44100

# Semitone offsets from the root, within one octave.
SCALES = {
    "chromatic": list(range(12)),
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "pentatonic": [0, 2, 4, 7, 9],
}


def build_audio_source(
    mode: str,
    duration: float,
    freq: float | None,
    seed: int | None = None,
    beep_interval: float = 1.0,
    note_duration: float = 0.25,
    note_scale: str = "major",
    root_freq: float = 440.0,
    rest_probability: float = 0.15,
) -> str | None:
    if mode == "none":
        return None

    if mode == "tone":
        f = freq if freq is not None else 440.0
        return f"sine=frequency={f}:duration={duration}:sample_rate={SAMPLE_RATE}"

    if mode == "noise":
        seed_val = seed if seed is not None else 0
        return f"anoisesrc=duration={duration}:color=white:seed={seed_val}"

    if mode == "beep":
        f = freq if freq is not None else 1000.0
        expr = f"if(lt(mod(t\\,{beep_interval})\\,0.1)\\,sin(2*PI*{f}*t)\\,0)"
        return f"aevalsrc=exprs='{expr}':duration={duration}:sample_rate={SAMPLE_RATE}"

    if mode == "melody":
        rng = random.Random(seed)
        intervals = SCALES[note_scale]
        n_slots = max(1, int(duration / note_duration))
        segments = []
        for i in range(n_slots):
            if rng.random() < rest_probability:
                segments.append(
                    f"anullsrc=r={SAMPLE_RATE}:cl=mono:duration={note_duration}[a{i}]"
                )
            else:
                semitone = rng.choice(intervals) + 12 * rng.choice([0, 1])
                note_freq = root_freq * (2 ** (semitone / 12))
                segments.append(
                    f"sine=frequency={note_freq:.2f}:duration={note_duration}:"
                    f"sample_rate={SAMPLE_RATE}[a{i}]"
                )
        chain = ";".join(segments)
        labels = "".join(f"[a{i}]" for i in range(n_slots))
        return f"{chain};{labels}concat=n={n_slots}:v=0:a=1"

    raise ValueError(f"Unknown audio mode: {mode}")
