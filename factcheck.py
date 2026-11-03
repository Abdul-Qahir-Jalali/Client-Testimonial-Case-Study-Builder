"""Code-level safety checks on generated content.

LLMs sometimes break prompt rules (inventing numbers, mixing timeframes, mis-attributing quotes).
These checks compare the output against the raw notes and report anything suspicious, so a
human never publishes an unverified claim.

Checks:
  1. Unknown numbers       - every number in the output must appear in the notes / project details
  2. Percentage points     - "cut by 25%" when the notes say "from 40% to 15%" (misleading)
  3. Timeframe mismatch    - "25% in five months" when the notes say "25% in the first three months"
  4. Speaker attribution   - quote credited to one person but worded like another speaker's lines
  5. Repeated statistics   - same number used in several testimonials
"""

from __future__ import annotations

import re

# --------------------------------------------------------------------------- #
# Text normalisation (special punctuation -> plain ASCII)
# --------------------------------------------------------------------------- #
_CHAR_MAP = {
    "‐": "-", "‑": "-", "‒": "-", "–": "-", "−": "-",
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "“": '"', "”": '"', "„": '"',
    " ": " ", " ": " ", " ": " ", " ": " ",
    "≈": "~", "…": "...",
}
_TRANS = str.maketrans(_CHAR_MAP)


def normalize_text(obj):
    """Recursively replace special punctuation in strings inside dicts/lists."""
    if isinstance(obj, str):
        return re.sub(r"[ ]{2,}", " ", obj.translate(_TRANS)).strip()
    if isinstance(obj, list):
        return [normalize_text(x) for x in obj]
    if isinstance(obj, dict):
        return {k: normalize_text(v) for k, v in obj.items()}
    return obj


# --------------------------------------------------------------------------- #
# Number helpers
# --------------------------------------------------------------------------- #
WORD_NUMBERS = {
    "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90, "hundred": 100, "double": 2, "doubled": 2, "twice": 2,
    "triple": 3, "tripled": 3, "half": 50,
}
IGNORE_NUMBERS = {0.0, 1.0}  # too common in normal prose ("one place", "zero")
TIMESTAMP = re.compile(r"\[?\b\d{1,2}:\d{2}(?::\d{2})?\b\]?")
NUM_RE = re.compile(r"(?<![\w.])\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?")
WORD_RE = re.compile(r"\b(" + "|".join(WORD_NUMBERS) + r")\b", re.IGNORECASE)
APPROX = r"(?:about |around |roughly |approximately |nearly |almost |over |under |~)?"


def numbers_in(text: str) -> set[float]:
    text = TIMESTAMP.sub(" ", text)
    found = {float(m.replace(",", "")) for m in NUM_RE.findall(text)}
    found |= {float(WORD_NUMBERS[w.lower()]) for w in WORD_RE.findall(text)}
    return found


def _fmt(n: float) -> str:
    return f"{n:,.0f}" if n == int(n) else str(n)


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


# --------------------------------------------------------------------------- #
# Collect every text field of the output with a readable location label
# --------------------------------------------------------------------------- #
def _fields(content: dict) -> list[tuple[str, str]]:
    out = []
    for i, q in enumerate(content.get("testimonials", []), 1):
        out.append((f"Testimonial {i}", q.get("text", "")))
    cs = content.get("case_study", {})
    out.append(("Case study title", cs.get("title", "")))
    out.append(("Case study summary", cs.get("summary", "")))
    out.append(("Challenge", cs.get("challenge", "")))
    out += [("Solution", s) for s in cs.get("solution", [])]
    out += [("Results", s) for s in cs.get("results", [])]
    out += [("Key metrics", f"{m.get('label', '')}: {m.get('value', '')}") for m in cs.get("key_metrics", [])]
    return out


def _snippet(text: str, needle: str, width: int = 45) -> str:
    idx = text.lower().find(needle.lower())
    if idx == -1:
        return text[: width * 2]
    start, end = max(0, idx - width), min(len(text), idx + len(needle) + width)
    return ("..." if start else "") + text[start:end] + ("..." if end < len(text) else "")


