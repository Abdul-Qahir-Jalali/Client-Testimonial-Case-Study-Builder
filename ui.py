"""Front-end look & feel: global styles and small HTML components for the Streamlit app.

Purely presentational - no business logic lives here. All model-generated text is HTML-escaped.
"""

from __future__ import annotations

import html

import streamlit as st

from icons import ICONS, svg, widget_icons_css

ACCENT = "#4F46E5"

# Native Streamlit widget labels can't hold SVG, so each gets a Lucide icon via CSS (keys are set in app.py).
WIDGET_ICONS = [
    (".st-key-btn_transcribe button p", "mic"),
    (".st-key-btn_transcribe_url button p", "mic"),
    (".st-key-btn_use_transcript button p", "circle-check"),
    (".st-key-btn_generate button p", "sparkles"),
    (".st-key-btn_save button p", "save"),
    (".st-key-dl_markdown button p", "download"),
    (".st-key-input_mode [role=\"radiogroup\"] > :nth-child(1) p", "pen-line"),
    (".st-key-input_mode [role=\"radiogroup\"] > :nth-child(2) p", "file-text"),
    (".st-key-input_mode [role=\"radiogroup\"] > :nth-child(3) p", "clapperboard"),
    (".st-key-media_source [role=\"radiogroup\"] > :nth-child(1) p", "upload"),
    (".st-key-media_source [role=\"radiogroup\"] > :nth-child(2) p", "link"),
    (".st-key-cs_view [role=\"radiogroup\"] > :nth-child(1) p", "play"),
    (".st-key-cs_view [role=\"radiogroup\"] > :nth-child(2) p", "book-open"),
    (".st-key-md_view [role=\"radiogroup\"] > :nth-child(1) p", "eye"),
    (".st-key-md_view [role=\"radiogroup\"] > :nth-child(2) p", "code-xml"),
    ('[role="tablist"] > [role="tab"]:nth-child(1) p', "message-square-quote"),
    ('[role="tablist"] > [role="tab"]:nth-child(2) p', "chart-column"),
    ('[role="tablist"] > [role="tab"]:nth-child(3) p', "file-text"),
    (".st-key-exp_fixed summary p", "wrench"),
    (".st-key-exp_review summary p", "lock"),
]


def _e(text) -> str:
    return html.escape(str(text or ""), quote=True)


