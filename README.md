# Project 2028

The source for [project2028.com](https://www.project2028.com/), a static site that
tracks the 2028 Democratic presidential field. A scheduled
[Claude Code routine](https://code.claude.com/docs/en/routines) researches the race
once a week, rewrites the data, rebuilds the page, and pushes it.

The odds on the page are the model's own judgment, not a poll or a market.


## Prerequisites

- [Python](https://www.python.org/downloads/) 3.10 or later - standard library only
- [uv](https://docs.astral.sh/uv/) - optional, for running the build locally


## Usage

Everything on the page comes from `data/site.json`. The build validates it, records
the week's odds in `data/history.json`, and writes `index.html` and `sitemap.xml`:

```bash
uv run build.py

# Preview at http://localhost:8000
python3 -m http.server
```

Note that `index.html` is generated, so edit `build.py` or `styles.css` instead.


## Weekly Update

The routine's whole prompt is "follow `UPDATE.md`", so the editorial rules (sourcing,
tone, how odds move) live in that file and change by editing it. To run an update by
hand, open Claude Code in this folder and give it the same prompt.

Note that the routine commits straight to `main` with no review, and
[GitHub Pages](https://docs.github.com/en/pages) publishes whatever is there.


## Deployment

GitHub Pages serves the root of `main` at the domain in `CNAME`. There is no build
step on the GitHub side.


## References

- [Seobility SEO check](https://www.seobility.net/en/seocheck/check/?url=https%3A%2F%2Fwww.project2028.com%2F&mode=standard)
- [PageSpeed Insights](https://pagespeed.web.dev/analysis/https-project2028-com/vwdhxjb2i4?form_factor=mobile)
