"""Front-end look & feel: global styles and small HTML components for the Streamlit app.

Purely presentational - no business logic lives here. All model-generated text is HTML-escaped.
"""

from __future__ import annotations

import html
import itertools

import streamlit as st

from icons import ICONS, svg, widget_icons_css

ACCENT = "#4F46E5"

# Native Streamlit widget labels can't hold SVG, so each gets a Lucide icon via CSS (keys are set in app.py).
WIDGET_ICONS = [
    (".st-key-btn_transcribe button p", "mic"),
    (".st-key-btn_transcribe_url button p", "mic"),
    (".st-key-btn_use_transcript button p", "circle-check"),
    (".st-key-btn_generate button p", "sparkles"),
    (".st-key-btn_load_sample button p", "file-text"),
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
    ('[role="tablist"] > [role="tab"]:nth-child(4) p', "video"),
    ('[role="tablist"] > [role="tab"]:nth-child(5) p', "share-2"),
    (".st-key-btn_captions button p", "wand-sparkles"),
    (".st-key-dl_video_share button p", "download"),
    (".st-key-btn_video button p", "sparkles"),
    (".st-key-dl_video button p", "download"),
    (".st-key-video_style [role=\"radiogroup\"] > :nth-child(1) p", "clapperboard"),
    (".st-key-video_style [role=\"radiogroup\"] > :nth-child(2) p", "zap"),
    (".st-key-video_style [role=\"radiogroup\"] > :nth-child(3) p", "wand-sparkles"),
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

:root{--accent:#4F46E5;--accent-2:#7C3AED;--ink:#0F172A;--muted:#5B6B7F;--line:#E2E8F0;--soft:#EEF2FF;--bg:#F6F7FB}
::selection{background:rgba(79,70,229,.22)}
.stMain{accent-color:var(--accent)}
.stMain button:focus-visible,.stMain [role="tab"]:focus-visible,.stMain [data-testid="stRadioOption"]:has(input:focus-visible){
  outline:2px solid var(--accent);outline-offset:2px}
@media (prefers-reduced-motion:reduce){.stButton button,.stDownloadButton button{transition:none}
  .stButton button:hover,.stDownloadButton button:hover,[data-testid="stBaseButton-primary"]:hover{transform:none}}
html, body, [class*="css"], .stApp, .stMarkdown, button, input, textarea, select{
  font-family:"Inter","Segoe UI",system-ui,-apple-system,sans-serif !important}
.stApp{background:var(--bg)}

/* hide Streamlit chrome */
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stAppDeployButton"], [data-testid="stDecoration"]{display:none !important}
header[data-testid="stHeader"]{background:transparent;height:0}
.block-container{padding-top:1.6rem !important;padding-bottom:3rem !important;max-width:1280px}

/* sidebar */
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0B1120 0%,#0F172A 55%,#111C33 100%);
  border-right:1px solid rgba(255,255,255,.06);color:#E2E8F0}
[data-testid="stSidebarContent"]{padding:0 6px}
[data-testid="stSidebar"] [data-testid="stSidebarHeader"]{height:44px;min-height:0;padding-bottom:0}
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"]{padding:.6rem 1rem 1.2rem}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{gap:.9rem}
[data-testid="stSidebar"] label p{font-size:12.5px !important;font-weight:500 !important;color:#CBD5E1 !important;margin-bottom:2px}

/* sidebar section cards (containers keyed "sb_card_...") */
[data-testid="stSidebar"] [class*="st-key-sb_card_"]{background:rgba(255,255,255,.035);border:1px solid rgba(255,255,255,.08);
  border-radius:14px;padding:14px 14px 16px;gap:.7rem}

/* sidebar inputs: one consistent field style with an accent focus ring */
[data-testid="stSidebar"] [data-testid="stTextInputRootElement"],
[data-testid="stSidebar"] [data-testid="stSelectbox"] [role="group"]{background:#0A1020 !important;
  border:1px solid rgba(255,255,255,.13) !important;border-radius:10px !important;box-shadow:none !important;
  transition:border-color .15s ease,box-shadow .15s ease}
[data-testid="stSidebar"] [data-testid="stTextInputRootElement"]:hover,
[data-testid="stSidebar"] [data-testid="stSelectbox"] [role="group"]:hover{border-color:rgba(165,180,252,.45) !important}
[data-testid="stSidebar"] [data-testid="stTextInputRootElement"]:focus-within,
[data-testid="stSidebar"] [data-testid="stSelectbox"] [role="group"]:focus-within{border-color:#818CF8 !important;
  box-shadow:0 0 0 3px rgba(129,140,248,.22) !important}
[data-testid="stSidebar"] input{background:transparent !important;border:0 !important;outline:0 !important;box-shadow:none !important;
  color:#F1F5F9 !important;font-size:14px}
[data-testid="stSidebar"] [data-testid="stSelectbox"] [role="group"] button{background:transparent !important;border:0 !important;
  color:#94A3B8 !important}
[data-testid="stSidebar"] [data-testid="stSelectbox"] [role="group"] button svg{fill:currentColor}

/* colour picker -> full-width swatch bar */
[data-testid="stSidebar"] [data-testid="stElementContainer"]:has([data-testid="stColorPicker"]){width:100% !important}
[data-testid="stSidebar"] [data-testid="stColorPicker"]{width:100% !important}
[data-testid="stSidebar"] [data-testid="stColorPicker"] > div, [data-testid="stSidebar"] [data-testid="stColorPicker"] > button{width:100% !important}
[data-testid="stSidebar"] [data-testid="stColorPicker"] button{width:100% !important;height:40px !important;padding:3px !important;
  background:#0A1020 !important;border:1px solid rgba(255,255,255,.13) !important;border-radius:10px !important;
  transition:border-color .15s ease}
[data-testid="stSidebar"] [data-testid="stColorPicker"] button:hover{border-color:rgba(165,180,252,.45) !important}
[data-testid="stSidebar"] [data-testid="stColorPickerBlock"]{width:100% !important;height:100% !important;border-radius:7px !important}

/* sidebar buttons */
[data-testid="stSidebar"] .stButton button{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.14);
  color:#F1F5F9;min-height:40px}
[data-testid="stSidebar"] .stButton button:hover{border-color:#818CF8;color:#fff;background:rgba(129,140,248,.14)}
[data-testid="stSidebar"] .stButton button:focus-visible{outline:0;box-shadow:0 0 0 3px rgba(129,140,248,.3)}

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
.hero h1{text-wrap:balance;font-size:34px !important;line-height:1.15;font-weight:800 !important;margin:14px 0 8px !important;color:#fff !important;
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
.hero .feat svg{flex:none}
.hero-top{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.hero-top > svg{flex:none;filter:drop-shadow(0 6px 14px rgba(15,23,42,.45))}
.hero-brand{font-weight:800;font-size:17px;letter-spacing:-.01em;color:#fff;margin-right:4px}
.page-foot{display:flex;align-items:center;justify-content:center;gap:10px;margin-top:40px;padding-top:20px;
  border-top:1px solid var(--line);font-size:12.5px;color:var(--muted)}
.page-foot b{color:#334155;font-weight:700}

.banner{border-radius:14px;padding:14px 18px;display:flex;gap:12px;align-items:flex-start;font-size:14px;margin:6px 0 12px}
.banner .ic{display:flex;flex:none;margin-top:1px}
.banner b{display:block;margin-bottom:2px}
.banner.ok{background:#ECFDF5;border:1px solid #A7F3D0;color:#065F46}
.banner.warn{background:#FFFBEB;border:1px solid #FDE68A;color:#92400E}
.banner.err{background:#FEF2F2;border:1px solid #FECACA;color:#991B1B}
.banner.info{background:var(--soft);border:1px solid #C7D2FE;color:#3730A3}
.banner ul{margin:6px 0 0 0;padding-left:18px}.banner li{margin-bottom:4px}

.results-head{display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:12px;margin:26px 0 12px}
.results-head .t{font-size:24px;font-weight:800;color:var(--ink);text-wrap:balance}
.results-head .s{font-size:14px;color:var(--muted)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-bottom:14px}
.stat{background:#fff;border:1px solid var(--line);border-radius:14px;padding:14px 16px}
.stat .v{font-size:22px;font-weight:800;color:var(--ink);font-variant-numeric:tabular-nums}
.stat .l{font-size:12.5px;color:var(--muted);margin-top:2px}
.stat.good .v{color:#059669}.stat.bad .v{color:#DC2626}


.empty{background:#fff;border:1px dashed #CBD5E1;border-radius:18px;padding:34px;text-align:center;color:var(--muted);margin-top:22px}
.empty .big svg{display:block;margin:0 auto 4px}.empty .t{font-size:16px;font-weight:700;color:#334155;margin-top:6px}

.sb-brand{display:flex;align-items:center;gap:12px;padding-bottom:16px;margin-bottom:16px;border-bottom:1px solid rgba(255,255,255,.08)}
.sb-logo{width:44px;height:44px;display:flex;flex:none;align-items:center;justify-content:center;
  filter:drop-shadow(0 6px 14px rgba(129,140,248,.35))}
.sb-name{font-weight:800;font-size:15.5px;color:#fff;line-height:1.2;letter-spacing:-.01em}
.sb-sub{font-size:12px;color:#94A3B8;margin-top:2px}
.sb-title{display:flex;align-items:center;gap:8px;font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:#A5B4FC;
  font-weight:700;margin:0 0 8px}
.sb-title svg{flex:none;opacity:.9}
.sb-title.plain{color:#94A3B8;margin:2px 0 12px}
.sb-steps{position:relative;display:flex;flex-direction:column;gap:14px;margin-bottom:18px}
.sb-steps:before{content:"";position:absolute;left:11px;top:14px;bottom:14px;width:1px;background:rgba(165,180,252,.25)}
.sb-step{position:relative;display:flex;gap:12px;align-items:flex-start;font-size:13px;line-height:1.45;color:#CBD5E1}
.sb-step .n{width:23px;height:23px;border-radius:50%;background:#1E1B4B;border:1px solid #4F46E5;color:#C7D2FE;
  font-size:11px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0;z-index:1}
.sb-foot{margin-top:6px;padding-top:16px;border-top:1px solid rgba(255,255,255,.08);display:flex;flex-direction:column;gap:9px}
.sb-foot div{display:flex;gap:8px;align-items:flex-start;font-size:12px;line-height:1.45;color:#8B9AB3}
.sb-foot svg{flex:none;margin-top:2px;color:#A5B4FC}
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
  <div class="hero-top">{logo_mark(46, "#1B2440")}<span class="hero-brand">Testimonial Studio</span></div>
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


_logo_ids = itertools.count(1)


def logo_mark(size: int = 40, fill: str = "#0F172A") -> str:
    """The Testimonial Studio mark (same artwork as assets/logo-mark.svg), inline so it needs no file serving."""
    gid = f"tsg{next(_logo_ids)}"   # unique per copy: several marks can share one page
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 64 64" role="img" '
            f'aria-label="Testimonial Studio"><defs><linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="#818CF8"/><stop offset="1" stop-color="#C084FC"/></linearGradient></defs>'
            f'<path d="M32 3l25 14.5v29L32 61 7 46.5v-29z" fill="{fill}" stroke="url(#{gid})" stroke-width="2.5" '
            f'stroke-linejoin="round"/><rect x="18" y="19" width="28" height="7" rx="3.5" fill="#fff"/>'
            f'<rect x="28.5" y="19" width="7" height="27" rx="3.5" fill="#fff"/><circle cx="45" cy="44" r="5" fill="#F59E0B"/></svg>')


def sidebar_brand() -> None:
    st.markdown(
        f"""
<div class="sb-brand"><div class="sb-logo">{logo_mark(44, "#1B2440")}</div>
  <div><div class="sb-name">Testimonial Studio</div><div class="sb-sub">Case studies from client feedback</div></div></div>
<div class="sb-title plain">How it works</div>
<div class="sb-steps">
  <div class="sb-step"><span class="n">1</span><span>Add feedback: notes, a file, a recording or a link</span></div>
  <div class="sb-step"><span class="n">2</span><span>Fill in the project details</span></div>
  <div class="sb-step"><span class="n">3</span><span>Generate, review the fact check, export</span></div>
</div>""",
        unsafe_allow_html=True,
    )


def sidebar_title(text: str, icon: str | None = None) -> None:
    badge = svg(icon, 14) if icon else ""
    st.markdown(f'<div class="sb-title">{badge}{_e(text)}</div>', unsafe_allow_html=True)


def sidebar_footer() -> None:
    st.markdown(
        f'<div class="sb-foot"><div>{svg("zap", 14)}<span>Powered by Groq and ElevenLabs Scribe</span></div>'
        f'<div>{svg("shield-check", 14)}<span>Always get client approval before publishing.</span></div></div>',
        unsafe_allow_html=True)


def empty_state() -> None:
    st.markdown(
        f"""<div class="empty"><div class="big">{logo_mark(64)}</div><div class="t">Your content will appear here</div>
        <div>Add client feedback, fill in the project details and click <b>Generate content</b>.</div></div>""",
        unsafe_allow_html=True,
    )


def page_footer() -> None:
    st.markdown(f'<div class="page-foot">{logo_mark(22)}<span><b>Testimonial Studio</b> · '
                f'Case studies from client feedback · Always get client approval before publishing.</span></div>',
                unsafe_allow_html=True)


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

