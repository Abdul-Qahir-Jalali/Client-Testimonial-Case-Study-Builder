"""Editorial case-study page for the Streamlit front end.

Reads like a story, top to bottom:

  Cover (headline + standfirst + facts)  ->  The numbers  ->  Opening quote
  -> Chapter 01 The Challenge -> Chapter 02 The Approach -> Chapter 03 The Outcome (+ before/after)
  -> In their words  ->  Closing quote  ->  Sign-off

Built from the same fact-checked content as the Markdown file. Everything coming from the model is
HTML-escaped. The internal "Review before publishing" checklist is NOT part of this view.
"""

from __future__ import annotations

import html
import re

from icons import mask_url

ARROW_SPLIT = re.compile(r"\s*(?:->|→|=>|⟶)\s*|\s+to\s+", re.IGNORECASE)
NUMBER = re.compile(r"(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*(%|[a-zA-Z]+)?")
HIGHLIGHT = re.compile(r"(~?\d[\d,.]*(?:\s?%|x\b)?(?:\s*(?:->|→)\s*~?\d[\d,.]*%?)?)")
CLOSING_HINTS = ("recommend", "talk to them", "work with", "again", "would", "anyone", "if you")


def _e(text) -> str:
    return html.escape(str(text or ""), quote=True)


def _highlight_numbers(text: str) -> str:
    """Mark the figures. Highlight on the raw text, escaping each piece separately
    (highlighting after escaping would break entities like &#x27;)."""
    text = str(text or "")
    out, last = [], 0
    for m in HIGHLIGHT.finditer(text):
        out.append(_e(text[last:m.start()]))
        core = m.group(1).rstrip(".,")  # keep sentence punctuation outside the highlight
        out.append(f'<span class="cs-num">{_e(core)}</span>')
        last = m.start() + len(core)
    out.append(_e(text[last:]))
    return "".join(out)


def _compact(value: str) -> str:
    """'around 4 hours' -> '~4 hours' for big numerals (same meaning, shorter)."""
    return re.sub(r"^(?:about|around|roughly|approximately|approx\.?)\s+", "~", str(value).strip(), flags=re.IGNORECASE)


def _initials(name: str) -> str:
    parts = [p for p in str(name or "").replace(".", " ").split() if p[:1].isalpha()]
    if len(parts) > 1 and parts[0].lower() in {"dr", "mr", "mrs", "ms", "prof"}:
        parts = parts[1:]
    return ("".join(p[0] for p in parts[:2]) or "·").upper()


# --------------------------------------------------------------------------- #
# Metric parsing: "40% -> 15%", "about 2 days -> around 4 hours", "2,000+", "4.7"
# --------------------------------------------------------------------------- #
def parse_metric(metric: dict) -> dict:
    value = str(metric.get("value", "")).strip()
    parts = [p.strip() for p in ARROW_SPLIT.split(value) if p.strip()]
    out = {"label": str(metric.get("label", "")).strip(), "value": value, "before": None, "after": None, "bars": None}
    if len(parts) == 2:
        out["before"], out["after"] = parts
        b, a = NUMBER.search(parts[0]), NUMBER.search(parts[1])
        if b and a:
            unit_b, unit_a = (b.group(2) or "").lower().rstrip("s"), (a.group(2) or "").lower().rstrip("s")
            if unit_b == unit_a:  # only compare like with like (no "2 days" vs "4 hours" bars)
                out["bars"] = (float(b.group(1).replace(",", "")), float(a.group(1).replace(",", "")))
    return out


# --------------------------------------------------------------------------- #
# Quote selection: opening (short, main contact) / closing (recommendation) / the rest
# --------------------------------------------------------------------------- #
def _pick_featured_quote(testimonials: list[dict], contact: str) -> dict | None:
    if not testimonials:
        return None
    contact = (contact or "").lower().strip()

    def score(q):
        words = len(q.get("text", "").split())
        return (q.get("speaker_name", "").lower().strip() == contact, 6 <= words <= 30, -abs(words - 16))
    return max(testimonials, key=score)


def _pick_closing_quote(testimonials: list[dict], used: list) -> dict | None:
    rest = [q for q in testimonials if all(q is not u for u in used)]
    if not rest:
        return None
    for q in rest:
        text = (q.get("text", "") + " " + q.get("theme", "")).lower()
        if any(h in text for h in CLOSING_HINTS) and len(q.get("text", "").split()) <= 60:
            return q
    return None


