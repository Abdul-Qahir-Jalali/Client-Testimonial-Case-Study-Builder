"""Command-line interface.

Examples:
    python cli.py samples/brightpath_dental_interview.txt
    python cli.py interview.mp3 --speaker-names "Bilal (Interviewer), Hamza Qureshi" --client "Sunrise Fitness"
    python cli.py interview.mp4 --speaker-names "Bilal (Interviewer), Hamza Qureshi"
    python cli.py "https://www.youtube.com/watch?v=..." --speaker-names "Bilal (Interviewer), Hamza Qureshi"
    python cli.py notes.txt --client "Acme Ltd" --contact "Jane Doe" --role "CEO"
    python cli.py --all-samples
"""

import argparse
import sys
from pathlib import Path

from generator import BASE_DIR, GenerationError, ProjectDetails, generate, parse_input_file, save_markdown
from transcribe import MEDIA_TYPES, TranscriptionError, format_transcript, transcribe_audio, transcribe_url

FIELDS = {
    "client": "client_name",
    "contact": "contact_name",
    "role": "contact_role",
    "industry": "industry",
    "service": "service",
    "timeline": "timeline",
    "agency": "agency_name",
}


def build_details(meta: dict, args: argparse.Namespace) -> ProjectDetails:
    details = ProjectDetails()
    for cli_name, attr in FIELDS.items():
        value = getattr(args, cli_name) or meta.get(attr)
        if value:
            setattr(details, attr, value)
    return details


def is_link(value: str) -> bool:
    return value.lower().startswith(("http://", "https://"))


def load_media(source: str, args: argparse.Namespace) -> str:
    """Transcribe an audio/video file or a link. --speaker-names are given in order of first
    appearance; add '(Interviewer)' after a name to mark your own team."""
    if is_link(source):
        print("\n> Transcribing from link with ElevenLabs...")
        transcript = transcribe_url(source, args.num_speakers)
        stem = "link"
    else:
        path = Path(source)
        print(f"\n> Transcribing {path.name} with ElevenLabs...")
        transcript = transcribe_audio(path.read_bytes(), path.name, args.num_speakers)
        stem = path.stem
    given = [n.strip() for n in (args.speaker_names or "").split(",") if n.strip()]
    names, interviewers = {}, set()
    for spk, raw in zip(transcript.speakers, given):
        if "(interviewer)" in raw.lower():
            interviewers.add(spk)
            raw = raw[: raw.lower().index("(interviewer)")].strip()
        names[spk] = raw
    text = format_transcript(transcript, names, interviewers)
    print(f"  {len(transcript.speakers)} speaker(s), {int(transcript.duration // 60)}:{int(transcript.duration % 60):02d} min")
    if len(given) < len(transcript.speakers):
        print("  ! Not all speakers were named - unnamed ones appear as 'Speaker A/B/...'. "
              "Use --speaker-names to set them.")
    out = Path(args.out) if args.out else BASE_DIR / "output"
    out.mkdir(parents=True, exist_ok=True)
    tpath = out / f"{stem}-transcript.txt"
    tpath.write_text(text, encoding="utf-8")
    print(f"  Transcript saved: {tpath}")
    return text


def run_one(source: str, args: argparse.Namespace) -> None:
    if is_link(source) or Path(source).suffix.lower().lstrip(".") in MEDIA_TYPES:
        notes, meta = load_media(source, args), {}
    else:
        notes, meta = parse_input_file(source)
    details = build_details(meta, args)
    print(f"\n> Generating content  (client: {details.client_name})")
    result = generate(notes, details)
    for w in result.warnings:
        print(f"  ! {w}")
    out = save_markdown(result.markdown, details, args.out)
    print(f"  Testimonials: {len(result.content['testimonials'])}")
    print(f"  Saved: {out}")
    if args.print:
        print("\n" + result.markdown)


def main() -> int:
    # Windows terminals may not be UTF-8; avoid crashes when printing characters like "→" or "—"
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Turn raw client feedback into testimonials + a case study.")
    p.add_argument("input", nargs="?", help="A .txt/.md notes file, an audio/video file, or a video link")
    p.add_argument("--speaker-names", help='Audio/video only: names in order of speaking, e.g. "Bilal (Interviewer), Hamza Qureshi"')
    p.add_argument("--num-speakers", type=int, help="Audio/video only: number of speakers, if known")
    p.add_argument("--all-samples", action="store_true", help="Run every file in samples/")
    p.add_argument("--out", help="Output folder (default: output/)")
    p.add_argument("--print", action="store_true", help="Also print the Markdown to the terminal")
    for name in FIELDS:
        p.add_argument(f"--{name}", help=f"Project detail: {name}")
    args = p.parse_args()

    if args.all_samples:
        sources = [str(f) for f in sorted((BASE_DIR / "samples").glob("*.txt"))]
    elif args.input:
        sources = [args.input]
    else:
        p.print_help()
        return 1

    try:
        for src in sources:
            if not is_link(src) and not Path(src).exists():
                print(f"File not found: {src}")
                return 1
            run_one(src, args)
    except (GenerationError, TranscriptionError) as exc:
        print(f"Error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
