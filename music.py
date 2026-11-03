"""Royalty-free background music for the videos, composed on the spot (nothing is downloaded or licensed).

A short, warm corporate-pop loop is synthesised with numpy: a soft pad, a plucked arpeggio, a round bass and
a gentle kick and hat. It is mixed under the voiceover with ffmpeg's sidechain compressor, so the music dips
whenever someone is speaking and swells back between lines. Without a voiceover it plays at a normal level.
"""

from __future__ import annotations

import hashlib
import shutil
import tempfile
import wave
from pathlib import Path

import numpy as np

from video_maker import VideoError, media_duration, run_ffmpeg

SR = 44100
# name -> (tempo, root MIDI note, chord progression as (semitones from root, minor?))
MOODS = {
    "bright": (100, 60, [(0, 0), (7, 0), (9, 1), (5, 0)]),     # C  G  Am F   uplifting
    "warm": (88, 57, [(0, 1), (8, 0), (3, 0), (10, 0)]),       # Am F  C  G   reflective
    "lift": (104, 65, [(0, 0), (2, 0), (7, 1), (9, 1)]),       # F  G  Em Am  hopeful
}


def pick_mood(seed: str) -> str:
    """Same client, same music; different clients get different moods."""
    names = sorted(MOODS)
    return names[int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(names)]