# --------------------------------------------------------------------------- #
# Global CSS
# --------------------------------------------------------------------------- #
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root{--accent:#4F46E5;--accent-2:#7C3AED;--ink:#0F172A;--muted:#64748B;--line:#E2E8F0;--soft:#EEF2FF;--bg:#F6F7FB}
html, body, [class*="css"], .stApp, .stMarkdown, button, input, textarea, select{
  font-family:"Inter","Segoe UI",system-ui,-apple-system,sans-serif !important}
.stApp{background:var(--bg)}

/* hide Streamlit chrome */
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stAppDeployButton"], [data-testid="stDecoration"]{display:none !important}
header[data-testid="stHeader"]{background:transparent;height:0}
.block-container{padding-top:1.6rem !important;padding-bottom:3rem !important;max-width:1280px}

/* sidebar */
[data-testid="stSidebar"]{background:#0F172A}
[data-testid="stSidebar"] *{color:#E2E8F0}
[data-testid="stSidebar"] .sb-muted{color:#94A3B8 !important}
[data-testid="stSidebar"] input, [data-testid="stSidebar"] [data-baseweb="select"] > div{
  background:#1E293B !important;border-color:#334155 !important;color:#F1F5F9 !important}
[data-testid="stSidebar"] [data-baseweb="select"] *{color:#F1F5F9 !important}
[data-testid="stSidebar"] .stButton button{background:#1E293B;border:1px solid #334155;color:#F1F5F9}
[data-testid="stSidebar"] .stButton button:hover{border-color:var(--accent);color:#fff;background:#273449}
[data-testid="stSidebar"] hr{border-color:#1E293B}
[data-testid="stSidebar"] label p{font-size:13px !important;color:#CBD5E1 !important}

/* bordered containers -> cards (each card container has key="card_..." -> class "st-key-card_...") */
.stMain [class*="st-key-card_"]{background:#fff !important;border:1px solid var(--line) !important;border-radius:18px !important;
  box-shadow:0 1px 2px rgba(15,23,42,.04),0 8px 24px rgba(15,23,42,.05);padding:22px 22px 18px !important}
.stMain [class*="st-key-card_spk"]{border-radius:14px !important;box-shadow:none;background:#F8FAFC !important;padding:14px 16px !important}
.stMain [class*="st-key-card_markdown"]{padding:26px 32px !important}

/* inputs */
.stTextInput input, .stTextArea textarea, [data-baseweb="select"] > div{border-radius:10px !important}
.stTextArea textarea{font-size:14px;line-height:1.55}
.stTextInput input:focus, .stTextArea textarea:focus{border-color:var(--accent) !important;
  box-shadow:0 0 0 3px rgba(79,70,229,.15) !important}
label p{font-weight:500 !important;color:#334155 !important}

/* buttons */
.stButton button, .stDownloadButton button{border-radius:10px !important;font-weight:600 !important;
  transition:all .15s ease;min-height:42px}
.stButton button[kind="primary"], [data-testid="stBaseButton-primary"]{
  background:linear-gradient(135deg,var(--accent),var(--accent-2)) !important;border:0 !important;color:#fff !important;
  box-shadow:0 6px 18px rgba(79,70,229,.30)}
.stButton button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover{transform:translateY(-1px);
  box-shadow:0 10px 24px rgba(79,70,229,.38)}
.stButton button[kind="primary"]:disabled, [data-testid="stBaseButton-primary"]:disabled{
  background:#CBD5E1 !important;box-shadow:none;color:#fff !important}
.stMain .stButton button[kind="secondary"], .stMain [data-testid="stBaseButton-secondary"],
.stDownloadButton button{background:#fff;border:1px solid var(--line);color:var(--ink)}
.stMain .stButton button[kind="secondary"]:hover, .stDownloadButton button:hover{border-color:var(--accent);color:var(--accent)}

/* radio -> segmented pills (new Streamlit: stRadioOption + data-selected; older: label:has(input:checked)) */
.stMain [role="radiogroup"]{gap:8px !important;flex-wrap:wrap}
.stMain [data-testid="stRadioOption"], .stMain [role="radiogroup"] > label{background:#F1F5F9;border:1px solid var(--line);
  border-radius:999px;padding:7px 16px !important;margin:0 !important;transition:all .15s ease;cursor:pointer}
.stMain [data-testid="stRadioOption"]:hover, .stMain [role="radiogroup"] > label:hover{border-color:#C7D2FE;background:#F8FAFF}
.stMain [data-testid="stRadioOption"][data-selected="true"], .stMain [role="radiogroup"] > label:has(input:checked){
  background:var(--soft);border-color:var(--accent);box-shadow:0 0 0 1px var(--accent) inset}
.stMain [data-testid="stRadioOption"][data-selected="true"] p, .stMain [role="radiogroup"] > label:has(input:checked) p{
  color:var(--accent) !important;font-weight:600 !important}
.stMain [data-testid="stRadioOption"] > div > div:first-child:not([data-testid="stMarkdownContainer"]),
.stMain [role="radiogroup"] > label > div:first-child:not(:has([data-testid="stMarkdownContainer"])){display:none !important}
.stMain [data-testid="stRadioOption"] p{margin:0 !important;font-size:14px}

/* file uploader */
[data-testid="stFileUploaderDropzone"]{border:2px dashed #C7D2FE !important;background:#F8FAFF !important;
  border-radius:14px !important}
[data-testid="stFileUploaderDropzone"]:hover{border-color:var(--accent) !important;background:var(--soft) !important}

/* tabs */
.stTabs [data-baseweb="tab-list"]{gap:6px;background:#fff;border:1px solid var(--line);border-radius:14px;padding:6px}
.stTabs [data-baseweb="tab"]{border-radius:10px;padding:8px 18px;height:auto}
.stTabs [aria-selected="true"]{background:var(--soft)}
.stTabs [aria-selected="true"] p{color:var(--accent) !important;font-weight:700 !important}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"]{display:none}

/* alerts & expanders */
[data-testid="stAlert"]{border-radius:12px}
[data-testid="stExpander"] details{border-radius:12px !important;border:1px solid var(--line) !important;background:#fff}

/* ---------- custom components ---------- */
.hero{background:radial-gradient(1200px 400px at 85% -20%,rgba(124,58,237,.55),transparent 60%),
  linear-gradient(135deg,#1E1B4B 0%,#312E81 45%,#4F46E5 100%);border-radius:22px;padding:34px 38px;color:#fff;
  position:relative;overflow:hidden;margin-bottom:18px}
.hero:after{content:"";position:absolute;right:-60px;bottom:-90px;width:280px;height:280px;border-radius:50%;
  background:rgba(255,255,255,.06)}
.hero .tag{display:inline-flex;align-items:center;gap:8px;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.2);
  padding:5px 12px;border-radius:999px;font-size:12px;font-weight:600;letter-spacing:.04em}
.hero h1{font-size:34px !important;line-height:1.15;font-weight:800 !important;margin:14px 0 8px !important;color:#fff !important;
  padding:0 !important}
.hero p{font-size:16px;color:#E0E7FF;max-width:760px;margin:0}
.hero .feats{display:flex;flex-wrap:wrap;gap:10px;margin-top:20px}
.hero .feat{display:flex;align-items:center;gap:8px;background:rgba(15,23,42,.25);border:1px solid rgba(255,255,255,.14);
  padding:8px 14px;border-radius:12px;font-size:13px;color:#EEF2FF}

.sec-head{display:flex;align-items:center;gap:12px;margin:2px 0 6px}
.sec-head .num{width:30px;height:30px;border-radius:9px;background:var(--soft);color:var(--accent);font-weight:800;
  display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0}
.sec-head .num svg{display:block}
.sec-head .t{font-size:17px;font-weight:700;color:var(--ink);line-height:1.2}
.sec-head .s{font-size:13px;color:var(--muted);margin-top:2px}

.note{font-size:12.5px;color:var(--muted);display:flex;gap:6px;align-items:center;margin-top:6px}
.note svg{flex:none}
.hero .tag svg,.hero .feat svg{flex:none}

.banner{border-radius:14px;padding:14px 18px;display:flex;gap:12px;align-items:flex-start;font-size:14px;margin:6px 0 12px}
.banner .ic{display:flex;flex:none;margin-top:1px}
.banner b{display:block;margin-bottom:2px}
.banner.ok{background:#ECFDF5;border:1px solid #A7F3D0;color:#065F46}
.banner.warn{background:#FFFBEB;border:1px solid #FDE68A;color:#92400E}
.banner.err{background:#FEF2F2;border:1px solid #FECACA;color:#991B1B}
.banner.info{background:var(--soft);border:1px solid #C7D2FE;color:#3730A3}
.banner ul{margin:6px 0 0 0;padding-left:18px}.banner li{margin-bottom:4px}

.results-head{display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:12px;margin:26px 0 12px}
.results-head .t{font-size:24px;font-weight:800;color:var(--ink)}
.results-head .s{font-size:14px;color:var(--muted)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-bottom:14px}
.stat{background:#fff;border:1px solid var(--line);border-radius:14px;padding:14px 16px}
.stat .v{font-size:22px;font-weight:800;color:var(--ink)}
.stat .l{font-size:12.5px;color:var(--muted);margin-top:2px}
.stat.good .v{color:#059669}.stat.bad .v{color:#DC2626}

.quotes{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:14px;margin-top:6px}
.qcard{background:#fff;border:1px solid var(--line);border-radius:16px;padding:20px 22px;display:flex;flex-direction:column;
  gap:14px;box-shadow:0 1px 2px rgba(15,23,42,.04)}
.qcard .meta{display:flex;gap:6px;flex-wrap:wrap}
.pill{font-size:11.5px;font-weight:600;padding:3px 10px;border-radius:999px;background:#F1F5F9;color:#475569}
.pill.short{background:#ECFDF5;color:#047857}.pill.medium{background:#EFF6FF;color:#1D4ED8}.pill.long{background:#F5F3FF;color:#6D28D9}
.qcard .q{font-size:16px;line-height:1.6;color:#1E293B;flex:1}
.qcard .who{display:flex;align-items:center;gap:10px;border-top:1px solid #F1F5F9;padding-top:12px}
.avatar{width:34px;height:34px;border-radius:50%;background:linear-gradient(135deg,var(--accent),var(--accent-2));color:#fff;
  font-weight:700;font-size:13px;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.who .n{font-size:14px;font-weight:700;color:var(--ink)}.who .r{font-size:12.5px;color:var(--muted)}

.empty{background:#fff;border:1px dashed #CBD5E1;border-radius:18px;padding:34px;text-align:center;color:var(--muted);margin-top:22px}
.empty .big{color:var(--accent)}.empty .big svg{display:block;margin:0 auto}.empty .t{font-size:16px;font-weight:700;color:#334155;margin-top:6px}

.sb-brand{display:flex;align-items:center;gap:10px;margin:4px 0 18px}
.sb-logo{width:38px;height:38px;border-radius:11px;background:linear-gradient(135deg,#6366F1,#A855F7);display:flex;
  align-items:center;justify-content:center;color:#fff}
.sb-name{font-weight:800;font-size:15px;color:#fff !important;line-height:1.15}
.sb-sub{font-size:11.5px;color:#94A3B8 !important}
.sb-title{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:#94A3B8 !important;font-weight:700;margin:6px 0 8px}
.sb-steps{display:flex;flex-direction:column;gap:10px;margin-bottom:6px}
.sb-step{display:flex;gap:10px;align-items:flex-start;font-size:13px;color:#CBD5E1 !important}
.sb-step .n{width:22px;height:22px;border-radius:7px;background:#1E293B;border:1px solid #334155;color:#A5B4FC !important;
  font-size:11px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.sb-foot{font-size:11.5px;color:#64748B !important;margin-top:18px}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(f"<style>{widget_icons_css(WIDGET_ICONS)}</style>", unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Components
# --------------------------------------------------------------------------- #
def hero() -> None:
    st.markdown(
        f"""
<div class="hero">
  <span class="tag">{svg("sparkles", 14)} AI CONTENT STUDIO</span>
  <h1>Client Testimonial &amp; Case Study Builder</h1>
  <p>Turn raw client feedback, interview transcripts or recordings into polished testimonials and a
     Challenge {svg("arrow-right", 15)} Solution {svg("arrow-right", 15)} Results case study, with every number fact-checked against the source.</p>
  <div class="feats">
    <span class="feat">{svg("mic", 16)} Text, audio, video &amp; links</span>
    <span class="feat">{svg("message-square-quote", 16)} 3–5 polished testimonials</span>
    <span class="feat">{svg("chart-column", 16)} Visual case study</span>
    <span class="feat">{svg("shield-check", 16)} Built-in fact check</span>
    <span class="feat">{svg("file-text", 16)} Markdown export</span>
  </div>
</div>""",
        unsafe_allow_html=True,
    )


def section_head(num: int | str, title: str, subtitle: str = "") -> None:
    """`num` is a step number, or the name of a Lucide icon."""
    badge = svg(num, 17) if num in ICONS else _e(num)
    sub = f'<div class="s">{_e(subtitle)}</div>' if subtitle else ""
    st.markdown(f'<div class="sec-head"><div class="num">{badge}</div><div><div class="t">{_e(title)}</div>{sub}</div></div>',
                unsafe_allow_html=True)


def note(text: str, icon: str = "info") -> None:
    st.markdown(f'<div class="note">{svg(icon, 14)} <span>{_e(text)}</span></div>', unsafe_allow_html=True)


def banner(kind: str, title: str, body: str = "", items: list[str] | None = None, icon: str | None = None) -> None:
    """`icon` is the name of a Lucide icon; defaults to one that matches `kind`."""
    icons = {"ok": "circle-check", "warn": "triangle-alert", "err": "octagon-x", "info": "lightbulb"}
    lst = "".join(f"<li>{_e(i)}</li>" for i in (items or []))
    lst = f"<ul>{lst}</ul>" if lst else ""
    body_html = f"<span>{_e(body)}</span>" if body else ""
    st.markdown(f'<div class="banner {kind}"><div class="ic">{svg(icon or icons[kind], 20)}</div>'
                f'<div><b>{_e(title)}</b>{body_html}{lst}</div></div>', unsafe_allow_html=True)


def sidebar_brand() -> None:
    st.markdown(
        f"""
<div class="sb-brand"><div class="sb-logo">{svg("sparkles", 20)}</div>
  <div><div class="sb-name">Testimonial Studio</div><div class="sb-sub">Case studies from client feedback</div></div></div>
<div class="sb-title">How it works</div>
<div class="sb-steps">
  <div class="sb-step"><span class="n">1</span>Add feedback: notes, a file, a recording or a link</div>
  <div class="sb-step"><span class="n">2</span>Fill in the project details</div>
  <div class="sb-step"><span class="n">3</span>Generate, review the fact check, export</div>
</div>""",
        unsafe_allow_html=True,
    )


def sidebar_title(text: str) -> None:
    st.markdown(f'<div class="sb-title">{_e(text)}</div>', unsafe_allow_html=True)


def sidebar_footer() -> None:
    st.markdown('<div class="sb-foot">Powered by Groq · ElevenLabs Scribe<br>Always get client approval before publishing.</div>',
                unsafe_allow_html=True)


def empty_state() -> None:
    st.markdown(
        f"""<div class="empty"><div class="big">{svg("sparkles", 36)}</div><div class="t">Your content will appear here</div>
        <div>Add client feedback, fill in the project details and click <b>Generate content</b>.</div></div>""",
        unsafe_allow_html=True,
    )


def results_header(content: dict, client: str) -> None:
    fc = content.get("fact_check", {})
    issues = len(fc.get("issues", []))
    quotes = content.get("testimonials", [])
    speakers = len({q.get("speaker_name", "") for q in quotes})
    metrics = len(content.get("case_study", {}).get("key_metrics", []))
    fixed = len(fc.get("auto_fixed", []))
    check_cls, check_v, check_l = (("bad", f"{issues} to review", "Fact check")
                                   if issues else ("good", "Passed", "Fact check"))
    st.markdown(
        f"""
<div class="results-head"><div><div class="t">Your content is ready</div>
<div class="s">Generated for {_e((client or "your client").rstrip("."))}. Review it below, then download the Markdown file.</div></div></div>
<div class="stats">
  <div class="stat"><div class="v">{len(quotes)}</div><div class="l">Testimonials</div></div>
  <div class="stat"><div class="v">{speakers}</div><div class="l">Client voice{"s" if speakers != 1 else ""} quoted</div></div>
  <div class="stat"><div class="v">{metrics}</div><div class="l">Key metrics</div></div>
  <div class="stat {check_cls}"><div class="v">{check_v}</div><div class="l">{check_l}{f" · {fixed} auto-fixed" if fixed else ""}</div></div>
</div>""",
        unsafe_allow_html=True,
    )


def _initials(name: str) -> str:
    parts = [p for p in str(name or "").replace(".", " ").split() if p[:1].isalpha()]
    if parts and parts[0].lower() in {"dr", "mr", "mrs", "ms", "prof"} and len(parts) > 1:
        parts = parts[1:]
    return ("".join(p[0] for p in parts[:2]) or "?").upper()


def testimonial_cards(quotes: list[dict], company: str) -> None:
    cards = []
    for q in quotes:
        length = str(q.get("length", "medium")).lower()
        words = len(str(q.get("text", "")).split())
        theme = f'<span class="pill">{_e(q.get("theme"))}</span>' if q.get("theme") else ""
        role = ", ".join(x for x in [q.get("speaker_role"), company] if x)
        cards.append(
            f'<div class="qcard"><div class="meta"><span class="pill {_e(length)}">{_e(length.title())}</span>{theme}'
            f'<span class="pill">{words} words</span></div>'
            f'<div class="q">“{_e(q.get("text"))}”</div>'
            f'<div class="who"><div class="avatar">{_e(_initials(q.get("speaker_name")))}</div>'
            f'<div><div class="n">{_e(q.get("speaker_name"))}</div><div class="r">{_e(role)}</div></div></div></div>')
    st.markdown(f'<div class="quotes">{"".join(cards)}</div>', unsafe_allow_html=True)
