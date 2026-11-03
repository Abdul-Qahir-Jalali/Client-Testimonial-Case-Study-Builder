"""Social posts: platform-tailored captions and hashtags for the finished video.

One Groq call writes all five posts from the fact-checked case study. Every number in the result is then
checked against the case study (one correction round, anything left is shown to the user), and a
template fallback means the Share tab works even without a key.

The platforms do not let an app post for you without an approved developer app, so each platform here
carries the URL of its upload page; share_view.py copies the caption and opens that page in one click.
"""

from __future__ import annotations

import json
import os
import re
import urllib.parse
from dataclasses import dataclass, field

from generator import DEFAULT_GROQ_MODEL, GROQ_BASE_URL, ProjectDetails, groq_api_key
from generator import is_configured as groq_ready


@dataclass(frozen=True)
class Platform:
    key: str
    name: str
    icon: str            # Lucide icon name (see icons.py)
    spec: str            # one line shown under the name
    limit: int           # hard character limit of the caption field
    max_tags: int
    upload_url: str      # where the button sends the user
    open_label: str
    tips: str


PLATFORMS = [
    Platform("linkedin", "LinkedIn", "linkedin", "Professional post, up to 3,000 characters", 3000, 5,
             "https://www.linkedin.com/feed/?shareActive=true&text={text}", "Open LinkedIn",
             "Best on weekday mornings. Native video gets more reach than a link. Add the video in the post box."),
    Platform("tiktok", "TikTok", "tiktok", "Short hook, up to 2,200 characters", 2200, 5,
             "https://www.tiktok.com/tiktokstudio/upload", "Open TikTok upload",
             "The first line is the hook. Keep it under 150 characters so it is not cut off in the feed."),
    Platform("instagram", "Instagram", "instagram", "Reels caption, up to 2,200 characters", 2200, 12,
             "https://www.instagram.com/", "Open Instagram",
             "Click the + button and choose Reel. Only the first line shows before 'more', so lead with the hook."),
    Platform("facebook", "Facebook", "facebook", "Friendly post, up to 63,000 characters", 63000, 3,
             "https://www.facebook.com/reels/create", "Open Facebook Reels",
             "Short, conversational captions do best. One or two hashtags is plenty."),
    Platform("youtube", "YouTube Shorts", "youtube", "Title up to 100 characters, description up to 5,000", 5000, 5,
             "https://www.youtube.com/upload", "Open YouTube upload",
             "Videos up to 3 minutes in a vertical format are published as Shorts. Keep #Shorts in the description."),
]
BY_KEY = {p.key: p for p in PLATFORMS}
TITLE_LIMIT = 100
TONES = ["Professional", "Friendly", "Bold"]


@dataclass
class Post:
    caption: str
    hashtags: list[str] = field(default_factory=list)
    title: str = ""                       # YouTube only


# --------------------------------------------------------------------------- #
# Hashtags and text helpers
# --------------------------------------------------------------------------- #
def clean_hashtags(tags, limit: int) -> list[str]:
    seen, out = set(), []
    if isinstance(tags, str):
        tags = re.findall(r"#?\w+", tags)
    for tag in tags or []:
        word = re.sub(r"[^\w]", "", str(tag), flags=re.UNICODE)
        if not word or word.isdigit() or len(word) > 30 or word.lower() in seen:
            continue
        seen.add(word.lower())
        out.append("#" + word)
    return out[:limit]


def compose(post: Post, caption: str | None = None, hashtags: str | None = None) -> str:
    """The text that is copied: caption, blank line, hashtags."""
    body = (post.caption if caption is None else caption).strip()
    tags = " ".join(post.hashtags) if hashtags is None else hashtags.strip()
    return f"{body}\n\n{tags}".strip() if tags else body


def open_url(platform: Platform, text: str) -> str:
    return platform.upload_url.format(text=urllib.parse.quote(text, safe="")) if "{text}" in platform.upload_url \
        else platform.upload_url


_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _numbers(text: str) -> set[str]:
    return {m.group().replace(",", "").rstrip(".") for m in _NUM.finditer(text)}