# --------------------------------------------------------------------------- #
# Styles
# --------------------------------------------------------------------------- #
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,600;1,9..144,400&family=Inter:wght@400;500;600;700&display=swap');
.cs{--accent:%(accent)s;--accent-soft:color-mix(in srgb,var(--accent) 16%%,transparent);
  --accent-wash:color-mix(in srgb,var(--accent) 6%%,#FBFAF7);--ink:#16161A;--body:#3A3A42;--muted:#8A8A93;
  --hair:#E8E5DE;--paper:#FBFAF7;--card:#FFFFFF;
  --serif:"Fraunces","Iowan Old Style","Palatino Linotype",Georgia,serif;
  --sans:"Inter","Segoe UI",system-ui,-apple-system,sans-serif;
  background:var(--paper);color:var(--body);font-family:var(--sans);border-radius:22px;overflow:hidden;
  border:1px solid var(--hair);line-height:1.65;-webkit-font-smoothing:antialiased}
.cs *{box-sizing:border-box}
.cs .wrap{max-width:1040px;margin:0 auto;padding:0 56px}
@keyframes cs-rise{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
.cs .rise{animation:cs-rise .7s cubic-bezier(.2,.7,.2,1) both}

/* ---------- cover ---------- */
.cs-cover{padding:64px 0 0;position:relative}
.cs-cover:before{content:"";position:absolute;inset:0 0 auto 0;height:6px;background:var(--accent)}
.cs-kicker{display:flex;align-items:center;gap:14px;font-size:12px;font-weight:600;letter-spacing:.18em;
  text-transform:uppercase;color:var(--muted)}
.cs-kicker .dot{width:6px;height:6px;border-radius:50%%;background:var(--accent)}
.cs-kicker b{color:var(--ink);font-weight:600}
.cs-h1{font-family:var(--serif);font-weight:400;color:var(--ink);font-size:clamp(34px,4.6vw,58px);line-height:1.06;
  letter-spacing:-.022em;margin:26px 0 24px;max-width:17ch;font-variation-settings:"opsz" 144}
.cs-stand{font-size:clamp(17px,1.6vw,20px);line-height:1.6;color:var(--body);max-width:62ch;margin:0}
.cs-facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));margin-top:48px;
  border-top:1px solid var(--hair);border-bottom:1px solid var(--hair)}
.cs-fact{padding:18px 20px 18px 0}
.cs-fact + .cs-fact{padding-left:20px;border-left:1px solid var(--hair)}
.cs-fact .k{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);font-weight:600}
.cs-fact .v{font-size:15px;color:var(--ink);font-weight:500;margin-top:4px}

/* ---------- numbers ---------- */
.cs-label{font-size:11.5px;letter-spacing:.18em;text-transform:uppercase;color:var(--muted);font-weight:600;
  display:flex;align-items:center;gap:12px;margin:0 0 22px}
.cs-label:after{content:"";flex:1;height:1px;background:var(--hair)}
.cs-numbers{padding:64px 0 8px}
.cs-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr))}
.cs-stat{padding:4px 28px 8px 0}
.cs-stat + .cs-stat{padding-left:28px;border-left:1px solid var(--hair)}
.cs-stat .from{font-size:13px;color:var(--muted);height:20px}
.cs-stat .from s{text-decoration-thickness:1px}
.cs-stat .big{font-family:var(--serif);font-size:clamp(38px,4vw,54px);line-height:1.02;color:var(--ink);
  letter-spacing:-.02em;margin:2px 0 10px;font-variation-settings:"opsz" 144}
.cs-stat .big em{font-style:normal;color:var(--accent)}
.cs-stat .big.sm{font-size:clamp(30px,3vw,40px);white-space:nowrap}
.cs-stat .lbl{font-size:14px;color:var(--body);max-width:24ch}

/* ---------- quotes ---------- */
.cs-pull{padding:72px 0 64px;text-align:center}
.cs-pull .mark{font-family:var(--serif);font-size:96px;line-height:.6;color:var(--accent);height:44px}
.cs-pull blockquote{font-family:var(--serif);font-weight:400;font-style:italic;color:var(--ink);
  font-size:clamp(26px,3vw,38px);line-height:1.3;letter-spacing:-.012em;margin:14px auto 28px;max-width:26ch}
