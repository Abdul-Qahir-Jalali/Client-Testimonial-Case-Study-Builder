"""Streamlit UI.  Run with:  streamlit run app.py"""

import hashlib
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from generator import (
    BASE_DIR,
    GenerationError,
    ProjectDetails,
    generate,
    is_configured,
    parse_input_file,
    parse_input_text,
    save_markdown,
    slugify,
)
import ui
from case_study_view import render_case_study_html
import ai_video
import share_view
import social
import video_maker
from story_view import render_story_html
from testimonial_view import estimate_height, render_testimonials_html
from transcribe import (
    MEDIA_TYPES,
    TranscriptionError,
    default_label,
    format_transcript,
    is_video,
    transcribe_audio,
    transcribe_url,
)
from transcribe import is_configured as transcription_ready

st.set_page_config(page_title="Testimonial & Case Study Builder", page_icon=str(BASE_DIR / "favicon.svg"),
                   layout="wide", initial_sidebar_state="expanded")
ui.inject_css()

SAMPLES = {p.stem.replace("_", " ").title(): p for p in sorted((BASE_DIR / "samples").glob("*.txt"))}
DETAIL_FIELDS = [
    ("client_name", "Client company"),
    ("contact_name", "Contact name"),
    ("contact_role", "Contact role"),
    ("industry", "Industry"),
    ("service", "Service delivered"),
    ("timeline", "Timeline"),
]
INPUT_MODES = ["Type / paste text", "Upload text file", "Audio / video"]   # icons: ui.WIDGET_ICONS
SOURCES = ["Upload a file", "Paste a link"]
CS_VIEWS = ["Story", "Full page"]
MD_VIEWS = ["Preview", "Source"]
ROLES = ["Client", "Interviewer"]
VIDEO_STYLES = ["Animated slides", "AI-generated film"]

for key, _ in DETAIL_FIELDS:
    st.session_state.setdefault(key, "")
st.session_state.setdefault("notes", "")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def apply_details(meta: dict) -> None:
    """Fill project-detail fields from a file's front-matter (only fields it provides)."""
    for key, _ in DETAIL_FIELDS:
        if meta.get(key):
            st.session_state[key] = meta[key]


def load_sample(name: str) -> None:
    if name == "— none —":
        return
    notes, meta = parse_input_file(SAMPLES[name])
    st.session_state["notes"] = notes
    for key, _ in DETAIL_FIELDS:
        st.session_state[key] = meta.get(key, "")


def fmt_duration(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d} min" if m else f"{s} sec"


def video_section(content: dict, details: ProjectDetails, accent: str) -> None:
    """Tab 4: short vertical video (9:16) for TikTok / Reels / Shorts."""
    style = st.radio("Video style", VIDEO_STYLES, horizontal=True, label_visibility="collapsed", key="video_style")
    voice = st.checkbox("Add a voiceover", value=True, key="video_voice",
                        disabled=not video_maker.voiceover_available(),
                        help="Free text-to-speech (edge-tts). Needs an internet connection; "
                             "if it fails, the video is made without sound.")
    use_ai = style == VIDEO_STYLES[1]
    if use_ai:
        ui.note("Free AI makes a short cinematic film of the client's story from prompts: a storyboard, then each "
                "shot is generated and animated (Wan 2.2 on Hugging Face). Expect 3-6 minutes. Your real, "
                "fact-checked numbers appear on a results card, never in AI-made footage. "
                "Only scene descriptions (client names removed) are sent to the free AI services. "
                "An optional free HF_TOKEN in .env raises the daily limit.", "wand-sparkles")
    else:
        ui.note("Branded animated slides built from your fact-checked numbers and best quote. Works offline, "
                "usually under a minute.", "clapperboard")

    if st.button("Create video", type="primary", use_container_width=True, key="btn_video"):
        shots = None
        if use_ai:
            bar = st.progress(0.0, text="Starting...")
            try:
                shots = ai_video.generate_film(content, details, lambda f, m: bar.progress(f, text=m))
            except ai_video.AIVideoError as exc:
                ui.banner("warn", "AI video unavailable - made the animated-slides version instead", str(exc))
            bar.empty()
        try:
            with st.spinner("Rendering the video..."):
                if shots:
                    try:
                        path = video_maker.render_ai_film(shots, content, details, accent, voice=voice)
                    finally:
                        ai_video.cleanup(shots)     # the downloaded shots are only needed for this render
                else:
                    path = video_maker.render_video(content, details, accent, voice=voice)
            st.session_state["video"] = {"path": str(path), "ai": bool(shots)}
        except video_maker.VideoError as exc:
            ui.banner("err", "Could not create the video", str(exc))

    saved = st.session_state.get("video")
    if saved and Path(saved["path"]).exists():
        left, mid, right = st.columns([1, 1, 1])
        mid.video(saved["path"])
        data = Path(saved["path"]).read_bytes()
        mid.download_button("Download video (MP4)", data, file_name=Path(saved["path"]).name, mime="video/mp4",
                            use_container_width=True, type="primary", key="dl_video")
        ui.note("1080x1920 MP4, ready for TikTok, Instagram Reels and YouTube Shorts. Saved in the output/ folder.", "video")


