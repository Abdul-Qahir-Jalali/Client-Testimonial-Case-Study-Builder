"""Testimonials tab: a featured quote, filter chips and copy buttons (front end only).

Rendered as a self-contained page for components.html (so it can use a little JavaScript for filtering and
copy-to-clipboard). Everything coming from the model is HTML-escaped; the quotes are never inserted as markup.
"""

from __future__ import annotations

import html
import math
import re

from case_study_view import _initials
from icons import svg

LENGTHS = ("short", "medium", "long")


def _e(text) -> str:
    return html.escape(str(text or ""), quote=True)


def _safe_color(accent: str) -> str:
    return accent if re.fullmatch(r"#[0-9a-fA-F]{3,8}", accent or "") else "#4F46E5"


def _words(q: dict) -> int:
    return len(str(q.get("text", "")).split())


def _copy_text(q: dict, company: str) -> str:
    who = ", ".join(x for x in [q.get("speaker_name"), q.get("speaker_role"), company] if x)
    return f"“{str(q.get('text', '')).strip()}”" + (f" - {who}" if who else "")


def _card(q: dict, company: str, featured: bool) -> str:
    length = str(q.get("length", "medium")).lower()
    length = length if length in LENGTHS else "medium"
    theme = f'<span class="tag">{_e(q.get("theme"))}</span>' if q.get("theme") else ""
    role = ", ".join(x for x in [q.get("speaker_role"), company] if x)
    badge = f'<span class="tag feat-tag">{svg("sparkles", 12)} Featured</span>' if featured else ""
    return (
        f'<article class="card {length}{" feat" if featured else ""}" data-length="{length}" '
        f'data-copy="{_e(_copy_text(q, company))}">'
        f'<span class="qicon">{svg("quote", 30 if featured else 24)}</span>'
        f'<div class="meta">{badge}<span class="tag len"><i></i>{_e(length.title())}</span>{theme}'
        f'<span class="tag">{_words(q)} words</span></div>'
        f'<p class="q">{_e(q.get("text"))}</p>'
        f'<div class="who"><div class="avatar">{_e(_initials(q.get("speaker_name")))}</div>'
        f'<div class="id"><div class="n">{_e(q.get("speaker_name"))}</div><div class="r">{_e(role)}</div></div>'
        f'<button class="copy" type="button">{svg("copy", 14)}<span>Copy</span></button></div></article>'
    )


def estimate_height(quotes: list[dict]) -> int:
    """Initial iframe height; the page resizes itself to its real content once it loads."""
    rest = max(len(quotes) - 1, 0)
    return 80 + (300 if quotes else 0) + math.ceil(rest / 2) * 250