def unsupported_numbers(text: str, content: dict, details: ProjectDetails, extra: str = "") -> list[str]:
    """Numbers in `text` that appear nowhere in the case study (nothing may be invented)."""
    source = json.dumps(content, ensure_ascii=False) + " " + " ".join(
        [details.timeline, details.client_name, details.service, details.industry, extra])
    return sorted(_numbers(text) - _numbers(source))


# --------------------------------------------------------------------------- #
# Writing the posts
# --------------------------------------------------------------------------- #
def _best_quote(content: dict) -> dict | None:
    quotes = content.get("testimonials") or []
    pool = [q for q in quotes if len(q["text"].split()) <= 30] or quotes
    return min(pool, key=lambda q: abs(len(q["text"].split()) - 18)) if pool else None


def _brief(content: dict, details: ProjectDetails) -> str:
    cs = content["case_study"]
    quote = _best_quote(content)
    metrics = "; ".join(f"{m['label']}: {m['value']}" for m in cs.get("key_metrics", []) if m.get("value"))
    return "\n".join([
        f"Client: {details.client_name} ({details.industry or 'n/a'}). Service delivered: {details.service or 'n/a'}. "
        f"Timeline: {details.timeline or 'n/a'}. Posted by: {details.agency_name}.",
        f"Case study title: {cs['title']}",
        f"Summary: {cs['summary']}",
        f"Challenge: {cs['challenge']}",
        f"Solution: {' '.join(cs['solution'][:4])}",
        f"Results: {' '.join(cs['results'][:4])}",
        f"Key metrics (exact wording): {metrics or 'none'}",
        f"Client quote (verbatim): \"{quote['text']}\" - {quote['speaker_name']}" if quote else "No quote.",
    ])


PROMPT = """You are a senior social media copywriter for a B2B agency. Write one post per platform to go with a short \
vertical video that tells this client's success story.

STRICT FACT RULES (the post is shown to the client and the public):
- Use ONLY facts from the brief. Never invent statistics, names, awards, quotes or claims.
- Write every number exactly as in the brief ("from X to Y"). Do not calculate or round anything. If unsure, leave the number out.
- A client quote may only appear word for word, with its speaker.

CRAFT RULES:
- Tone: {tone}. Emojis: {emoji}. Write like a person, not an ad. No clickbait, no ALL CAPS, no filler like "game-changer".
- First line is the hook: a concrete result or problem, not the client's name.
- {cta}
- LinkedIn: 600-1,200 characters, short paragraphs separated by blank lines, a clear takeaway, 3-5 hashtags.
- TikTok: caption under 150 characters before hashtags, 4-6 hashtags mixing broad and niche.
- Instagram: hook line, 2-4 short lines, call to action, 8-12 hashtags mixing broad and niche.
- Facebook: conversational, 250-500 characters, 2-3 hashtags.
- YouTube: "title" under 70 characters with the main result and a keyword; "caption" is the description (2-4 short paragraphs, a call to action, keywords naturally); 3-5 hashtags including #Shorts.
- Hashtags: relevant to the industry, service and result; no spaces; do not use banned or spammy tags; the "hashtags" lists do not repeat inside the caption text.

Return JSON only:
{{"linkedin":{{"caption":"","hashtags":[]}},"tiktok":{{"caption":"","hashtags":[]}},"instagram":{{"caption":"","hashtags":[]}},\
"facebook":{{"caption":"","hashtags":[]}},"youtube":{{"title":"","caption":"","hashtags":[]}}}}

BRIEF
{brief}"""


def _call_groq(prompt: str) -> dict:
    from openai import OpenAI
    client = OpenAI(api_key=groq_api_key(), base_url=GROQ_BASE_URL)
    resp = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL), temperature=0.7,
        response_format={"type": "json_object"}, messages=[{"role": "user", "content": prompt}])
    return json.loads(resp.choices[0].message.content or "{}")