# --------------------------------------------------------------------------- #
# Individual checks
# --------------------------------------------------------------------------- #
def check_unknown_numbers(content: dict, source: str) -> list[str]:
    allowed = numbers_in(source) | IGNORE_NUMBERS
    issues = []
    for where, text in _fields(content):
        for n in sorted(numbers_in(text) - allowed):
            token = _fmt(n)
            m = re.search(rf"{re.escape(token)}|{re.escape(str(int(n)) if n == int(n) else token)}", text)
            snippet = _snippet(text, m.group(0) if m else token)
            issues.append(f'{where}: the number "{token}" does not appear in the notes '
                          f'(possibly calculated or invented) -> "{snippet}"')
    return issues


def check_percentage_points(content: dict, notes: str) -> list[str]:
    """Flag 'by X%' when X is just the gap between two percentages in a 'from A% to B%' change."""
    changes = []
    for s in _sentences(notes):
        m = re.search(rf"from\s+{APPROX}(\d+(?:\.\d+)?)\s*%.*?\bto\s+{APPROX}(\d+(?:\.\d+)?)\s*%", s, re.IGNORECASE)
        if m:
            a, b = float(m.group(1)), float(m.group(2))
            subject = s[: m.start()]
            subject = TIMESTAMP.sub(" ", subject.split(":")[-1])
            keywords = {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z-]{3,}", subject)} - {"went", "dropped", "fell", "rose"}
            changes.append((a, b, keywords))

    issues = []
    for where, text in _fields(content):
        for m in re.finditer(rf"\bby\s+{APPROX}(\d+(?:\.\d+)?)\s*%", text, re.IGNORECASE):
            x = float(m.group(1))
            before = text[max(0, m.start() - 70): m.start()].lower()
            for a, b, keys in changes:
                if abs(abs(a - b) - x) < 0.01 and (not keys or any(k in before for k in keys)):
                    issues.append(f'{where}: "by {_fmt(x)}%" is the percentage-POINT gap between '
                                  f'{_fmt(a)}% and {_fmt(b)}% - write "from {_fmt(a)}% to {_fmt(b)}%" instead '
                                  f'-> "{_snippet(text, m.group(0))}"')
    return issues


_TIMEFRAME = re.compile(
    r"\b(?:first|last|past|next|in|within|over|after)[\s-]+(?:just\s+|the\s+)?(?:first[\s-]+|last[\s-]+)?"
    r"(\d+|a|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)?[\s-]*"
    r"(day|week|month|quarter|year)s?\b",
    re.IGNORECASE,
)
PCT = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?)\s*%")
# A timeframe only applies inside its own clause: "X fell from 40% to 15% AND Y rose 25% in 3 months"
CLAUSE_SPLIT = re.compile(r"\s+and\s+|;|\s+while\s+|\s+but\s+|\s+whereas\s+", re.IGNORECASE)


def _frame(qty: str, unit: str) -> tuple[int, str]:
    q = (qty or "1").lower()
    return (int(q) if q.isdigit() else WORD_NUMBERS.get(q, 1), unit.lower())


def _pct_frames(text: str) -> list[tuple[str, tuple[int, str]]]:
    """Pair each percentage with the NEAREST timeframe in the same clause (if any)."""
    pairs = []
    for sent in _sentences(text):
        for clause in CLAUSE_SPLIT.split(sent):
            frames = [(m.start(), _frame(*m.groups())) for m in _TIMEFRAME.finditer(clause)]
            if not frames:
                continue
            for m in PCT.finditer(clause):
                nearest = min(frames, key=lambda f: abs(f[0] - m.start()))[1]
                pairs.append((m.group(1), nearest))
    return pairs


def _say(frame: tuple[int, str]) -> str:
    n, u = frame
    return f"{n} {u}{'s' if n > 1 else ''}"


def check_timeframes(content: dict, notes: str) -> list[str]:
    """A percentage stated with a timeframe must keep the timeframe the client used for it."""
    source: dict[str, set] = {}
    for pct, frame in _pct_frames(TIMESTAMP.sub(" ", notes)):
        source.setdefault(pct, set()).add(frame)
    issues = []
    for where, text in _fields(content):
        for pct, frame in _pct_frames(text):
            if pct in source and frame not in source[pct]:
                issues.append(f'{where}: {pct}% is given with timeframe "{_say(frame)}" but the notes say '
                              f'"{", ".join(_say(f) for f in sorted(source[pct]))}" -> "{_snippet(text, pct + "%")}"')
    return list(dict.fromkeys(issues))


