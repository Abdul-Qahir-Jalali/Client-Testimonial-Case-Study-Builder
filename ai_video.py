"""Prompt-to-video with free AI models - a short cinematic film of the client's story.

Pipeline (all free, no API key required):
  1. Groq writes a 3-scene storyboard from the case study (visual prompt, on-screen caption, narration).
  2. Each scene's first frame is generated from its prompt (FLUX through the free Pollinations service).
  3. Wan 2.2 (open-source, public Hugging Face Space) animates that frame into a ~5 second cinematic shot.
     If Wan is unavailable, LTX-Video text-to-video is used for that shot instead.
video_maker.py then adds captions, voiceover and a results card with the real, fact-checked numbers.

An optional free Hugging Face token (HF_TOKEN in .env) raises the daily GPU quota of the shared Spaces.
"""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import tempfile
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import requests
from PIL import Image

from generator import DEFAULT_GROQ_MODEL, GROQ_BASE_URL, ProjectDetails, groq_api_key
from generator import is_configured as groq_ready

WAN_SPACE = "https://zerogpu-aoti-wan2-2-fp8da-aoti-faster.hf.space"
LTX_SPACE = "https://lightricks-ltx-video-distilled.hf.space"
IMAGE_API = "https://image.pollinations.ai/prompt/"
NEGATIVE = "blurry, distorted, deformed, warped, text, letters, watermark, logo, subtitles, static, low quality, jpeg artifacts"
N_SCENES = 3
SCENE_SECONDS = 5.0


class AIVideoError(Exception):
    """A problem the user should see (quota, service down, bad response)."""


@dataclass
class AIScene:
    visual: str
    caption: str
    narration: str
    clip: Path | None = None


def hf_token() -> str:
    return os.getenv("HF_TOKEN", "").strip()


def _headers(url: str = "") -> dict:
    """Auth header for Hugging Face hosts only; a URL returned by a Space is never trusted with the token."""
    host = urllib.parse.urlparse(url).hostname or "" if url else "huggingface.co"
    trusted = host == "huggingface.co" or host.endswith((".hf.space", ".huggingface.co"))
    return {"Authorization": f"Bearer {hf_token()}"} if hf_token() and trusted else {}


# --------------------------------------------------------------------------- #
# 1. Storyboard
# --------------------------------------------------------------------------- #
def _fallback_storyboard(content: dict, details: ProjectDetails) -> list[AIScene]:
    cs = content["case_study"]
    industry = details.industry or "modern business"
    style = "cinematic, shallow depth of field, soft natural light, 35mm film look, vertical composition"
    shorten = lambda t, n=70: (" ".join(str(t).split())[:n].rsplit(" ", 1)[0] if len(str(t)) > n else str(t))
    return [
        AIScene(f"a stressed small team in a {industry} workplace facing a growing pile of work, {style}",
                "It started with a problem", shorten(cs["challenge"], 140)),
        AIScene(f"a focused team collaborating around a laptop, ideas coming together, warm light, {style}",
                "Then everything changed", shorten((cs["solution"] or [""])[0], 140)),
        AIScene(f"a happy confident founder smiling in a bright {industry} space, success and relief, {style}",
                "The results speak", shorten((cs["results"] or [""])[0], 140)),
    ]