def _hz(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def _triad(root: int, minor: bool) -> list[int]:
    return [root, root + (3 if minor else 4), root + 7]


def _add(buf: np.ndarray, start: float, sig: np.ndarray, pan: float = 0.0) -> None:
    """Mix a mono signal into the stereo buffer at `start` seconds (pan -1 left .. +1 right)."""
    i = int(start * SR)
    if i >= buf.shape[1]:
        return
    n = min(len(sig), buf.shape[1] - i)
    buf[0, i:i + n] += sig[:n] * (1 - max(pan, 0))
    buf[1, i:i + n] += sig[:n] * (1 + min(pan, 0))


def _tone(freq: float, dur: float, harmonics=(1.0, 0.35, 0.12), detune: float = 0.0) -> np.ndarray:
    t = np.arange(int(dur * SR)) / SR
    out = np.zeros_like(t)
    for k, amp in enumerate(harmonics, start=1):
        out += amp * np.sin(2 * np.pi * freq * k * (1 + detune) * t)
    return out


def compose(seconds: float, mood: str = "bright") -> np.ndarray:
    """Return a stereo float array (2, n) with a fade in and fade out."""
    tempo, key, prog = MOODS[mood]
    beat = 60.0 / tempo
    bar = beat * 4
    total = seconds + 0.5
    buf = np.zeros((2, int(total * SR)))
    rng = np.random.default_rng(7)

    for b in range(int(total / bar) + 2):
        t0 = b * bar
        offset, minor = prog[b % len(prog)]
        notes = _triad(key + offset, bool(minor))

        # pad: three slightly detuned voices per note, soft attack, overlapping into the next bar
        pad_len = bar + 0.6
        env = np.minimum(1, np.arange(int(pad_len * SR)) / (0.5 * SR)) * np.exp(-np.arange(int(pad_len * SR)) / (SR * 4.5))
        for n in notes:
            for d in (-0.003, 0.0, 0.003):
                _add(buf, t0, _tone(_hz(n), pad_len, detune=d) * env * 0.045, pan=(d * 100))

        # bass: root, one octave down, two pushes per bar
        for half in (0, 2):
            ln = beat * 1.9
            e = np.minimum(1, np.arange(int(ln * SR)) / (0.02 * SR)) * np.exp(-np.arange(int(ln * SR)) / (SR * 0.9))
            _add(buf, t0 + half * beat, _tone(_hz(notes[0] - 24), ln, (1.0, 0.25)) * e * 0.17)

        # arpeggio: eighth-note plucks climbing through the chord, a touch of stereo movement
        pattern = [0, 1, 2, 1, 0, 2, 1, 2]
        for s, idx in enumerate(pattern):
            note = notes[idx] + (12 if s in (2, 6) else 0)
            ln = beat * 1.2
            e = np.exp(-np.arange(int(ln * SR)) / (SR * 0.16)) * np.minimum(1, np.arange(int(ln * SR)) / (0.008 * SR))
            _add(buf, t0 + s * beat / 2, _tone(_hz(note + 12), ln, (1.0, 0.2)) * e * 0.085, pan=0.45 if s % 2 else -0.45)

        # kick on 1 and 3 (softer on 2 and 4), closed hat on the off-beats
        for bt in range(4):
            amp = 0.30 if bt in (0, 2) else 0.14
            n = int(0.22 * SR)
            tt = np.arange(n) / SR
            freq = 48 + 95 * np.exp(-tt * 35)                       # pitch drops from ~140 Hz to 48 Hz: a soft thump
            kick = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-tt * 18)
            _add(buf, t0 + bt * beat, kick * amp)
            hat = np.diff(rng.standard_normal(int(0.05 * SR) + 1)) * np.exp(-np.arange(int(0.05 * SR)) / (SR * 0.012))
            _add(buf, t0 + bt * beat + beat / 2, hat * 0.04, pan=0.3)

    # a little space: two feedback-style echoes, swapped between the channels
    wet = np.zeros_like(buf)
    for delay, gain in ((0.19, 0.30), (0.37, 0.20), (0.61, 0.12)):
        d = int(delay * SR)
        wet[0, d:] += buf[1, :-d] * gain
        wet[1, d:] += buf[0, :-d] * gain
    buf = (buf + wet)[:, :int(seconds * SR)]

    peak = np.max(np.abs(buf)) or 1.0
    buf = buf / peak * 0.85
    n = buf.shape[1]
    fade_in, fade_out = min(int(1.5 * SR), n // 4), min(int(2.5 * SR), n // 3)
    buf[:, :fade_in] *= np.linspace(0, 1, fade_in)
    buf[:, n - fade_out:] *= np.linspace(1, 0, fade_out)
    return buf


def write_wav(path: Path, data: np.ndarray) -> None:
    pcm = (np.clip(data, -1, 1) * 32767).astype("<i2").T.copy()
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def _has_audio(video: Path) -> bool:
    import subprocess
    from video_maker import ffmpeg_exe
    proc = subprocess.run([ffmpeg_exe(), "-hide_banner", "-i", str(video)], capture_output=True, text=True)
    return "Audio:" in proc.stderr


def add_background_music(video: Path, seed: str = "") -> Path:
    """Mix generated music into `video` in place (ducked under any voiceover) and return the same path."""
    video = Path(video)
    seconds = media_duration(video)
    if seconds <= 0:
        raise VideoError("Could not read the video length to add music.")
    with tempfile.TemporaryDirectory(prefix="music-") as tmp:
        work = Path(tmp)
        wav = work / "track.wav"
        write_wav(wav, compose(seconds, pick_mood(seed)))
        out = work / "mixed.mp4"
        if _has_audio(video):
            graph = ("[1:a]volume=0.40[m];[0:a]aformat=channel_layouts=stereo,asplit=2[v][sc];"
                     "[m][sc]sidechaincompress=threshold=0.015:ratio=12:attack=15:release=450:makeup=1[duck];"
                     "[v][duck]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[aout]")
        else:
            graph = "[1:a]volume=0.8,loudnorm=I=-16:TP=-1.5:LRA=11[aout]"
        run_ffmpeg(["-i", str(video), "-i", str(wav), "-filter_complex", graph, "-map", "0:v", "-map", "[aout]",
                    "-c:v", "copy", "-c:a", "aac", "-ar", "44100", "-b:a", "192k", "-t", f"{seconds:.2f}", "-movflags", "+faststart",
                    str(out)])
        shutil.move(str(out), str(video))      # may cross drives, so not os.replace
    return video