.cs-by{display:inline-flex;align-items:center;gap:12px;text-align:left}
.cs-av{width:42px;height:42px;border-radius:50%%;background:var(--ink);color:#fff;font-size:13.5px;font-weight:600;
  display:flex;align-items:center;justify-content:center;letter-spacing:.04em;flex-shrink:0}
.cs-by .n{font-size:15px;font-weight:600;color:var(--ink);line-height:1.3}
.cs-by .r{font-size:13px;color:var(--muted)}

/* ---------- chapters (story spine) ---------- */
.cs-story{position:relative;padding:8px 0 24px}
.cs-chapter{display:grid;grid-template-columns:200px 1fr;gap:48px;padding:56px 0;border-top:1px solid var(--hair);position:relative}
.cs-side{position:relative}
.cs-side .no{font-family:var(--serif);font-size:64px;line-height:1;color:var(--accent);letter-spacing:-.03em;
  font-variation-settings:"opsz" 144}
.cs-side .t{font-size:12px;letter-spacing:.18em;text-transform:uppercase;color:var(--ink);font-weight:700;margin-top:14px}
.cs-side .s{font-size:13.5px;color:var(--muted);margin-top:6px;max-width:18ch;line-height:1.5}
.cs-body{font-size:17px;line-height:1.75;color:var(--body);max-width:64ch}
.cs-lead{margin:0}
.cs-lead:first-letter{font-family:var(--serif);float:left;font-size:66px;line-height:.8;padding:7px 6px 0 0;
  margin-right:2px;color:var(--ink);font-weight:400}
.cs-num{color:var(--ink);font-weight:600;background:linear-gradient(transparent 60%%,var(--accent-soft) 60%%);padding:0 1px}

.cs-steps{list-style:none;margin:0;padding:0;position:relative}
.cs-steps:before{content:"";position:absolute;left:15px;top:10px;bottom:10px;width:1px;background:var(--hair)}
.cs-steps li{position:relative;padding:0 0 26px 56px}
.cs-steps li:last-child{padding-bottom:0}
.cs-steps .i{position:absolute;left:0;top:0;width:31px;height:31px;border-radius:50%%;background:var(--card);
  border:1px solid var(--hair);font-size:12px;font-weight:700;color:var(--accent);display:flex;align-items:center;
  justify-content:center}
.cs-steps p{margin:3px 0 0}

.cs-outcomes{display:flex;flex-direction:column}
.cs-out{display:grid;grid-template-columns:28px 1fr;gap:14px;padding:16px 0;border-bottom:1px solid var(--hair)}
.cs-out:first-child{padding-top:0}
.cs-out .ar{width:20px;height:20px;flex:none;margin-top:3px;background-color:var(--accent);
  -webkit-mask:%(arrow)s center/contain no-repeat;mask:%(arrow)s center/contain no-repeat}