def share_section(content: dict, details: ProjectDetails) -> None:
    """Tab 5: captions + hashtags per platform, and one button each that copies the caption and opens the upload page."""
    ui.banner("info", "Get the client's approval before posting",
              "Check the captions and the video with them first. Nothing is posted by this app: each button copies "
              "the caption and opens that platform's upload page, where you attach the video and press Post.",
              icon="shield-check")

    video = st.session_state.get("video")
    video_path = Path(video["path"]) if video and Path(video["path"]).exists() else None
    with st.container(border=True, key="card_share_opts"):
        left, right = st.columns([1, 3], gap="large")
        with left:
            if video_path:
                st.video(str(video_path))
                st.download_button("Download video", video_path.read_bytes(), file_name=video_path.name,
                                   mime="video/mp4", use_container_width=True, key="dl_video_share")
            else:
                ui.note("No video yet. Create one in the Video tab, then download it here.", "video")
        with right:
            ui.section_head("wand-sparkles", "Write the captions", "One tailored post per platform, hashtags included")
            c1, c2 = st.columns([1, 2])
            tone = c1.selectbox("Tone", social.TONES, key="share_tone")
            link = c2.text_input("Link to include (optional)", key="share_link",
                                 placeholder="https://your-site.com/case-study")
            emojis = st.toggle("Use a few emojis", value=True, key="share_emoji")
            if st.button("Rewrite captions" if st.session_state.get("social") else "Write captions",
                         type="primary", use_container_width=True, key="btn_captions"):
                with st.spinner("Writing captions and checking every number against the case study..."):
                    posts, warnings, used_ai = social.write_posts(content, details, tone=tone, emojis=emojis, link=link)
                for key, post in posts.items():
                    st.session_state[f"share_cap_{key}"] = post.caption
                    st.session_state[f"share_tags_{key}"] = " ".join(post.hashtags)
                    if key == "youtube":
                        st.session_state["share_title_youtube"] = post.title
                st.session_state["social"] = {"warnings": warnings, "ai": used_ai}

    state = st.session_state.get("social")
    if not state:
        return
    if not state["ai"]:
        ui.banner("info", "These captions come from a template",
                  "Add a Groq key to .env for captions written specifically for each platform.")
    if state["warnings"]:
        ui.banner("warn", "Check these numbers before posting", items=state["warnings"], icon="search-check")

    for p in social.PLATFORMS:
        with st.container(border=True, key=f"card_share_{p.key}"):
            ui.section_head(p.icon, p.name, p.spec)
            if p.key == "youtube":
                st.text_input("Title", key="share_title_youtube", max_chars=social.TITLE_LIMIT)
            st.text_area("Caption", key=f"share_cap_{p.key}", height=260 if p.key == "linkedin" else 170)
            st.text_input("Hashtags", key=f"share_tags_{p.key}")
            text = social.compose(st.session_state.get(f"share_cap_{p.key}", ""),
                                  st.session_state.get(f"share_tags_{p.key}", ""))
            if len(text) > p.limit:
                ui.banner("warn", f"{len(text):,} characters: {p.name} allows {p.limit:,}", "Shorten the caption or hashtags.")
            else:
                ui.note(f"{len(text):,} of {p.limit:,} characters", "hash")
            extras = [("Copy title", st.session_state.get("share_title_youtube", ""), "Title")] if p.key == "youtube" else []
            components.html(share_view.post_buttons_html(p.open_label, p.icon, text, social.open_url(p, text), extras),
                            height=64)
            ui.note(p.tips, "lightbulb")