def storyboard(content: dict, details: ProjectDetails) -> list[AIScene]:
    """Ask Groq for a 3-scene visual storyboard; fall back to a template if that fails."""
    fallback = _fallback_storyboard(content, details)
    if not groq_ready():
        return fallback
    cs = content["case_study"]
    brief = (f"Client: {details.client_name} ({details.industry or 'business'}). Service: {details.service or 'n/a'}.\n"
             f"Challenge: {cs['challenge']}\nSolution: {' '.join(cs['solution'][:3])}\n"
             f"Results: {' '.join(cs['results'][:3])}")
    try:
        from openai import OpenAI
        client = OpenAI(api_key=groq_api_key(), base_url=GROQ_BASE_URL)
        resp = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL), temperature=0.7,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content":
                       f"Storyboard a {N_SCENES}-shot vertical social video telling this client story as a cinematic film: "
                       "1) the struggle before, 2) the turning point, 3) the success after.\n"
                       "For each shot give: 'visual' = one vivid sentence (max 40 words) for an AI image/video model "
                       "(subject, setting, lighting, camera, mood; realistic; NO text, signs, logos, brand names, "
                       "screens with readable words, or close-up faces), 'caption' = on-screen line, max 6 words, "
                       "'narration' = one spoken sentence, max 18 words, with NO numbers or statistics that are not in the brief.\n"
                       f'Return JSON: {{"scenes":[{{"visual":"","caption":"","narration":""}}]}}\n\n{brief}'}])
        data = json.loads(resp.choices[0].message.content or "{}")
        scenes = [AIScene(str(s["visual"]).strip(), str(s["caption"]).strip(), str(s["narration"]).strip())
                  for s in data["scenes"][:N_SCENES] if all(str(s.get(k, "")).strip() for k in ("visual", "caption", "narration"))]
        return scenes if len(scenes) == N_SCENES else fallback
    except Exception:
        return fallback


