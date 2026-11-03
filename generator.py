"""Core engine: turns raw client feedback into testimonials + a case study using Groq.

Flow: notes + project details -> Groq (JSON) -> validate -> clean -> fact-check
      -> (one self-correction round if needed) -> Markdown.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader

from factcheck import fact_check, normalize_text
from prompts import FACT_FIX_TEMPLATE, RETRY_TEMPLATE, SYSTEM_PROMPT, USER_TEMPLATE

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
VALID_LENGTHS = {"short", "medium", "long"}


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #
@dataclass
class ProjectDetails:
    client_name: str = "Client"
    contact_name: str = "Client contact"
    contact_role: str = ""
    industry: str = ""
    service: str = ""
    timeline: str = ""
    agency_name: str = field(default_factory=lambda: os.getenv("AGENCY_NAME", "Our team"))

    def filled(self) -> dict:
        """Return details with 'Not specified' instead of blanks (for prompts)."""
        return {k: (v.strip() if v and v.strip() else "Not specified") for k, v in asdict(self).items()}


@dataclass
class GenerationResult:
    content: dict
    markdown: str
    warnings: list[str] = field(default_factory=list)


class GenerationError(Exception):
    """A problem the user should see (missing key, API error, bad input)."""


# --------------------------------------------------------------------------- #
# Input files (optional front-matter: key: value lines between --- markers)
# --------------------------------------------------------------------------- #
def parse_input_file(path: str | Path) -> tuple[str, dict]:
    return parse_input_text(Path(path).read_text(encoding="utf-8"))


def parse_input_text(text: str) -> tuple[str, dict]:
    """Split optional front-matter (project details) from the notes."""
    text = text.replace("\r\n", "\n").lstrip("\ufeff")
    meta: dict = {}
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
    if match:
        for line in match.group(1).splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                meta[key.strip()] = value.strip()
        text = match.group(2)
    return text.strip(), meta


# --------------------------------------------------------------------------- #
# Groq API
# --------------------------------------------------------------------------- #
def groq_api_key() -> str:
    return os.getenv("GROQ_API_KEY", "").strip()


def is_configured() -> bool:
    key = groq_api_key()
    return bool(key) and "your_groq_api_key" not in key


def _call_groq(messages: list[dict]) -> str:
    """Groq exposes an OpenAI-compatible API, so the OpenAI SDK works with Groq's base URL."""
    from openai import APIConnectionError, AuthenticationError, NotFoundError, OpenAI, RateLimitError

    client = OpenAI(api_key=groq_api_key(), base_url=GROQ_BASE_URL)
    model = os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL)
    try:
        resp = client.chat.completions.create(
            model=model,
            temperature=0.4,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, *messages],
        )
    except AuthenticationError:
        raise GenerationError("Groq rejected the API key. Check GROQ_API_KEY in your .env file.")
    except NotFoundError:
        raise GenerationError(f"Groq model '{model}' was not found. Change GROQ_MODEL in .env "
                              "(see https://console.groq.com/docs/models).")
    except RateLimitError:
        raise GenerationError("Groq rate limit reached. Wait a minute and try again.")
    except APIConnectionError:
        raise GenerationError("Could not connect to Groq. Check your internet connection.")
    return resp.choices[0].message.content or ""


# --------------------------------------------------------------------------- #
# JSON parsing + structure validation
# --------------------------------------------------------------------------- #
def _extract_json(raw: str) -> dict:
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found in the response")
    return json.loads(raw[start : end + 1])


def _length_label(text: str) -> str:
    n = len(text.split())
    return "short" if n <= 20 else "medium" if n <= 45 else "long"


def validate_content(data: dict) -> dict:
    """Check structure; raise ValueError with a readable message if invalid."""
    if not isinstance(data, dict):
        raise ValueError("response is not a JSON object")

    quotes = data.get("testimonials")
    if not isinstance(quotes, list) or not 3 <= len(quotes) <= 5:
        raise ValueError("'testimonials' must be a list of 3 to 5 items")
    for q in quotes:
        if not isinstance(q, dict) or not str(q.get("text", "")).strip():
            raise ValueError("every testimonial needs non-empty 'text'")
        q["text"] = q["text"].strip().strip('"').strip()
        q["length"] = str(q.get("length", "")).lower()
        if q["length"] not in VALID_LENGTHS:
            q["length"] = _length_label(q["text"])
        q.setdefault("theme", "")

    cs = data.get("case_study")
    if not isinstance(cs, dict):
        raise ValueError("'case_study' object is missing")
    for key in ("title", "summary", "challenge"):
        if not str(cs.get(key, "")).strip():
            raise ValueError(f"case_study.{key} is missing")
    for key in ("solution", "results"):
        if isinstance(cs.get(key), str):
            cs[key] = [cs[key]]
        if not isinstance(cs.get(key), list) or not cs[key]:
            raise ValueError(f"case_study.{key} must be a non-empty list")
    cs.setdefault("key_metrics", [])
    data.setdefault("review_notes", [])

    order = {"short": 0, "medium": 1, "long": 2}
    data["testimonials"] = sorted(quotes, key=lambda q: order[q["length"]])
    return data