def use_transcript(file_id: str) -> None:
    """Button callback: turn the named transcript into notes text."""
    transcript = st.session_state["transcript"]["data"]
    names, interviewers = {}, set()
    for spk in transcript.speakers:
        names[spk] = st.session_state.get(f"spk_name_{file_id}_{spk}", "")
        if st.session_state.get(f"spk_role_{file_id}_{spk}", ROLES[0]) != ROLES[0]:
            interviewers.add(spk)
    st.session_state["notes"] = format_transcript(transcript, names, interviewers)
    st.session_state["transcript_used"] = file_id


# --------------------------------------------------------------------------- #
# Input sections
# --------------------------------------------------------------------------- #
def text_file_section() -> None:
    uploaded = st.file_uploader("Drag and drop a .txt or .md file, or click to browse",
                                type=["txt", "md"], key="text_file")
    if uploaded is None:
        return
    file_id = hashlib.md5(uploaded.getvalue()).hexdigest()
    if st.session_state.get("_last_text_file") != file_id:  # load each file only once
        notes, meta = parse_input_text(uploaded.getvalue().decode("utf-8", errors="ignore"))
        st.session_state["notes"] = notes
        apply_details(meta)
        st.session_state["_last_text_file"] = file_id
    ui.banner("ok", f"Loaded {uploaded.name}", "The text is in the notes box below. Project details from the file header were filled in.")


SPEAKER_CHOICES = ["Auto-detect", 1, 2, 3, 4, 5, 6]


def _speakers_value(choice) -> int | None:
    return None if choice == "Auto-detect" else int(choice)


def _run_transcription(source_id: str, label: str, job) -> None:
    """Run a transcription job and remember the result for this source."""
    try:
        with st.spinner(label):
            transcript = job()
        st.session_state["transcript"] = {"id": source_id, "data": transcript}
    except TranscriptionError as exc:
        ui.banner("err", "Transcription failed", str(exc))


def media_section() -> None:
    if not transcription_ready():
        ui.banner("warn", "ElevenLabs API key needed",
                  "Add ELEVENLABS_API_KEY to the .env file and restart the app to transcribe audio, video or links.")

    source = st.radio("Source", SOURCES, horizontal=True,
                      label_visibility="collapsed", key="media_source")

    if source == SOURCES[0]:
        media = st.file_uploader("Drag and drop an interview recording (audio or video), or click to browse",
                                 type=MEDIA_TYPES, key="media_file",
                                 help="Audio: mp3, wav, m4a, ogg, flac, aac, opus, wma. "
                                      "Video: mp4, mov, mkv, avi, webm, wmv, flv, m4v, 3gp, mpeg. "
                                      "For video, only the audio track is extracted and sent.")
        if media is None:
            return
        data = media.getvalue()
        source_id = "file:" + hashlib.md5(data).hexdigest()
        video = is_video(media.name)
        if video:
            st.video(data)
        else:
            st.audio(data, format=media.type or "audio/mpeg")

        c1, c2 = st.columns(2)
        speakers = c1.selectbox("Number of speakers", SPEAKER_CHOICES, key="n_spk_file",
                                help="Set this if you know it - it makes speaker detection more accurate.")
        c2.write("")
        if c2.button("Transcribe", use_container_width=True, disabled=not transcription_ready(),
                     key="btn_transcribe"):
            label = ("Extracting audio from the video, then transcribing..." if video
                     else "Transcribing... long recordings can take a minute or two.")
            _run_transcription(source_id, label,
                               lambda: transcribe_audio(data, media.name, _speakers_value(speakers)))
    else:
        url = st.text_input("Video or audio link", key="media_url",
                            placeholder="https://www.youtube.com/watch?v=...  ·  TikTok  ·  Google Drive  ·  Dropbox  ·  direct .mp4/.mp3 link")
        st.caption("The link must be public. ElevenLabs downloads the media itself, so nothing is downloaded "
                   "to this computer. Only use recordings you have permission to transcribe.")
        if not url.strip():
            return
        source_id = "url:" + url.strip()
        c1, c2 = st.columns(2)
        speakers = c1.selectbox("Number of speakers", SPEAKER_CHOICES, key="n_spk_url")
        c2.write("")
        if c2.button("Transcribe from link", use_container_width=True, disabled=not transcription_ready(),
                     key="btn_transcribe_url"):
            _run_transcription(source_id, "Fetching the media and transcribing... this can take a few minutes for long videos.",
                               lambda: transcribe_url(url, _speakers_value(speakers)))

    speaker_naming(source_id)


