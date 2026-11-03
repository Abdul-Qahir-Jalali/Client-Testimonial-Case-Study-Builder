"""Audio / video / link -> speaker-labelled transcript using ElevenLabs Speech-to-Text (Scribe).

  * Audio files are sent as they are.
  * Video files: the audio track is extracted locally first (bundled ffmpeg via imageio-ffmpeg),
    so a large video becomes a small audio upload.
  * Links (YouTube, TikTok, public Google Drive / Dropbox / direct media URLs) are passed to
    ElevenLabs, which downloads the media itself.

The output format matches the text samples, e.g.:

    Participants: Bilal (Interviewer), Hamza Qureshi (Client)

    [00:00] Bilal (Interviewer): Thanks for joining. What was the situation before?
    [00:07] Hamza Qureshi: Honestly, bookings were a mess...

so the rest of the pipeline (prompt rules + fact check) treats it exactly like a typed transcript.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

API_URL = "https://api.elevenlabs.io/v1/speech-to-text"
DEFAULT_MODEL = "scribe_v2"
AUDIO_TYPES = ["mp3", "wav", "m4a", "ogg", "flac", "aac", "opus", "wma"]
VIDEO_TYPES = ["mp4", "mov", "mkv", "avi", "webm", "wmv", "flv", "m4v", "3gp", "mpeg", "mpg"]
MEDIA_TYPES = AUDIO_TYPES + VIDEO_TYPES
REQUEST_TIMEOUT = 900  # seconds - long recordings can take a few minutes


class TranscriptionError(Exception):
    """A problem the user should see (missing key, quota, bad file...)."""


@dataclass
class Segment:
    speaker: str   # e.g. "speaker_0"
    start: float   # seconds
    text: str


@dataclass
class Transcript:
    segments: list[Segment]
    language: str = ""
    duration: float = 0.0
    speakers: list[str] = field(default_factory=list)  # in order of first appearance

    def stats(self) -> dict[str, dict]:
        """Per speaker: word count, talk share and a sample line (helps the user identify who is who)."""
        info: dict[str, dict] = {}
        for seg in self.segments:
            s = info.setdefault(seg.speaker, {"words": 0, "sample": "", "first": seg.start})
            s["words"] += len(seg.text.split())
            if len(s["sample"].split()) < 8 and len(seg.text.split()) >= 6:
                s["sample"] = seg.text
        total = sum(s["words"] for s in info.values()) or 1
        for spk, s in info.items():
            s["share"] = round(100 * s["words"] / total)
            if not s["sample"]:
                s["sample"] = next(seg.text for seg in self.segments if seg.speaker == spk)
        return info


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
def api_key() -> str:
    return os.getenv("ELEVENLABS_API_KEY", "").strip()


def is_configured() -> bool:
    key = api_key()
    return bool(key) and "your_elevenlabs_api_key" not in key


# --------------------------------------------------------------------------- #
# API call
# --------------------------------------------------------------------------- #
def _error_message(resp: requests.Response) -> str:
    try:
        detail = resp.json().get("detail", "")
    except ValueError:
        detail = resp.text
    if isinstance(detail, dict):
        status, msg = str(detail.get("status", "")), str(detail.get("message", ""))
    else:
        status, msg = "", str(detail)
    low = f"{status} {msg}".lower()

    if "quota" in low or "credits" in low or resp.status_code == 402:
        return "Your ElevenLabs free credits for this month are used up (or too low for this file)."
    if resp.status_code in (401, 403):
        return "ElevenLabs rejected the API key. Check ELEVENLABS_API_KEY in your .env file."
    if resp.status_code == 429:
        return "ElevenLabs is busy or the rate limit was reached. Wait a minute and try again."
    if resp.status_code in (400, 422):
        return f"ElevenLabs could not process this file: {msg or 'unsupported or corrupted audio'}"
    return f"ElevenLabs error {resp.status_code}: {msg or resp.reason}"


def is_video(filename: str) -> bool:
    return Path(filename).suffix.lower().lstrip(".") in VIDEO_TYPES


# --------------------------------------------------------------------------- #
# Video -> audio (local, bundled ffmpeg)
# --------------------------------------------------------------------------- #
def _ffmpeg() -> str | None:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # package missing or no binary for this platform
        return None


def extract_audio(data: bytes, filename: str) -> bytes:
    """Return the video's audio track as a compact mono MP3 (speech quality)."""
    exe = _ffmpeg()
    if not exe:
        raise TranscriptionError("Video conversion is unavailable (imageio-ffmpeg is not installed). "
                                 "Run: python -m pip install -r requirements.txt")
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / ("input" + (Path(filename).suffix or ".mp4"))
        dst = Path(tmp) / "audio.mp3"
        src.write_bytes(data)
        proc = subprocess.run(
            [exe, "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
             "-vn", "-ac", "1", "-ar", "22050", "-b:a", "64k", str(dst)],
            capture_output=True, text=True,
        )
        if proc.returncode != 0 or not dst.exists() or dst.stat().st_size == 0:
            err = (proc.stderr or "").lower()
            if "does not contain any stream" in err or "matches no streams" in err or "no audio" in err:
                raise TranscriptionError("This video has no audio track.")
            raise TranscriptionError("Could not extract audio from this video. The file may be corrupted "
                                     "or in an unsupported format.")
        return dst.read_bytes()


