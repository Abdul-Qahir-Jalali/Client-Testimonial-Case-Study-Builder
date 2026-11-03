# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Agency teams (for example, account managers and marketers) who collect client feedback as call notes, emails, interview transcripts, or audio/video recordings and need to turn it into publishable proof: client testimonials and a case study. They work at a desk, between client calls, and must get the client's approval before anything is published.

## Product Purpose

Testimonial Studio turns raw client feedback into polished testimonials and a Challenge, Solution, Results case study, then exports it as Markdown. Success is a team shipping client proof quickly without ever publishing a claim the client did not make.

## Positioning

Two claims together: every number in the output is checked in code against the original notes (with one automatic self-correction pass and anything still wrong flagged for human review), and the input can be an audio/video recording or a link, not only text. Speed from raw recording to finished case study, with trustworthy numbers.

## Operating Context

- A Streamlit web app run locally by the agency team (`streamlit run app.py`), with an optional command-line version.
- Writing is done by the Groq API; audio, video and link transcription by ElevenLabs Scribe. Both need API keys in a local `.env`.
- Interview recordings are sent to ElevenLabs, so client consent matters before uploading real interviews.
- Output goes to clients' own channels afterwards: testimonials pasted into pages and proposals, case studies shown in a story player or full-page view, and the Markdown file.

## Capabilities and Constraints

- Inputs: typed notes, `.txt`/`.md` upload, audio/video upload, or a public link (YouTube, TikTok, Google Drive, Dropbox); optional project details (client, contact, role, industry, service, timeline).
- Outputs: 3 to 5 testimonials (short, medium, long) credited to the person who said them; a case study; a Markdown file.
- Speaker handling: after transcription the user names each speaker and marks the interviewer; interviewer words are never treated as client claims.
- Case study views: an auto-playing story player and an editorial full-page view, both using the agency's chosen brand colour and name.
- Testimonials can be filtered by length and copied with attribution.
- Numbers are never calculated or derived; changes are always written "from X to Y" as the client stated them.
- Streamlit front end: native widget labels accept only text, so icons on buttons, radios, tabs and expanders are applied with CSS.

## Brand Commitments

- Product name: Testimonial Studio ("Client Testimonial & Case Study Builder" in the README).
- Logo: the T Monogram (hexagon, white "T", amber dot), files in `assets/` and `favicon.svg`.
- Icons: Lucide only. No emoji or ASCII glyphs used as icons (explicit user requirement).
- Client-facing views (story player, full-page case study) stay unbranded by Testimonial Studio. They carry the agency's brand and colour.
- The UI keeps reminding users to get client approval before publishing.

## Evidence on Hand

- Four demo inputs in `samples/` (BrightPath Dental, Northwind Logistics, Urban Threads, Sunrise Fitness). These are sample content only.
- No real customers, testimonials, benchmarks, pricing, or press are recorded. Future work must not invent any, in the product, its samples, or its copy.

## Product Principles

1. Never fabricate. No invented testimonials, customers, metrics or results anywhere in the product or its sample content.
2. Trust is visible. Fact-check status, auto-corrections and review notes are shown plainly, never hidden.
3. Faithful to the client's words. Quotes stay in the speaker's voice, with the right attribution.
4. The deliverable belongs to the agency. Client-facing output carries the agency's brand, not the tool's.
5. A human approves before anything is published.