def finalize(content: dict, details: ProjectDetails) -> dict:
    """Plain punctuation + make sure every testimonial has a speaker."""
    content = normalize_text(content)
    for q in content["testimonials"]:
        if not str(q.get("speaker_name", "")).strip():
            q["speaker_name"] = details.contact_name
            q["speaker_role"] = details.contact_role
        q.setdefault("speaker_role", "")
    return content


def _details_text(details: ProjectDetails) -> str:
    return " ".join(str(v) for v in asdict(details).values())


# --------------------------------------------------------------------------- #
# Generation: bad JSON -> retry; fact-check problems -> one correction round
# --------------------------------------------------------------------------- #
def _generate_with_groq(notes: str, details: ProjectDetails) -> tuple[dict, list, list]:
    """Returns (content, remaining_issues, issues_fixed_by_model)."""
    messages = [{"role": "user", "content": USER_TEMPLATE.format(notes=notes, **details.filled())}]
    last_error, first_issues, best = "", [], None

    for _attempt in range(4):
        raw = _call_groq(messages)
        try:
            content = finalize(validate_content(_extract_json(raw)), details)
        except (ValueError, json.JSONDecodeError) as exc:
            last_error = str(exc)
            messages += [{"role": "assistant", "content": raw},
                         {"role": "user", "content": RETRY_TEMPLATE.format(error=last_error)}]
            continue

        issues = fact_check(content, notes, _details_text(details))
        if best is None or len(issues) < len(best[1]):
            best = (content, issues)
        if issues and not first_issues:  # first draft had problems -> ask the model to fix them
            first_issues = issues
            messages += [{"role": "assistant", "content": raw},
                         {"role": "user", "content": FACT_FIX_TEMPLATE.format(
                             issues="\n".join(f"- {i}" for i in issues))}]
            continue
        break

    if best is None:
        raise GenerationError(f"The model returned unusable output. Please try again. ({last_error})")
    content, remaining = best
    return content, remaining, [i for i in first_issues if i not in remaining]


# --------------------------------------------------------------------------- #
# Markdown rendering + saving
# --------------------------------------------------------------------------- #
_env = Environment(loader=FileSystemLoader(BASE_DIR / "templates"), trim_blocks=True, lstrip_blocks=True)


def render_markdown(content: dict, details: ProjectDetails) -> str:
    template = _env.get_template("case_study.md.j2")
    return template.render(c=content, d=details,
                           generated=datetime.now().strftime("%Y-%m-%d %H:%M")).strip() + "\n"


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "client"


def save_markdown(markdown: str, details: ProjectDetails, out_dir: str | Path | None = None) -> Path:
    out = Path(out_dir) if out_dir else BASE_DIR / "output"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{slugify(details.client_name)}-case-study-{datetime.now():%Y%m%d-%H%M%S}.md"
    path.write_text(markdown, encoding="utf-8")
    return path


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #
def generate(notes: str, details: ProjectDetails) -> GenerationResult:
    if not is_configured():
        raise GenerationError("Groq API key is missing. Add GROQ_API_KEY to the .env file and restart the app.")
    notes = (notes or "").strip()
    if len(notes) < 40:
        raise GenerationError("Please provide more feedback text (at least a few sentences).")

    content, issues, fixed = _generate_with_groq(notes, details)

    # Sign-off notes added by code, so they are never forgotten
    review = list(content.get("review_notes", []))
    for i, q in enumerate(content["testimonials"], 1):
        if q["speaker_name"].strip().lower() != (details.contact_name or "").strip().lower():
            review.append(f"Testimonial {i} is from {q['speaker_name']}"
                          f"{' (' + q['speaker_role'] + ')' if q.get('speaker_role') else ''}, "
                          f"not the main contact - confirm they approve being quoted.")
    content["review_notes"] = list(dict.fromkeys([f"FACT CHECK: {i}" for i in issues] + review))
    content["fact_check"] = {"issues": issues, "auto_fixed": fixed}

    warnings = [f"Fact check flagged {len(issues)} issue(s) - see 'Review Before Publishing'."] if issues else []
    return GenerationResult(content, render_markdown(content, details), warnings)