# --------------------------------------------------------------------------- #
# Links
# --------------------------------------------------------------------------- #
def normalize_link(url: str) -> str:
    """Validate a media link and turn common share links into direct-download links."""
    url = (url or "").strip()
    if url and "://" not in url and re.match(r"^(www\.)?[\w-]+(\.[\w-]+)+(/|$)", url):
        url = "https://" + url  # "youtube.com/watch?v=..." -> "https://youtube.com/watch?v=..."
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise TranscriptionError("Please paste a full link starting with http:// or https://")
    host = parsed.netloc.lower()

    # Google Drive: /file/d/<id>/view  or  open?id=<id>  ->  direct download
    if "drive.google.com" in host:
        m = re.search(r"/file/d/([\w-]+)", parsed.path)
        file_id = m.group(1) if m else parse_qs(parsed.query).get("id", [None])[0]
        if file_id:
            return f"https://drive.google.com/uc?export=download&id={file_id}"
    # Dropbox: ?dl=0 -> ?dl=1
    if "dropbox.com" in host:
        return re.sub(r"([?&])dl=0", r"\1dl=1", url) if "dl=0" in url else url + ("&" if "?" in url else "?") + "dl=1"
    return url


def _base_form(num_speakers: int | None) -> dict:
    form = {
        "model_id": os.getenv("ELEVENLABS_STT_MODEL", DEFAULT_MODEL),
        "diarize": "true",                  # label who is speaking
        "timestamps_granularity": "word",
        "tag_audio_events": "false",        # no "(laughter)" tags in quotes
    }
    if num_speakers:
        form["num_speakers"] = str(num_speakers)
    return form


def _require_key() -> None:
    if not is_configured():
        raise TranscriptionError("ElevenLabs API key is missing. Add ELEVENLABS_API_KEY to the .env file "
                                 "and restart the app.")


def _post(form: dict, files: dict | None = None, link: bool = False) -> Transcript:
    try:
        resp = requests.post(API_URL, headers={"xi-api-key": api_key()}, data=form, files=files,
                             timeout=REQUEST_TIMEOUT)
    except requests.Timeout:
        raise TranscriptionError("Transcription timed out. Try a shorter recording.")
    except requests.ConnectionError:
        raise TranscriptionError("Could not connect to ElevenLabs. Check your internet connection.")
    if resp.status_code != 200:
        msg = _error_message(resp)
        if link and resp.status_code in (400, 422):
            msg = ("ElevenLabs could not fetch media from this link. Make sure the video is public "
                   "(not private or login-only) and the link opens the video directly. "
                   "If it still fails, download the file and upload it instead.")
        raise TranscriptionError(msg)
    return parse_response(resp.json())


def transcribe_audio(data: bytes, filename: str, num_speakers: int | None = None) -> Transcript:
    """Transcribe an uploaded audio OR video file (video -> audio is extracted locally first)."""
    _require_key()
    if not data:
        raise TranscriptionError("The file is empty.")
    if is_video(filename):
        data, filename = extract_audio(data, filename), Path(filename).stem + ".mp3"
    return _post(_base_form(num_speakers), files={"file": (filename, data)})


def transcribe_url(url: str, num_speakers: int | None = None) -> Transcript:
    """Transcribe media from a link (YouTube, TikTok, Google Drive, Dropbox, direct file URL)."""
    _require_key()
    form = _base_form(num_speakers)
    form["source_url"] = normalize_link(url)
    return _post(form, link=True)


# --------------------------------------------------------------------------- #
# Response -> speaker segments
# --------------------------------------------------------------------------- #
def parse_response(payload: dict) -> Transcript:
    """Group word-level results into consecutive same-speaker segments."""
    words = payload.get("words") or []
    segments: list[Segment] = []
    current: Segment | None = None
    duration = 0.0

    for w in words:
        kind = w.get("type", "word")
        text = w.get("text", "")
        if kind == "audio_event":
            continue
        duration = max(duration, float(w.get("end") or 0))
        speaker = w.get("speaker_id") or "speaker_0"

        if kind == "spacing":  # whitespace between words - attach to the current segment
            if current:
                current.text += text
            continue
        if current is None or speaker != current.speaker:
            current = Segment(speaker=speaker, start=float(w.get("start") or 0), text="")
            segments.append(current)
        current.text += text

    for seg in segments:
        seg.text = " ".join(seg.text.split())
    segments = [s for s in segments if s.text]

    # Fallback: no word data -> one block of text
    if not segments and payload.get("text", "").strip():
        segments = [Segment("speaker_0", 0.0, " ".join(payload["text"].split()))]
    if not segments:
        raise TranscriptionError("No speech was detected in this audio file.")

    speakers = list(dict.fromkeys(s.speaker for s in segments))
    return Transcript(segments, payload.get("language_code", ""), duration, speakers)


# --------------------------------------------------------------------------- #
# Transcript -> text in the same format as the samples
# --------------------------------------------------------------------------- #
def default_label(index: int) -> str:
    return f"Speaker {chr(ord('A') + index)}" if index < 26 else f"Speaker {index + 1}"


def _timestamp(seconds: float) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"[{h}:{m:02d}:{s:02d}]" if h else f"[{m:02d}:{s:02d}]"


def _clean_name(name: str, fallback: str) -> str:
    name = " ".join((name or "").replace(":", " ").split())
    if not name:
        return fallback
    return name[0].upper() + name[1:]  # speaker lines must start with a capital letter


def format_transcript(transcript: Transcript, names: dict[str, str], interviewers: set[str]) -> str:
    """names: speaker_id -> display name. interviewers: speaker_ids that are on our (agency) side."""
    labels = {}
    for i, spk in enumerate(transcript.speakers):
        name = _clean_name(names.get(spk, ""), default_label(i))
        labels[spk] = f"{name} (Interviewer)" if spk in interviewers else name

    participants = ", ".join(
        f"{labels[s]}" if s in interviewers else f"{labels[s]} (Client)" for s in transcript.speakers
    )
    lines = [f"Participants: {participants}", ""]
    lines += [f"{_timestamp(seg.start)} {labels[seg.speaker]}: {seg.text}" for seg in transcript.segments]
    return "\n".join(lines)