STOP = set("""that this with have from they them their there were what when your into been just
like really also very about would could which will then than more most only over some such
because before after where while those these other being every much make made good great""".split())
SPEAKER_LINE = re.compile(r"^\s*(?:\[[\d:]+\]\s*)?([A-Z][\w.']*(?:\s[A-Z][\w.']*){0,2})\s*(\([^)]*\))?\s*:\s*(.+)$")


def _content_words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z']{4,}", text.lower()) if w not in STOP}


def speaker_lines(notes: str) -> dict[str, str]:
    """Map client-side speaker first name -> everything they said (interviewer excluded)."""
    speakers: dict[str, str] = {}
    for line in notes.splitlines():
        m = SPEAKER_LINE.match(line)
        if not m:
            continue
        name, tag, said = m.group(1), (m.group(2) or "").lower(), m.group(3)
        if name.lower() in {"q", "a", "interviewer", "host", "me", "us", "participants", "note", "notes"} \
                or any(t in tag for t in ("interviewer", "agency", "host")):
            continue
        # unnamed audio speakers ("Speaker B", "Speaker C") must stay separate people
        key = name.lower() if name.lower().startswith("speaker ") else name.split()[0].lower()
        speakers[key] = speakers.get(key, "") + " " + said
    return speakers


def check_attribution(content: dict, notes: str) -> list[str]:
    speakers = speaker_lines(notes)
    if len(speakers) < 2:
        return []  # single speaker - nothing to mix up
    vocab = {k: _content_words(v) for k, v in speakers.items()}
    issues = []
    for i, q in enumerate(content.get("testimonials", []), 1):
        words = _content_words(q.get("text", ""))
        if len(words) < 4:
            continue
        scores = {k: len(words & v) / len(words) for k, v in vocab.items()}
        full = str(q.get("speaker_name", "")).lower().strip()
        name_words = {w.strip(".") for w in full.split()}
        credited = next((k for k in speakers if k in name_words or k == full), None)
        best = max(scores, key=scores.get)
        if credited and best != credited and scores[best] - scores[credited] >= 0.15:
            issues.append(f'Testimonial {i}: credited to {q.get("speaker_name")} but the wording mostly '
                          f'matches what {best.title()} said - credit {best.title()} or rewrite with '
                          f'{credited.title()}\'s own words')
    return issues


def check_repeated_stats(content: dict) -> list[str]:
    seen: dict[float, list[int]] = {}
    for i, q in enumerate(content.get("testimonials", []), 1):
        for n in {x for x in numbers_in(q.get("text", "")) if x >= 5}:  # skip small counting words
            seen.setdefault(n, []).append(i)
    repeats = [f"{_fmt(n)} (testimonials {', '.join(map(str, ids))})"
               for n, ids in sorted(seen.items()) if len(ids) >= 2]
    if not repeats:
        return []
    return ["Same figures repeated across testimonials: " + "; ".join(repeats)
            + " - give each testimonial a different angle"]


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
_PERCENT_WORDS = re.compile(r"\b(\d+(?:\.\d+)?|" + "|".join(WORD_NUMBERS) + r")\s*(?:percent|per cent|pc)\b",
                            re.IGNORECASE)


def spoken_percent_to_symbol(text: str) -> str:
    """'nine percent' / '9 percent' -> '9%' (speech-to-text often writes numbers as words)."""
    def repl(m):
        tok = m.group(1).lower()
        n = float(tok) if tok[0].isdigit() else float(WORD_NUMBERS[tok])
        return f"{_fmt(n)}%"
    return _PERCENT_WORDS.sub(repl, text)


def fact_check(content: dict, notes: str, details_text: str = "") -> list[str]:
    notes = spoken_percent_to_symbol(notes)
    content = {
        "testimonials": [{**q, "text": spoken_percent_to_symbol(q.get("text", ""))}
                         for q in content.get("testimonials", [])],
        "case_study": {k: (spoken_percent_to_symbol(v) if isinstance(v, str) else
                           [spoken_percent_to_symbol(x) if isinstance(x, str) else x for x in v]
                           if isinstance(v, list) else v)
                       for k, v in content.get("case_study", {}).items()},
    }
    source = notes + "\n" + details_text
    issues = (check_unknown_numbers(content, source)
              + check_percentage_points(content, notes)
              + check_timeframes(content, notes)
              + check_attribution(content, notes)
              + check_repeated_stats(content))
    return list(dict.fromkeys(issues))  # de-duplicate, keep order

