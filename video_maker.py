"""Vertical (9:16) short video for TikTok / Reels / Shorts, built from the fact-checked content.

Two looks share one pipeline:
  * render_video    - animated branded slides, 100% offline and free (needs only Pillow + ffmpeg).
  * render_ai_film  - AI-generated cinematic shots (see ai_video.py) with captions and narration,
                      followed by a results card that carries the real numbers.

Optional free voiceover through edge-tts. No edge-tts or no internet -> a silent video.
"""

from __future__ import annotations

import asyncio
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from generator import BASE_DIR, ProjectDetails, slugify

W, H = 1080, 1920
FPS = 30
FADE = 0.35
MARGIN = 96
DEFAULT_VOICE = "en-US-AriaNeural"


class VideoError(Exception):
    """A problem the user should see (missing ffmpeg, render failure)."""


# --------------------------------------------------------------------------- #
# Helpers: ffmpeg, fonts, colours
# --------------------------------------------------------------------------- #
def ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:  # pragma: no cover - environment problem
        raise VideoError("ffmpeg is not available. Run: pip install imageio-ffmpeg") from exc


def run_ffmpeg(args: list[str]) -> str:
    proc = subprocess.run([ffmpeg_exe(), "-y", "-hide_banner", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise VideoError("ffmpeg failed: " + (proc.stderr.strip().splitlines() or ["unknown error"])[-1])
    return proc.stderr


def media_duration(path: Path) -> float:
    proc = subprocess.run([ffmpeg_exe(), "-hide_banner", "-i", str(path)], capture_output=True, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", proc.stderr)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]) if m else 0.0


_FONT_FILES = {
    True: ["segoeuib.ttf", "arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"],
    False: ["segoeui.ttf", "arial.ttf", "Arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"],
}
_FONT_DIRS = ["C:/Windows/Fonts", "/Library/Fonts", "/System/Library/Fonts/Supplemental",
              "/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/truetype/liberation", "/usr/share/fonts/TTF"]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for name in _FONT_FILES[bold]:
        for folder in _FONT_DIRS:
            path = Path(folder) / name
            if path.exists():
                return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size)


def hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    try:
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError:
        return (79, 70, 229)


def mix(a, b, t: float):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# --------------------------------------------------------------------------- #
# Story: which scenes, what they say
# --------------------------------------------------------------------------- #
@dataclass
class Scene:
    kind: str
    data: dict
    narration: str
    min_seconds: float


def _arrows(text: str) -> str:
    return text.replace("->", "→").replace("=>", "→")


def _first_sentences(text: str, limit: int = 150) -> str:
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    return cut[:end + 1] if end > 40 else cut.rsplit(" ", 1)[0].rstrip(",;:") + "..."


def _best_quote(quotes: list[dict]) -> dict | None:
    if not quotes:
        return None
    short_enough = [q for q in quotes if len(q["text"].split()) <= 38]
    pool = short_enough or quotes
    return max(pool, key=lambda q: len(q["text"])) if short_enough else min(pool, key=lambda q: len(q["text"]))


def build_scenes(content: dict, details: ProjectDetails) -> list[Scene]:
    cs = content["case_study"]
    client = details.client_name
    metrics = [m for m in cs.get("key_metrics", []) if str(m.get("value", "")).strip()][:3]
    scenes: list[Scene] = []

    if metrics:
        lead = metrics[0]
        hook = {"big": str(lead["value"]), "label": str(lead["label"]), "title": cs["title"], "client": client}
        spoken = f"{lead['label']}: {lead['value']}. Here is how {client} did it."
    else:
        hook = {"big": "", "label": "", "title": cs["title"], "client": client}
        spoken = cs["title"]
    scenes.append(Scene("hook", hook, spoken, 3.6))

    challenge = _first_sentences(cs["challenge"])
    scenes.append(Scene("challenge", {"text": challenge}, "The challenge. " + challenge, 4.5))

    if metrics:
        rows = [{"value": str(m["value"]), "label": str(m["label"])} for m in metrics]
        spoken = "The results. " + ". ".join(f"{r['label']}, {r['value']}" for r in rows[:2])
    else:
        rows = [{"value": "", "label": _first_sentences(r, 90)} for r in cs["results"][:3]]
        spoken = "The results. " + " ".join(r["label"] for r in rows)
    scenes.append(Scene("results", {"rows": rows}, spoken, 5.0))

    quote = _best_quote(content["testimonials"])
    if quote:
        who = ", ".join(x for x in (quote.get("speaker_name", ""), quote.get("speaker_role", ""), client) if x)
        scenes.append(Scene("quote", {"text": quote["text"], "who": who}, quote["text"], 6.0))

    scenes.append(Scene("cta", {"agency": details.agency_name}, f"Want results like this? Talk to {details.agency_name}.", 3.4))
    return scenes


# --------------------------------------------------------------------------- #
# Drawing
# --------------------------------------------------------------------------- #
class Layer:
    """A transparent canvas that stacks centred text blocks from the top down."""

    def __init__(self) -> None:
        self.img = Image.new("RGBA", (W, 2400), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)
        self.y = 0

    def gap(self, px: int) -> None:
        self.y += px

    def text(self, text: str, size: int, fill, bold: bool = False, max_lines: int = 6,
             width: int = W - 2 * MARGIN, spacing: float = 1.22, min_size: int = 34) -> None:
        while True:
            f = font(size, bold)
            lines = self._wrap(text, f, width)
            if (len(lines) <= max_lines and all(self.d.textlength(l, font=f) <= width for l in lines)) or size <= min_size:
                break
            size -= 4
        for line in lines:
            w = self.d.textlength(line, font=f)
            self.d.text(((W - w) / 2, self.y), line, font=f, fill=fill)
            self.y += int(size * spacing)

    def _wrap(self, text: str, f, width: int) -> list[str]:
        lines, cur = [], ""
        for word in text.split():
            trial = f"{cur} {word}".strip()
            if self.d.textlength(trial, font=f) <= width or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        return lines + ([cur] if cur else [])

    def pill(self, label: str, fill, text_fill) -> None:
        f = font(34, True)
        label = label.upper()
        tw = self.d.textlength(label, font=f) + sum(1 for _ in label) * 3
        x0, x1 = (W - tw) / 2 - 34, (W + tw) / 2 + 34
        self.d.rounded_rectangle((x0, self.y, x1, self.y + 70), radius=35, fill=fill)
        x = x0 + 34
        for ch in label:
            self.d.text((x, self.y + 14), ch, font=f, fill=text_fill)
            x += self.d.textlength(ch, font=f) + 3
        self.y += 70

    def paste_logo(self, size: int, accent) -> None:
        mark = logo_mark(size, accent)
        self.img.alpha_composite(mark, ((W - size) // 2, self.y))
        self.y += size

    def bbox(self):
        return self.img.getbbox() or (0, 0, W, 1)


def logo_mark(size: int, accent) -> Image.Image:
    """The T-monogram badge, drawn with Pillow (hexagon, white T, amber dot)."""
    s = size * 4
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = cy = s / 2
    r = s * 0.48
    import math
    pts = [(cx + r * math.cos(math.radians(60 * i - 90)), cy + r * math.sin(math.radians(60 * i - 90))) for i in range(6)]
    d.polygon(pts, fill=(15, 23, 42, 255), outline=(*accent, 255), width=int(s * 0.035))
    bar_w, bar_h, stem = s * 0.46, s * 0.1, s * 0.11
    top = cy - s * 0.2
    d.rounded_rectangle((cx - bar_w / 2, top, cx + bar_w / 2, top + bar_h), radius=bar_h / 3, fill="white")
    d.rounded_rectangle((cx - stem / 2, top, cx + stem / 2, cy + s * 0.22), radius=stem / 3, fill="white")
    dr = s * 0.045
    d.ellipse((cx + s * 0.2 - dr, cy + s * 0.2 - dr, cx + s * 0.2 + dr, cy + s * 0.2 + dr), fill=(251, 191, 36, 255))
    return img.resize((size, size), Image.LANCZOS)


def _background(accent) -> Image.Image:
    top, bottom = (11, 16, 32), mix((11, 16, 32), accent, 0.38)
    col = Image.new("RGB", (1, H))
    for y in range(H):
        col.putpixel((0, y), mix(top, bottom, (y / H) ** 1.4))
    bg = col.resize((W, H))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((W * 0.35, -H * 0.12, W * 1.3, H * 0.3), fill=(*accent, 70))
    from PIL import ImageFilter
    glow = glow.filter(ImageFilter.GaussianBlur(120))
    bg = bg.convert("RGBA")
    bg.alpha_composite(glow)
    return bg


def render_scene(scene: Scene, accent_hex: str, client: str) -> Image.Image:
    """Return a full 1080x1920 RGBA frame on the branded gradient background."""
    accent = hex_rgb(accent_hex)
    soft = mix(accent, (255, 255, 255), 0.55)
    white, muted = (255, 255, 255, 255), (203, 213, 225, 255)
    L, d = Layer(), scene.data

    if scene.kind == "hook":
        L.pill(f"Case study  ·  {d['client']}", (*accent, 255), white)
        L.gap(60)
        if d["big"]:
            L.text(_arrows(d["big"]), 230, (*soft, 255), True, max_lines=1, spacing=1.2, min_size=70)
            L.gap(18)
            L.text(d["label"], 62, white, True, max_lines=3)
            L.gap(54)
            L.text(d["title"], 44, muted, max_lines=4)
        else:
            L.text(d["title"], 88, white, True, max_lines=6, spacing=1.15)
    elif scene.kind == "challenge":
        L.pill("The challenge", (*accent, 255), white)
        L.gap(64)
        L.text(d["text"], 70, white, True, max_lines=8, spacing=1.28)
    elif scene.kind == "results":
        L.pill("The results", (*accent, 255), white)
        L.gap(60)
        for row in d["rows"]:
            if row["value"]:
                L.text(_arrows(row["value"]), 128, (*soft, 255), True, max_lines=1, spacing=1.25, min_size=60)
                L.text(row["label"], 46, white, max_lines=2)
            else:
                L.text(row["label"], 56, white, True, max_lines=3)
            L.gap(60)
    elif scene.kind == "quote":
        L.text("\u201C", 260, (*soft, 255), True, max_lines=1, spacing=0.7)
        L.gap(10)
        L.text(d["text"], 62, white, True, max_lines=11, spacing=1.28, min_size=40)
        L.gap(52)
        L.text(d["who"], 40, muted, max_lines=3)
    else:  # cta
        L.paste_logo(190, accent)
        L.gap(60)
        L.text("Want results like this?", 84, white, True, max_lines=3, spacing=1.15)
        L.gap(36)
        L.text(d["agency"], 58, (*soft, 255), True, max_lines=2)
        L.gap(20)
        L.text("Let\u2019s talk", 44, muted)

    x0, y0, x1, y1 = L.bbox()
    block = L.img.crop((0, y0, W, y1))
    top = max(180, int(H * 0.47 - block.height / 2))

    frame = _background(accent)
    frame.alpha_composite(block, (0, top))

    # Brand strip at the bottom of every scene (not the closing card, which already is the brand)
    if scene.kind != "cta":
        fd = ImageDraw.Draw(frame)
        f = font(34, True)
        label = client
        tw = fd.textlength(label, font=f)
        mark = logo_mark(60, accent)
        total = 60 + 20 + tw
        x = (W - total) / 2
        frame.alpha_composite(mark, (int(x), H - 230))
        fd.text((x + 80, H - 218), label, font=f, fill=(255, 255, 255, 235))
    return frame


# --------------------------------------------------------------------------- #
# Voiceover (free, edge-tts)
# --------------------------------------------------------------------------- #
def voiceover_available() -> bool:
    try:
        import edge_tts  # noqa: F401
        return True
    except ImportError:
        return False


def _synthesize(text: str, voice: str, path: Path) -> None:
    import edge_tts

    async def go():
        spoken = text.replace("->", " to ").replace("=>", " to ")
        await edge_tts.Communicate(spoken, voice, rate=os.getenv("VIDEO_VOICE_RATE", "+12%")).save(str(path))

    try:
        asyncio.run(go())
    except RuntimeError:  # an event loop is already running in this thread
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(go())
        finally:
            loop.close()


def make_voiceovers(scenes: list[Scene], workdir: Path) -> list[Path | None]:
    """One mp3 per scene; all None if voiceover isn't possible (offline, no edge-tts, ...)."""
    if not voiceover_available():
        return [None] * len(scenes)
    voice = os.getenv("VIDEO_VOICE", DEFAULT_VOICE)
    paths: list[Path | None] = []
    try:
        for i, scene in enumerate(scenes):
            p = workdir / f"voice{i}.mp3"
            _synthesize(scene.narration, voice, p)
            paths.append(p if p.exists() and p.stat().st_size > 0 else None)
    except Exception:
        return [None] * len(scenes)
    return paths if all(paths) else [None] * len(scenes)


# --------------------------------------------------------------------------- #
# Assembly
# --------------------------------------------------------------------------- #
@dataclass
class Segment:
    """One stretch of the final video: a still card (zoom + fade) or an AI clip with a caption overlay."""
    png: Path
    dur: float
    clip: Path | None = None
    audio: Path | None = None


def _segment_filters(i: int, seg: Segment, n_inputs: dict) -> tuple[list[str], str]:
    """Filter chain for segment i; returns (filter strings, output label)."""
    d, out = seg.dur, f"v{i}"
    fades = f"fade=t=in:st=0:d={FADE},fade=t=out:st={d - FADE:.2f}:d={FADE},setsar=1,format=yuv420p"
    if seg.clip:
        c, p = n_inputs[("clip", i)], n_inputs[("png", i)]
        clip_len = max(media_duration(seg.clip), 0.5)
        stretch = min(d / clip_len, 1.6)          # slow the shot a little to cover the narration
        return ([f"[{c}:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS},"
                 f"setpts=PTS*{stretch:.3f},tpad=stop_mode=clone:stop_duration={d:.2f},trim=duration={d:.2f},"
                 f"setpts=PTS-STARTPTS[c{i}]",
                 f"[c{i}][{p}:v]overlay=0:0:format=auto,{fades}[{out}]"], out)
    p = n_inputs[("png", i)]
    frames = int(d * FPS)
    return ([f"[{p}:v]scale={W * 2}:{H * 2},zoompan=z='1+0.0007*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
             f"d={frames}:s={W}x{H}:fps={FPS},{fades}[{out}]"], out)


def _assemble(segments: list[Segment], out: Path) -> None:
    args: list[str] = []
    idx: dict = {}
    k = 0
    for i, seg in enumerate(segments):
        if seg.clip:
            args += ["-i", str(seg.clip)]
            idx[("clip", i)] = k
            k += 1
        args += ["-i", str(seg.png)]
        idx[("png", i)] = k
        k += 1

    filters: list[str] = []
    for i, seg in enumerate(segments):
        f, _ = _segment_filters(i, seg, idx)
        filters += f
    n = len(segments)
    filters.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vout]")

    map_args = ["-map", "[vout]"]
    if all(s.audio for s in segments):
        for s in segments:
            args += ["-i", str(s.audio)]
        for i, s in enumerate(segments):
            filters.append(f"[{k + i}:a]aresample=44100,apad=whole_dur={s.dur:.2f}[a{i}]")
        filters.append("".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1[aout]")
        map_args += ["-map", "[aout]", "-c:a", "aac", "-b:a", "160k"]
    else:
        map_args += ["-an"]

    total = sum(s.dur for s in segments)
    run_ffmpeg([*args, "-filter_complex", ";".join(filters), *map_args, "-t", f"{total:.2f}", "-r", str(FPS),
                "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", str(out)])


def _out_path(details: ProjectDetails, out_dir: Path | None) -> Path:
    folder = Path(out_dir) if out_dir else BASE_DIR / "output"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{slugify(details.client_name)}-reel-{datetime.now():%Y%m%d-%H%M%S}.mp4"


def _durations(scenes: list[Scene], audio: list[Path | None], floor: float | None = None) -> list[float]:
    out = []
    for scene, a in zip(scenes, audio):
        base = max(floor or scene.min_seconds, len(scene.narration.split()) * 0.28 + 1.4)
        out.append(max(base, media_duration(a) + 0.35) if a else base)
    return out


def render_video(content: dict, details: ProjectDetails, accent: str, *, voice: bool = True,
                 out_dir: Path | None = None) -> Path:
    """Animated branded slides (no AI, works offline)."""
    scenes = build_scenes(content, details)
    out = _out_path(details, out_dir)
    with tempfile.TemporaryDirectory(prefix="reel-") as tmp:
        work = Path(tmp)
        audio = make_voiceovers(scenes, work) if voice else [None] * len(scenes)
        segs = []
        for i, (scene, dur, a) in enumerate(zip(scenes, _durations(scenes, audio), audio)):
            png = work / f"scene{i}.png"
            render_scene(scene, accent, details.agency_name).save(png)
            segs.append(Segment(png, dur, audio=a))
        _assemble(segs, out)
    return out


def caption_frame(text: str, accent_hex: str, agency: str) -> Image.Image:
    """Transparent overlay for an AI shot: dark gradient at the bottom, a short caption, the brand strip."""
    accent = hex_rgb(accent_hex)
    frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shade = Image.new("RGBA", (1, 900))
    for y in range(900):
        shade.putpixel((0, y), (6, 10, 24, int(215 * (y / 900) ** 1.6)))
    frame.alpha_composite(shade.resize((W, 900)), (0, H - 900))

    L = Layer()
    L.text(text, 84, (255, 255, 255, 255), True, max_lines=3, spacing=1.15, min_size=52)
    L.gap(26)
    L.d.rounded_rectangle(((W - 120) // 2, L.y, (W + 120) // 2, L.y + 10), radius=5, fill=(*accent, 255))
    L.y += 10
    x0, y0, x1, y1 = L.bbox()
    frame.alpha_composite(L.img.crop((0, y0, W, y1)), (0, H - 330 - (y1 - y0)))

    fd = ImageDraw.Draw(frame)
    f = font(34, True)
    total = 60 + 20 + fd.textlength(agency, font=f)
    x = (W - total) / 2
    frame.alpha_composite(logo_mark(60, accent), (int(x), H - 200))
    fd.text((x + 80, H - 188), agency, font=f, fill=(255, 255, 255, 235))
    return frame


def render_ai_film(ai_scenes: list, content: dict, details: ProjectDetails, accent: str, *,
                   voice: bool = True, out_dir: Path | None = None) -> Path:
    """AI-generated shots with captions and narration, then the real results card and a closing card."""
    cards = [s for s in build_scenes(content, details) if s.kind in ("results", "cta")]
    shots = [Scene("shot", {"caption": s.caption}, s.narration, 4.5) for s in ai_scenes]
    scenes = shots + cards
    out = _out_path(details, out_dir)
    with tempfile.TemporaryDirectory(prefix="reel-") as tmp:
        work = Path(tmp)
        audio = make_voiceovers(scenes, work) if voice else [None] * len(scenes)
        durations = _durations(scenes, audio)
        segs = []
        for i, (scene, dur, a) in enumerate(zip(scenes, durations, audio)):
            png = work / f"scene{i}.png"
            if scene.kind == "shot":
                caption_frame(scene.data["caption"], accent, details.agency_name).save(png)
                segs.append(Segment(png, dur, clip=ai_scenes[i].clip, audio=a))
            else:
                render_scene(scene, accent, details.agency_name).save(png)
                segs.append(Segment(png, dur, audio=a))
        _assemble(segs, out)
    return out
