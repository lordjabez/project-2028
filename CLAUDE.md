# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Static site for project2028.com, a weekly tracker of the 2028 Democratic presidential field. GitHub Pages serves the root of `main` directly (no CI build), so a push to `main` is a publish.

A scheduled Claude Code routine (on the personal account) runs the weekly update. Its entire prompt is "follow `UPDATE.md`", which holds the editorial process, the `data/site.json` schema, and the sourcing and odds rules. Read `UPDATE.md` before touching content; change editorial behavior by editing that file.

## Commands

```bash
uv run build.py            # validate data/site.json, update history, write index.html, candidates/, archive/, sitemap.xml
uv run tools/portrait.py <src> <slug>   # crop/resize a portrait + race thumbnail (Pillow, via uv)
python3 -m http.server     # preview at http://localhost:8000
uvx ruff check build.py    # lint; build.py isn't ruff-formatted, so don't reformat it wholesale
```

There is no test suite. The validation in `build.py` (`validate()`) is the check, and it must stay at least as strict when extended.

## Architecture

- `build.py` is a single standard-library Python script: `validate()` → sort candidates by odds → `record_history()` → render every page from f-string templates through one shared `render_layout()` (head, meta, header, footer). Keep it stdlib-only and the CSS plain (no frameworks, no JS). `tools/portrait.py` is the one exception to stdlib-only, since image resizing needs Pillow; it's a separate uv script, not imported by the build.
- Pages: `index.html` (the full field), `candidates/<slug>/` (profile and odds history per current candidate), `archive/<date>/` (each week's frozen brief and odds), `archive/` (edition list). The build wipes and regenerates `candidates/` and `archive/` every run, so a dropped candidate's page disappears.
- `data/site.json` is the only hand-edited content. All text is plain and HTML-escaped at render time.
- `data/history.json` is build-owned. Each build upserts a snapshot keyed by `site.json`'s `updated` date: `odds` (field odds under the `_field` key), `names`, `headline` and `summary`. The archive pages are rendered from these, and older snapshots without a headline get no archive page. Week-over-week deltas, ghost markers, and sparklines all come from it, keyed by candidate `slug`, so slugs must never change. Never edit it by hand, and be aware that running the build after a throwaway edit to `site.json` will overwrite that date's snapshot.
- `index.html`, `sitemap.xml`, `candidates/` and `archive/` are generated and committed. Edit `build.py` or `styles.css`, never the output.
- Portraits are optional: `images/portraits/<slug>.webp` (400x500) plus `images/portraits/thumbs/<slug>.webp` (80x100, used in the race chart), both made by `tools/portrait.py`, otherwise a monogram is rendered. `images/og.png` is the static social share image and `apple-touch-icon.png` the iOS icon. A photo whose license requires attribution needs a `photo_credit` on the candidate, which renders at the bottom of the card.
- Odds across `candidates` plus `field_odds` must total 100 or the build fails.