.cs-compare{margin-top:34px;background:var(--card);border:1px solid var(--hair);border-radius:16px;padding:26px 28px}
.cs-compare .h{font-size:11.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--muted);font-weight:600;margin-bottom:18px}
.cs-cmp + .cs-cmp{margin-top:22px;padding-top:22px;border-top:1px solid var(--hair)}
.cs-cmp .lbl{font-size:14.5px;font-weight:600;color:var(--ink);margin-bottom:12px}
.cs-row{display:grid;grid-template-columns:64px 1fr 92px;align-items:center;gap:14px;font-size:13px;color:var(--muted)}
.cs-row + .cs-row{margin-top:8px}
.cs-track{height:8px;border-radius:999px;background:#F0EEE8;overflow:hidden}
.cs-fill{height:100%%;border-radius:999px;background:#C9C6BE}
.cs-row.after .cs-fill{background:var(--accent)}
.cs-row .v{text-align:right;color:var(--ink);font-weight:600;font-size:14px}
.cs-row.after .v{color:var(--accent)}

/* ---------- voices ---------- */
.cs-voices{padding:64px 0 16px;border-top:1px solid var(--hair)}
.cs-vgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px}
.cs-voice{background:var(--card);border:1px solid var(--hair);border-radius:16px;padding:28px 28px 24px;
  display:flex;flex-direction:column;gap:22px}
.cs-voice p{font-family:var(--serif);font-size:19px;line-height:1.55;color:var(--ink);margin:0;flex:1}
.cs-voice .cs-av{width:36px;height:36px;font-size:12px;background:var(--accent)}

/* ---------- closing ---------- */
.cs-close{background:var(--ink);color:#EDEBE6;padding:72px 0;margin-top:56px;position:relative}
.cs-close:before{content:"";position:absolute;left:0;right:0;top:0;height:4px;background:var(--accent)}
.cs-close .cs-label{color:#9C9AA3}.cs-close .cs-label:after{background:#2E2E36}
.cs-close blockquote{font-family:var(--serif);font-style:italic;font-weight:400;font-size:clamp(24px,2.6vw,34px);
  line-height:1.35;color:#fff;margin:0 0 28px;max-width:30ch;letter-spacing:-.01em}
.cs-close .cs-av{background:var(--accent)}
.cs-close .cs-by .n{color:#fff}.cs-close .cs-by .r{color:#9C9AA3}
.cs-sign{display:flex;justify-content:space-between;align-items:flex-end;gap:24px;flex-wrap:wrap;margin-top:56px;
  padding-top:28px;border-top:1px solid #2E2E36}
.cs-sign .q{font-family:var(--serif);font-size:clamp(22px,2.2vw,28px);color:#fff;line-height:1.25;max-width:22ch}
.cs-sign .q em{color:var(--accent);font-style:italic;filter:brightness(1.35)}
.cs-sign .m{font-size:13px;color:#9C9AA3;text-align:right}
.cs-sign .m b{display:block;color:#fff;font-size:15px;font-weight:600;margin-top:2px}

@media (max-width:820px){
  .cs .wrap{padding:0 24px}
  .cs-cover{padding-top:44px}
  .cs-chapter{grid-template-columns:1fr;gap:18px;padding:40px 0}
  .cs-side .no{font-size:48px}
  .cs-stat,.cs-stat + .cs-stat{padding:18px 0;border-left:0;border-top:1px solid var(--hair)}
  .cs-fact + .cs-fact{border-left:0;padding-left:0}
  .cs-fact{border-bottom:1px solid var(--hair)}
  .cs-row{grid-template-columns:52px 1fr 80px}
  .cs-sign .m{text-align:left}
}
</style>
"""


# --------------------------------------------------------------------------- #
# Page
# --------------------------------------------------------------------------- #
def _byline(q: dict, company: str) -> str:
    role = ", ".join(x for x in [q.get("speaker_role"), company] if x)
    return (f'<div class="cs-by"><div class="cs-av">{_e(_initials(q.get("speaker_name")))}</div>'
            f'<div><div class="n">{_e(q.get("speaker_name"))}</div><div class="r">{_e(role)}</div></div></div>')


def render_case_study_html(content: dict, details, accent: str = "#4f46e5") -> str:
    cs = content.get("case_study", {})
    quotes = content.get("testimonials", [])
    metrics = [parse_metric(m) for m in cs.get("key_metrics", []) if m.get("value")]
    client = details.client_name or "the client"

    opening = _pick_featured_quote(quotes, details.contact_name)
    closing = _pick_closing_quote(quotes, [opening])
    voices = [q for q in quotes if q is not opening and q is not closing][:4]

    p = [CSS % {"accent": _e(accent), "arrow": mask_url("arrow-up-right")},   # st.html strips <svg>, so it's a CSS mask
         '<article class="cs">']

    # ---- cover
    facts = [("Client", details.client_name), ("Industry", details.industry), ("Service", details.service),
             ("Timeline", details.timeline), ("Partner", details.agency_name)]
    facts_html = "".join(f'<div class="cs-fact"><div class="k">{_e(k)}</div><div class="v">{_e(v)}</div></div>'
                         for k, v in facts if v)
    p.append(f'<header class="cs-cover"><div class="wrap rise">'
             f'<div class="cs-kicker"><span class="dot"></span>Case study<span>·</span><b>{_e(client)}</b></div>'
             f'<h1 class="cs-h1">{_e(cs.get("title"))}</h1>'
             f'<p class="cs-stand">{_e(cs.get("summary"))}</p>'
             f'<div class="cs-facts">{facts_html}</div></div></header>')

    # ---- the numbers
    if metrics:
        stats = []
        shown = [_compact(m["after"] if m["before"] else m["value"]) for m in metrics[:4]]
        size = " sm" if any(len(v) > 6 for v in shown) else ""  # one size for the whole row
        for m in metrics[:4]:
            if m["before"]:
                after = _compact(m["after"])
                stats.append(f'<div class="cs-stat"><div class="from">from <s>{_e(_compact(m["before"]))}</s></div>'
                             f'<div class="big{size}"><em>{_e(after)}</em></div>'
                             f'<div class="lbl">{_e(m["label"])}</div></div>')
            else:
                value = _compact(m["value"])
                stats.append(f'<div class="cs-stat"><div class="from"></div>'
                             f'<div class="big{size}">{_e(value)}</div>'
                             f'<div class="lbl">{_e(m["label"])}</div></div>')
        p.append(f'<section class="cs-numbers"><div class="wrap rise" style="animation-delay:.1s">'
                 f'<div class="cs-label">The results, in numbers</div><div class="cs-stats">{"".join(stats)}</div>'
                 f'</div></section>')

    # ---- opening quote
    if opening:
        p.append(f'<section class="cs-pull"><div class="wrap rise" style="animation-delay:.2s">'
                 f'<div class="mark">“</div><blockquote>{_e(opening["text"])}</blockquote>'
                 f'{_byline(opening, client)}</div></section>')

    # ---- chapters
    steps = "".join(f'<li><span class="i">{i:02d}</span><p>{_highlight_numbers(s)}</p></li>'
                    for i, s in enumerate(cs.get("solution", []), 1))
    outcomes = "".join(f'<div class="cs-out"><span class="ar"></span><div>{_highlight_numbers(r)}</div></div>'
                       for r in cs.get("results", []))

    compare = ""
    bar_metrics = [m for m in metrics if m["bars"]][:3]
    if bar_metrics:
        rows = []
        for m in bar_metrics:
            b, a = m["bars"]
            top = max(b, a) or 1
            rows.append(
                f'<div class="cs-cmp"><div class="lbl">{_e(m["label"])}</div>'
                f'<div class="cs-row"><span>Before</span><div class="cs-track"><div class="cs-fill" '
                f'style="width:{max(3, 100 * b / top):.1f}%"></div></div><span class="v">{_e(_compact(m["before"]))}</span></div>'
                f'<div class="cs-row after"><span>After</span><div class="cs-track"><div class="cs-fill" '
                f'style="width:{max(3, 100 * a / top):.1f}%"></div></div><span class="v">{_e(_compact(m["after"]))}</span></div></div>')
        compare = f'<div class="cs-compare"><div class="h">Before &amp; after</div>{"".join(rows)}</div>'

    chapters = [
        ("01", "The Challenge", f"Where {client} started",
         f'<p class="cs-lead">{_highlight_numbers(cs.get("challenge"))}</p>'),
        ("02", "The Approach", "What we built together", f'<ol class="cs-steps">{steps}</ol>'),
        ("03", "The Outcome", "What changed", f'<div class="cs-outcomes">{outcomes}</div>{compare}'),
    ]
    p.append('<section class="cs-story"><div class="wrap">')
    for no, title, sub, body in chapters:
        p.append(f'<div class="cs-chapter"><div class="cs-side"><div class="no">{no}</div>'
                 f'<div class="t">{_e(title)}</div><div class="s">{_e(sub)}</div></div>'
                 f'<div class="cs-body">{body}</div></div>')
    p.append('</div></section>')

    # ---- in their words
    if voices:
        cards = "".join(f'<div class="cs-voice"><p>“{_e(q["text"])}”</p>{_byline(q, "")}</div>' for q in voices)
        p.append(f'<section class="cs-voices"><div class="wrap"><div class="cs-label">In their words</div>'
                 f'<div class="cs-vgrid">{cards}</div></div></section>')

    # ---- closing
    close_quote = (f'<div class="cs-label">The last word</div><blockquote>“{_e(closing["text"])}”</blockquote>'
                   f'{_byline(closing, client)}') if closing else ""
    p.append(f'<footer class="cs-close"><div class="wrap">{close_quote}'
             f'<div class="cs-sign" style="{"" if closing else "margin-top:0;border-top:0;padding-top:0"}">'
             f'<div class="q">Ready to write <em>your</em> next chapter?</div>'
             f'<div class="m">A case study by<b>{_e(details.agency_name)}</b></div></div></div></footer>')

    p.append("</article>")
    return "".join(p)