def _parse(data: dict) -> dict[str, Post]:
    posts = {}
    for p in PLATFORMS:
        item = data[p.key]
        caption = str(item["caption"]).replace("‑", "-").replace(" ", " ").strip()
        if not caption:
            raise ValueError(f"empty caption for {p.key}")
        title = str(item.get("title", "")).strip()[:TITLE_LIMIT] if p.key == "youtube" else ""
        posts[p.key] = Post(caption, clean_hashtags(item.get("hashtags"), p.max_tags), title)
    return posts


def _fallback(content: dict, details: ProjectDetails, link: str, tone: str) -> dict[str, Post]:
    """Deterministic posts built straight from the case study, used when the AI is unavailable."""
    cs = content["case_study"]
    metrics = [m for m in cs.get("key_metrics", []) if m.get("value")]
    hook = f"{metrics[0]['label']}: {metrics[0]['value']}." if metrics else cs["title"]
    first = lambda items: (items or [""])[0]
    quote = _best_quote(content)
    q = f"\n\n“{quote['text']}” – {quote['speaker_name']}" if quote else ""
    cta = f"\n\nRead the full story: {link}" if link else f"\n\nWant results like this? Talk to {details.agency_name}."
    body = (f"{hook}\n\n{cs['summary']}\n\nThe challenge: {cs['challenge']}\n\nWhat we did: {first(cs['solution'])}"
            f"\n\nThe result: {first(cs['results'])}{q}{cta}")
    industry = re.sub(r"[^A-Za-z0-9]", "", (details.industry or "business").title())
    service = re.sub(r"[^A-Za-z0-9]", "", (details.service or "").title())
    tags = ["CaseStudy", "ClientSuccess", industry, service, "Results", "Testimonial"]
    short = f"{hook} {cs['title']}"[:140].rsplit(" ", 1)[0]
    return {
        "linkedin": Post(body, clean_hashtags(tags, 5)),
        "tiktok": Post(short, clean_hashtags(tags + ["fyp"], 5)),
        "instagram": Post(f"{hook}\n\n{first(cs['results'])}\n\nSave this for later.{cta}", clean_hashtags(tags + ["SmallBusiness", "Marketing"], 10)),
        "facebook": Post(f"{hook} {first(cs['results'])}{cta}", clean_hashtags(tags, 3)),
        "youtube": Post(f"{cs['summary']}\n\nThe challenge: {cs['challenge']}\n\nThe result: {first(cs['results'])}{cta}",
                        clean_hashtags(tags + ["Shorts"], 5), cs["title"][:TITLE_LIMIT]),
    }


def write_posts(content: dict, details: ProjectDetails, *, tone: str = "Professional", emojis: bool = True,
                link: str = "") -> tuple[dict[str, Post], list[str], bool]:
    """Returns (posts, warnings, used_ai). Warnings list numbers that could not be matched to the case study."""
    link = link.strip()
    if not groq_ready():
        return _fallback(content, details, link, tone), [], False
    cta = (f"End with a call to action that points to this link exactly as written: {link}" if link
           else f"End with a soft call to action to talk to {details.agency_name}. Do not invent any link.")
    prompt = PROMPT.format(tone=tone, emoji="a few, tasteful" if emojis else "none", cta=cta, brief=_brief(content, details))
    try:
        posts = _parse(_call_groq(prompt))
        issues = _issues(posts, content, details, link)
        if issues:   # one correction round, like the main generator
            retry = prompt + ("\n\nYour previous draft used numbers that are not in the brief: "
                              + ", ".join(sorted({n for v in issues.values() for n in v}))
                              + ". Rewrite all posts without them.")
            try:
                posts = _parse(_call_groq(retry))
                issues = _issues(posts, content, details, link)
            except Exception:
                pass
        warnings = [f"{BY_KEY[k].name}: check the number(s) {', '.join(v)} - not found in the case study."
                    for k, v in issues.items()]
        return posts, warnings, True
    except Exception:
        return _fallback(content, details, link, tone), [], False


def _issues(posts: dict[str, Post], content: dict, details: ProjectDetails, link: str) -> dict[str, list[str]]:
    out = {}
    for key, post in posts.items():
        bad = unsupported_numbers(f"{post.title} {post.caption}", content, details, extra=link)
        if bad:
            out[key] = bad
    return out