# --------------------------------------------------------------------------- #
# 2. First frame (text -> image)
# --------------------------------------------------------------------------- #
def generate_image(prompt: str, seed: int) -> Image.Image:
    """Portrait 9:16 still. The free service stamps a small logo at the bottom, so we crop it off."""
    url = (IMAGE_API + urllib.parse.quote(prompt + ", photorealistic, cinematic lighting")
           + f"?width=720&height=1280&model=flux&nologo=true&seed={seed}")
    try:
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content)).convert("RGB")
    except Exception as exc:
        raise AIVideoError(f"The free image service did not respond ({type(exc).__name__}). Try again in a moment.")
    w, h = img.size
    img = img.crop((0, 0, w, int(h * 0.93)))               # drop the watermark strip
    target_w = int(img.height * 9 / 16)
    left = max(0, (img.width - target_w) // 2)
    return img.crop((left, 0, left + min(target_w, img.width), img.height))


# --------------------------------------------------------------------------- #
# 3. Animation (image -> video) through public Gradio Spaces
# --------------------------------------------------------------------------- #
def _explain(payload: str) -> str:
    low = payload.lower().strip('" ')
    if low in ("", "null", "none") or "quota" in low or "zerogpu" in low or "gpu" in low:   # Spaces send a bare "null" on quota errors
        return ("The free GPU quota for today is used up. Add a free Hugging Face token as HF_TOKEN in .env "
                "for a bigger quota, or try again later.")
    msg = re.sub(r"\s+", " ", payload).strip('" ')
    return f"The AI video service reported an error: {msg[:160] or 'unknown'}"


def _upload(base: str, name: str, data: bytes) -> dict:
    r = requests.post(f"{base}/gradio_api/upload", files=[("files", (name, data, "image/jpeg"))],
                      headers=_headers(base), timeout=60)
    r.raise_for_status()
    return {"path": r.json()[0], "meta": {"_type": "gradio.FileData"}}


def _call(base: str, endpoint: str, data: list, timeout: int = 420) -> Path:
    """Run a Gradio endpoint over HTTP and return the generated video as a local file."""
    try:
        r = requests.post(f"{base}/gradio_api/call/{endpoint}", json={"data": data}, headers=_headers(base), timeout=30)
        r.raise_for_status()
        event_id = r.json()["event_id"]
        result, event = None, ""
        with requests.get(f"{base}/gradio_api/call/{endpoint}/{event_id}", headers=_headers(base),
                          stream=True, timeout=timeout) as stream:
            for raw in stream.iter_lines(decode_unicode=True):
                if raw.startswith("event:"):
                    event = raw.split(":", 1)[1].strip()
                elif raw.startswith("data:"):
                    payload = raw.split(":", 1)[1].strip()
                    if event == "complete":
                        result = json.loads(payload)
                        break
                    if event == "error":
                        raise AIVideoError(_explain(payload))
        if not result:
            raise AIVideoError("The AI video service ended without returning a video.")
        url = _file_url(result, base)
        if not url:
            raise AIVideoError("The AI video service returned an unexpected response.")
        video = requests.get(url, headers=_headers(url), timeout=120)
        video.raise_for_status()
    except AIVideoError:
        raise
    except requests.Timeout:
        raise AIVideoError("The free AI video service took too long (it queues when busy).")
    except (requests.RequestException, KeyError, ValueError) as exc:
        raise AIVideoError(f"Could not reach the free AI video service ({type(exc).__name__}).")
    path = Path(tempfile.mkdtemp(prefix="aiclip-")) / "clip.mp4"
    path.write_bytes(video.content)
    return path


def _file_url(value, base: str) -> str | None:
    if isinstance(value, dict):
        for key in ("url", "path"):
            v = value.get(key)
            if isinstance(v, str) and v:
                return v if v.startswith("http") else f"{base}/gradio_api/file={v}"
        return _file_url(value.get("video"), base)
    if isinstance(value, list) and value:
        return _file_url(value[0], base)
    return None


def animate_wan(image: Image.Image, motion_prompt: str) -> Path:
    buf = io.BytesIO()
    image.save(buf, "JPEG", quality=92)
    frame = _upload(WAN_SPACE, "frame.jpg", buf.getvalue())
    prompt = f"{motion_prompt}. Smooth cinematic camera movement, natural lifelike motion, high quality"
    return _call(WAN_SPACE, "generate_video", [frame, prompt, 6, NEGATIVE, SCENE_SECONDS, 1, 1, 42, True])


def animate_ltx(prompt: str) -> Path:
    data = [prompt, NEGATIVE, None, None, 704, 384, "text-to-video", SCENE_SECONDS, 9, 42, True, 1, True]
    return _call(LTX_SPACE, "text_to_video", data)


def generate_scene_clip(scene: AIScene, seed: int) -> Path:
    """One shot: prompt -> still frame -> animated clip (Wan 2.2), LTX text-to-video as fallback."""
    try:
        return animate_wan(generate_image(scene.visual, seed), scene.visual)
    except AIVideoError as first:
        try:
            return animate_ltx(scene.visual)
        except AIVideoError:
            raise first


def _scrub(text: str, details: ProjectDetails) -> str:
    """Replace the client, contact and agency names so confidential details never leave the machine in a prompt."""
    for name, generic in ((details.client_name, "a small business"), (details.contact_name, "the founder"),
                          (details.agency_name, "an agency")):
        name = (name or "").strip()
        if len(name) > 2:
            text = re.sub(re.escape(name), generic, text, flags=re.IGNORECASE)
    return text


def cleanup(scenes: list[AIScene]) -> None:
    """Delete the downloaded shot files once the video has been rendered."""
    for scene in scenes:
        if scene.clip:
            shutil.rmtree(scene.clip.parent, ignore_errors=True)
            scene.clip = None


def generate_film(content: dict, details: ProjectDetails,
                  progress: Callable[[float, str], None] | None = None) -> list[AIScene]:
    """Storyboard + all shots. Raises AIVideoError only if no shot could be made."""
    note = progress or (lambda f, m: None)
    note(0.02, "Writing the storyboard...")
    scenes = storyboard(content, details)
    for scene in scenes:      # prompts go to public third-party services: never send names
        scene.visual = _scrub(scene.visual, details)
    made: list[AIScene] = []
    last_error: AIVideoError | None = None
    for i, scene in enumerate(scenes):
        note(0.05 + 0.9 * i / len(scenes), f"Generating shot {i + 1} of {len(scenes)} (about a minute each)...")
        try:
            scene.clip = generate_scene_clip(scene, seed=7 + i * 11)
            made.append(scene)
        except AIVideoError as exc:
            last_error = exc
            if not made:          # first shot failed: the service is down or out of quota, stop early
                break
    if not made:
        raise last_error or AIVideoError("No AI shot could be generated.")
    note(1.0, "Assembling the video...")
    return made