def speaker_naming(source_id: str) -> None:
    """After transcription: let the user name speakers and mark the interviewer."""
    saved = st.session_state.get("transcript")
    if not saved or saved["id"] != source_id:
        return
    file_id = hashlib.md5(source_id.encode()).hexdigest()[:12]  # short, widget-safe key

    transcript = saved["data"]
    lang = f" · language: {transcript.language}" if transcript.language else ""
    ui.banner("ok", "Transcription complete",
              f"{fmt_duration(transcript.duration)} of audio · {len(transcript.speakers)} speaker(s) detected{lang}")
    ui.section_head("users", "Who is who?", "Name each speaker and mark the interviewer (your team). Client names are used to credit quotes.")
    stats = transcript.stats()
    multi = len(transcript.speakers) > 1
    for i, spk in enumerate(transcript.speakers):
        info = stats[spk]
        with st.container(border=True, key=f"card_spk_{file_id}_{spk}"):
            sample = info["sample"] if len(info["sample"]) <= 160 else info["sample"][:157] + "..."
            st.caption(f"**{default_label(i)}** · {info['share']}% of the talking · e.g. “{sample}”")
            n, r = st.columns([3, 2])
            n.text_input("Name", key=f"spk_name_{file_id}_{spk}", placeholder=f"{default_label(i)} - type a name",
                         label_visibility="collapsed")
            r.selectbox("Role", ROLES, index=1 if (multi and i == 0) else 0,
                        key=f"spk_role_{file_id}_{spk}", label_visibility="collapsed")

    st.button("Use this transcript", type="primary", use_container_width=True,
              on_click=use_transcript, args=(file_id,), key="btn_use_transcript")
    if st.session_state.get("transcript_used") == file_id:
        ui.banner("info", "Transcript added to the notes box below",
                  "Check it, fill in the project details, then click Generate content.")


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
with st.sidebar:
    ui.sidebar_brand()
    with st.container(key="sb_card_sample"):
        ui.sidebar_title("Try a sample", "flask-conical")
        choice = st.selectbox("Sample input", ["— none —", *SAMPLES], label_visibility="collapsed")
        if st.button("Load sample", use_container_width=True, key="btn_load_sample"):
            load_sample(choice)
            st.rerun()

    with st.container(key="sb_card_brand"):
        ui.sidebar_title("Branding", "palette")
        agency = st.text_input("Your agency name", value=ProjectDetails().agency_name)
        accent = st.color_picker("Case study colour", value="#4F46E5")
    ui.sidebar_footer()

# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
ui.hero()

if not is_configured():
    ui.banner("err", "Groq API key not found",
              "Open the .env file, set GROQ_API_KEY=your_key, save it, and restart the app.")

left, right = st.columns([3, 2], gap="large")
with left:
    with st.container(border=True, key="card_feedback"):
        ui.section_head(1, "Add client feedback", "Type or paste notes, upload a text file, or use a recording or link")
        mode = st.radio("Add client feedback", INPUT_MODES, horizontal=True, key="input_mode",
                        label_visibility="collapsed")
        if mode == INPUT_MODES[1]:
            text_file_section()
        elif mode == INPUT_MODES[2]:
            media_section()
        st.text_area("Feedback / interview notes", key="notes", height=340,
                     placeholder="Paste call notes, client emails, survey answers or an interview transcript...\n\n"
                                 "Tip: for interviews, start each line with the speaker's name, e.g.\n"
                                 "Bilal (Interviewer): What changed after launch?\nSana: Cancellations dropped from 9% to 5%.")
        words = len(st.session_state.get("notes", "").split())
        ui.note(f"{words} words · you can edit the text before generating", "pen-line")