TEMPLATE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root{--accent:__ACCENT__;--ink:#0F172A;--muted:#64748B;--line:#E2E8F0;--soft:#EEF2FF}
*{box-sizing:border-box}
html,body{margin:0;background:transparent}
body{font-family:Inter,"Segoe UI",system-ui,sans-serif;color:var(--ink);padding:4px 2px 10px;-webkit-font-smoothing:antialiased}
svg.lucide{display:block;flex:none}

.bar{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;margin:0 0 16px}
.chips{display:flex;gap:8px;flex-wrap:wrap}
.chip{display:inline-flex;align-items:center;gap:8px;border:1px solid var(--line);background:#fff;color:#475569;border-radius:999px;
  padding:7px 8px 7px 15px;font:600 13px Inter,sans-serif;cursor:pointer;transition:all .15s ease}
.chip .n{min-width:22px;text-align:center;background:#F1F5F9;border-radius:999px;padding:1px 7px;font-size:11.5px;color:#475569}
.chip:hover{border-color:#C7D2FE}
.chip.on{background:var(--soft);border-color:var(--accent);color:var(--accent);box-shadow:0 0 0 1px var(--accent) inset}
.chip.on .n{background:#fff;color:var(--accent)}
.btn{display:inline-flex;align-items:center;gap:8px;border:1px solid var(--line);background:#fff;color:var(--ink);border-radius:10px;
  padding:8px 14px;font:600 13px Inter,sans-serif;cursor:pointer;transition:all .15s ease}
.btn:hover{border-color:var(--accent);color:var(--accent)}
.btn.done{color:#047857;border-color:#A7F3D0;background:#ECFDF5}

.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:16px}
.card{position:relative;display:flex;flex-direction:column;gap:16px;background:#fff;border:1px solid var(--line);border-radius:18px;
  padding:26px 24px 18px;box-shadow:0 1px 2px rgba(15,23,42,.04);transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease}
.card:hover{transform:translateY(-2px);border-color:#C7D2FE;box-shadow:0 12px 28px rgba(15,23,42,.08)}
.card:before{content:"";position:absolute;left:24px;top:0;width:44px;height:4px;border-radius:0 0 4px 4px;background:var(--tone)}
.card.short{--tone:#10B981}.card.medium{--tone:#3B82F6}.card.long{--tone:#8B5CF6}
.qicon{position:absolute;right:20px;top:20px;color:#E0E7FF}
.meta{display:flex;flex-wrap:wrap;gap:6px;padding-right:34px}
.tag{display:inline-flex;align-items:center;gap:6px;font-size:11.5px;font-weight:600;padding:3px 10px;border-radius:999px;background:#F1F5F9;color:#475569}
.tag.len i{width:7px;height:7px;border-radius:50%;background:var(--tone)}
.q{margin:0;flex:1;font-size:16.5px;line-height:1.65;color:#1E293B;font-weight:450}
.who{display:flex;align-items:center;gap:12px;border-top:1px solid #F1F5F9;padding-top:14px}
.avatar{width:38px;height:38px;border-radius:50%;background:linear-gradient(135deg,var(--accent),#7C3AED);color:#fff;font-weight:700;font-size:13px;
  display:flex;align-items:center;justify-content:center;flex:none}
.id{min-width:0;flex:1}.id .n{font-size:14px;font-weight:700;color:var(--ink)}.id .r{font-size:12.5px;color:var(--muted);margin-top:1px}
.copy{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--line);background:#fff;color:#475569;border-radius:9px;
  padding:6px 11px;font:600 12px Inter,sans-serif;cursor:pointer;transition:all .15s ease;flex:none}
.copy:hover{border-color:var(--accent);color:var(--accent);background:var(--soft)}
.copy.done{color:#047857;border-color:#A7F3D0;background:#ECFDF5}

.card.feat{grid-column:1/-1;border:0;padding:34px 36px 22px;color:#fff;
  background:radial-gradient(900px 300px at 90% -30%,rgba(168,85,247,.55),transparent 60%),linear-gradient(135deg,#1E1B4B 0%,#312E81 50%,#4F46E5 100%)}
.card.feat:before{background:#F59E0B;left:36px;width:56px}
.card.feat .qicon{color:rgba(255,255,255,.2);right:30px;top:28px}
.card.feat .q{font-size:23px;line-height:1.55;font-weight:500;color:#fff;letter-spacing:-.005em}
.card.feat .tag{background:rgba(255,255,255,.14);color:#E0E7FF}
.card.feat .feat-tag{background:#F59E0B;color:#1E1B4B}
.card.feat .who{border-top-color:rgba(255,255,255,.18)}
.card.feat .id .n{color:#fff}.card.feat .id .r{color:#C7D2FE}
.card.feat .avatar{background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.3)}
.card.feat .copy{background:rgba(255,255,255,.1);border-color:rgba(255,255,255,.3);color:#fff}
.card.feat .copy:hover{background:rgba(255,255,255,.2);border-color:#fff}
.card.feat .copy.done{background:#ECFDF5;color:#047857;border-color:#A7F3D0}
.empty{display:none;text-align:center;color:var(--muted);padding:34px;border:1px dashed #CBD5E1;border-radius:16px;background:#fff;font-size:14px}
@media (max-width:640px){.grid{grid-template-columns:1fr}.card.feat .q{font-size:19px}}
</style></head><body>
<div class="bar">
  <div class="chips" id="chips">__CHIPS__</div>
  <button class="btn" id="copyall" type="button">__ICO_COPY__<span>Copy all</span></button>
</div>
<div class="grid" id="grid">__CARDS__</div>
<div class="empty" id="empty">No testimonials of this length.</div>
<script>
const grid=document.getElementById('grid'), cards=[...grid.querySelectorAll('.card')], empty=document.getElementById('empty');
function resize(){   // body, not documentElement: scrollHeight never drops below the iframe's current height
  try{ const h=(Math.ceil(document.body.getBoundingClientRect().height)+8)+'px', f=window.frameElement;
    f.style.height=h; f.parentElement.style.height=h; f.parentElement.style.flexBasis=h;   // Streamlit pins the wrapper (flex-basis) to the initial height estimate
  }catch(e){} }
function copyText(t){
  const fallback=()=>new Promise((res,rej)=>{ const a=document.createElement('textarea'); a.value=t; a.style.cssText='position:fixed;opacity:0';
    document.body.appendChild(a); a.select(); try{ document.execCommand('copy') ? res() : rej(); }catch(e){ rej(); } finally{ a.remove(); } });
  if(navigator.clipboard && window.isSecureContext){ return navigator.clipboard.writeText(t).catch(fallback); }
  return fallback();
}
function flash(btn, label){ const s=btn.querySelector('span'), old=s.textContent; btn.classList.add('done'); s.textContent=label;
  setTimeout(()=>{ btn.classList.remove('done'); s.textContent=old; }, 1600); }
function copyWith(btn, text){ copyText(text).then(()=>flash(btn,'Copied'), ()=>flash(btn,'Copy failed')); }   // btn captured up front: event.currentTarget is null once the handler returns
cards.forEach(c=>{ const btn=c.querySelector('.copy'); btn.addEventListener('click',()=>copyWith(btn, c.dataset.copy)); });
const all=document.getElementById('copyall');
all.addEventListener('click',()=>{ const vis=cards.filter(c=>c.style.display!=='none'); copyWith(all, vis.map(c=>c.dataset.copy).join('\\n\\n')); });
document.getElementById('chips').addEventListener('click',e=>{ const b=e.target.closest('.chip'); if(!b) return;
  document.querySelectorAll('.chip').forEach(x=>x.classList.toggle('on', x===b)); const f=b.dataset.f; let n=0;
  cards.forEach(c=>{ const show=(f==='all'||c.dataset.length===f); c.style.display=show?'':'none'; if(show) n++; });
  empty.style.display=n?'none':'block'; resize(); });
window.addEventListener('load',resize); new ResizeObserver(resize).observe(document.body);
</script></body></html>"""


def render_testimonials_html(quotes: list[dict], company: str, accent: str = "#4F46E5") -> str:
    # The most developed quote leads as the featured card (only worth doing when there are several to compare).
    ordered = sorted(quotes, key=_words, reverse=True) if len(quotes) >= 3 else list(quotes)
    cards = "".join(_card(q, company, featured=(i == 0 and len(quotes) >= 3)) for i, q in enumerate(ordered))
    counts = {k: sum(1 for q in quotes if str(q.get("length", "medium")).lower() == k) for k in LENGTHS}
    chips = [f'<button class="chip on" data-f="all" type="button">All <span class="n">{len(quotes)}</span></button>']
    chips += [f'<button class="chip" data-f="{k}" type="button">{k.title()} <span class="n">{n}</span></button>'
              for k, n in counts.items() if n]
    return (TEMPLATE.replace("__ACCENT__", _safe_color(accent))
            .replace("__CHIPS__", "".join(chips)).replace("__CARDS__", cards)
            .replace("__ICO_COPY__", svg("copy", 15)))
