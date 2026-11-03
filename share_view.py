"""One-click share buttons for the Share tab.

Rendered as a small self-contained page (components.html) because a Streamlit button cannot write to the
clipboard or open a new tab. Click = copy the text, then open the platform's upload page.
"""

from __future__ import annotations

import json

from icons import svg

CSS = """
*{box-sizing:border-box}
html,body{margin:0;background:transparent;font-family:"Source Sans 3","Segoe UI",system-ui,-apple-system,sans-serif}
.row{display:flex;flex-wrap:wrap;align-items:center;gap:10px;padding:4px 2px 6px}
button{font:inherit;font-weight:600;font-size:15px;line-height:1;display:inline-flex;align-items:center;gap:8px;
  border-radius:10px;padding:0 18px;min-height:44px;cursor:pointer;transition:transform .15s cubic-bezier(.22,1,.36,1),
  box-shadow .15s,background .15s,border-color .15s}
button svg{flex:none}
button:active{transform:translateY(1px)}
button:focus-visible{outline:0;box-shadow:0 0 0 3px rgba(99,102,241,.35)}
.go{color:#fff;border:0;background:linear-gradient(135deg,#4F46E5,#7C3AED);box-shadow:0 6px 16px rgba(79,70,229,.28)}
.go:hover{box-shadow:0 8px 20px rgba(79,70,229,.36)}
.alt{color:#4338CA;background:#fff;border:1px solid #C7D2FE}
.alt:hover{background:#EEF2FF;border-color:#818CF8}
.msg{font-size:13.5px;color:#475569;display:flex;align-items:center;gap:6px;min-height:20px}
.msg.ok{color:#047857}
.msg svg{flex:none}
"""

JS = """
const MSG = document.getElementById('msg');
function say(text, ok){
  MSG.className = 'msg' + (ok ? ' ok' : '');
  MSG.innerHTML = (ok ? OK_ICON : '') + '<span></span>';
  MSG.lastChild.textContent = text;
}
function syncCopy(text){
  const ta = document.createElement('textarea');
  ta.value = text; ta.setAttribute('readonly', '');
  ta.style.cssText = 'position:fixed;top:0;left:0;opacity:0';
  document.body.appendChild(ta); ta.select();
  let done = false;
  try { done = document.execCommand('copy'); } catch (e) {}
  document.body.removeChild(ta);
  return done;
}
function copyText(text){
  if (syncCopy(text)) return Promise.resolve();
  if (navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(text);
  return Promise.reject(new Error('no clipboard'));
}
function run(btn){
  const text = btn.dataset.text, url = btn.dataset.url, what = btn.dataset.what;
  copyText(text).then(
    () => say(url ? what + ' copied. Paste it on the page that just opened, then add your video.' : what + ' copied.', true),
    () => say('Could not copy automatically. Select the text in the box above and copy it by hand.', false));
  if (url) window.open(url, '_blank', 'noopener');
}
document.querySelectorAll('button').forEach(b => b.addEventListener('click', () => run(b)));
function resize(){   // wrapped buttons and the status line must never be clipped on narrow windows
  try { const h = (Math.ceil(document.body.getBoundingClientRect().height) + 8) + 'px', f = window.frameElement;
    f.style.height = h; f.parentElement.style.height = h; f.parentElement.style.flexBasis = h;
  } catch (e) {}
}
window.addEventListener('load', resize); new ResizeObserver(resize).observe(document.body);
"""


def post_buttons_html(label: str, icon: str, text: str, url: str, extras: list[tuple[str, str, str]] | None = None) -> str:
    """`extras` are (label, text, what-was-copied) secondary buttons that only copy (e.g. the YouTube title)."""
    def attr(value: str) -> str:
        return (value.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;"))

    main = (f'<button class="go" data-text="{attr(text)}" data-url="{attr(url)}" data-what="Caption">'
            f'{svg(icon, 18)}<span>{attr(label)}</span>{svg("external-link", 16)}</button>')
    more = "".join(f'<button class="alt" data-text="{attr(t)}" data-url="" data-what="{attr(w)}">'
                   f'{svg("copy", 16)}<span>{attr(l)}</span></button>' for l, t, w in (extras or []))
    ok_icon = json.dumps(svg("circle-check", 16))
    return (f"<style>{CSS}</style><div class='row'>{main}{more}<div id='msg' class='msg'>"
            f"{svg('info', 16)}<span>Copies your caption, then opens the page.</span></div></div>"
            f"<script>const OK_ICON={ok_icon};{JS}</script>")
