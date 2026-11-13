# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Static site for project2028.com, a weekly tracker of the 2028 Democratic presidential field. GitHub Pages serves the root of `main` directly (no CI build), so a push to `main` is a publish.

A scheduled Claude Code routine (on the personal account) runs the weekly update. Its entire prompt is "follow `UPDATE.md`", which holds the editorial process, the `data/site.json` schema, and the sourcing and odds rules. Read `UPDATE.md` before touching content; change editorial behavior by editing that file.

## Commands

```bash
uv run build.py            # validate data/site.json, update history, write index.html + sitemap.xml
python3 -m http.server     # preview at http://localhost:8000
uvx ruff check build.py    # lint; build.py isn't ruff-formatted, so don't reformat it wholesale
```

There is no test suite. The validation in `build.py` (`validate()`) is the check, and it must stay at least as strict when extended.

## Architecture

- `build.py` is a single standard-library Python script: `validate()` → sort candidates by odds → `record_history()` → render `index.html` and `sitemap.xml` from f-string templates. Keep it stdlib-only and the CSS plain (no frameworks, no JS).
- `data/site.json` is the only hand-edited content. All text is plain and HTML-escaped at render time.
- `data/history.json` is build-owned. Each build upserts a snapshot keyed by `site.json`'s `updated` date (field odds under the `_field` key). Week-over-week deltas, ghost markers, and sparklines all come from it, keyed by candidate `slug`, so slugs must never change. Never edit it by hand, and be aware that running the build after a throwaway edit to `site.json` will overwrite that date's snapshot.
- `index.html` and `sitemap.xml` are generated and committed. Edit `build.py` or `styles.css`, never the output.
- Portraits are optional: `images/portraits/<slug>.{webp,jpg,png}`, otherwise a monogram is rendered. A photo whose license requires attribution needs a `photo_credit` on the candidate, which renders at the bottom of the card.
- Odds across `candidates` plus `field_odds` must total 100 or the build fails.