with right:
    with st.container(border=True, key="card_details"):
        ui.section_head(2, "Project details", "Used to credit quotes and for the case study header")
        c1, c2 = st.columns(2)
        c1.text_input("Client company", key="client_name", placeholder="e.g. BrewBox Coffee Co.")
        c2.text_input("Industry", key="industry", placeholder="e.g. E-commerce")
        c1.text_input("Contact name", key="contact_name", placeholder="e.g. Sana Malik")
        c2.text_input("Contact role", key="contact_role", placeholder="e.g. Founder & CEO")
        c1.text_input("Service delivered", key="service", placeholder="e.g. AI support assistant")
        c2.text_input("Timeline", key="timeline", placeholder="e.g. 4 months")

    with st.container(border=True, key="card_generate"):
        ui.section_head(3, "Generate", "Testimonials, case study and Markdown in one go")
        generate_clicked = st.button("Generate content", type="primary", use_container_width=True,
                                     disabled=not is_configured(), key="btn_generate")
        ui.note("Usually 10–30 seconds · every number is checked against your notes", "shield-check")

if generate_clicked:
    details = ProjectDetails(**{k: st.session_state[k] for k, _ in DETAIL_FIELDS}, agency_name=agency)
    try:
        with st.spinner("Writing testimonials and case study, then fact-checking them..."):
            st.session_state["result"] = generate(st.session_state["notes"], details)
            st.session_state["details"] = details
            st.session_state.pop("video", None)  # a new result makes the old video and posts stale
            st.session_state.pop("social", None)
    except GenerationError as exc:
        ui.banner("err", "Could not generate content", str(exc))

# --------------------------------------------------------------------------- #
# Results
# --------------------------------------------------------------------------- #
result = st.session_state.get("result")
if not result:
    ui.empty_state()
else:
    details = st.session_state["details"]
    fc = result.content.get("fact_check", {})
    ui.results_header(result.content, details.client_name)

    if fc.get("issues"):
        ui.banner("err", "Fact check: please review before publishing", items=fc["issues"], icon="search-check")
    else:
        ui.banner("ok", "Fact check passed", "Every number in the content matches your notes.", icon="shield-check")
    if fc.get("auto_fixed"):
        with st.expander(f"The first draft had {len(fc['auto_fixed'])} issue(s) - the model corrected them",
                         key="exp_fixed"):
            st.markdown("\n".join(f"- {i}" for i in fc["auto_fixed"]))

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Testimonials", "Case study", "Markdown", "Video", "Share"])
    with tab1:
        quotes = result.content["testimonials"]
        components.html(render_testimonials_html(quotes, details.client_name, accent),
                        height=estimate_height(quotes))
    with tab2:
        if result.content.get("review_notes"):
            with st.expander(f"Internal: review before publishing ({len(result.content['review_notes'])} item(s)) "
                             f"- not part of the client-facing page", key="exp_review"):
                st.markdown("\n".join(f"- {n}" for n in result.content["review_notes"]))
        cs_view = st.radio("Case study view", CS_VIEWS, horizontal=True,
                           label_visibility="collapsed", key="cs_view")
        if cs_view == CS_VIEWS[0]:
            components.html(render_story_html(result.content, details, accent), height=720)
            ui.note("Autoplays chapter by chapter. Use the previous / next buttons, the arrow keys or the progress bar to move; space to pause.",
                    "clapperboard")
        else:
            st.html(render_case_study_html(result.content, details, accent))
    with tab3:
        view = st.radio("Markdown view", MD_VIEWS, horizontal=True,
                        label_visibility="collapsed", key="md_view")
        with st.container(border=True, key="card_markdown"):
            if view == MD_VIEWS[0]:
                st.markdown(result.markdown)
            else:
                st.code(result.markdown, language="markdown")

    with tab4:
        video_section(result.content, details, accent)
    with tab5:
        share_section(result.content, details)

    st.write("")
    d1, d2, _ = st.columns([1, 1, 1])
    d1.download_button("Download Markdown", result.markdown,
                       file_name=f"{slugify(details.client_name)}-case-study.md",
                       mime="text/markdown", use_container_width=True, type="primary", key="dl_markdown")
    if d2.button("Save to output/ folder", use_container_width=True, key="btn_save"):
        path = save_markdown(result.markdown, details)
        st.toast(f"Saved {Path(path).name}")

ui.page_footer()
