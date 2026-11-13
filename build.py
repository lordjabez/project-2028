#!/usr/bin/env python3
"""Render index.html and sitemap.xml from data/site.json.

Standard library only. Run with `uv run build.py`.
Each run records the current odds in data/history.json, keyed by the
`updated` date, so the page can show week-over-week movement.
"""

from __future__ import annotations

import json
import math
import sys
from datetime import date
from html import escape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "site.json"
HISTORY = ROOT / "data" / "history.json"
PORTRAITS = ROOT / "images" / "portraits"
SITE_URL = "https://www.project2028.com/"
CLOUDFLARE_TOKEN = "3e0b3cabee9a4b2a9d79e96f2b17edcf"  # Web Analytics beacon; public by design

STATUSES = {
    "declared": "Declared",
    "exploring": "Exploring",
    "undeclared": "Undeclared",
}
FIELD = "_field"  # history key for "someone else"

Json = dict[str, Any]


def fail(errors: list[str]) -> None:
    print("data/site.json is invalid:", file=sys.stderr)
    for error in errors:
        print(f"  - {error}", file=sys.stderr)
    sys.exit(1)


def is_url(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("https://")


def is_date(value: Any) -> bool:
    try:
        date.fromisoformat(value)
    except (TypeError, ValueError):
        return False
    return True


def validate(site: Json) -> None:
    errors: list[str] = []
    if not is_date(site.get("updated")):
        errors.append("`updated` must be an ISO date (YYYY-MM-DD)")
    if not site.get("headline"):
        errors.append("`headline` is required")
    if not site.get("summary"):
        errors.append("`summary` needs at least one paragraph")

    candidates = site.get("candidates") or []
    if not candidates:
        errors.append("`candidates` is empty")
    slugs = [c.get("slug") for c in candidates]
    if len(set(slugs)) != len(slugs):
        errors.append("candidate slugs must be unique")

    for c in candidates:
        who = c.get("slug") or c.get("name") or "?"
        for field in ("slug", "name", "title", "bio", "outlook"):
            if not c.get(field):
                errors.append(f"{who}: `{field}` is required")
        if c.get("status") not in STATUSES:
            errors.append(f"{who}: `status` must be one of {sorted(STATUSES)}")
        if not isinstance(c.get("odds"), (int, float)) or c["odds"] <= 0:
            errors.append(f"{who}: `odds` must be a positive number")
        credit = c.get("photo_credit")
        if credit is not None and not (
            credit.get("author") and credit.get("license") and is_url(credit.get("url"))
        ):
            errors.append(f"{who}: `photo_credit` needs `author`, `license`, and an https `url`")
        for kind in ("headlines", "quotes"):
            for item in c.get(kind) or []:
                if not item.get("text"):
                    errors.append(f"{who}: every entry in `{kind}` needs `text`")
                if not is_url(item.get("url")):
                    errors.append(f"{who}: every entry in `{kind}` needs an https `url`")
                if not item.get("source"):
                    errors.append(f"{who}: every entry in `{kind}` needs a `source`")
                if not is_date(item.get("date")):
                    errors.append(f"{who}: every entry in `{kind}` needs an ISO `date`")

    field_odds = site.get("field_odds")
    if not isinstance(field_odds, (int, float)) or field_odds < 0:
        errors.append("`field_odds` must be a non-negative number")
    else:
        total = field_odds + sum(
            c["odds"] for c in candidates if isinstance(c.get("odds"), (int, float))
        )
        if abs(total - 100) > 0.05:
            errors.append(f"odds plus `field_odds` must total 100 (got {total:g})")

    for item in site.get("calendar") or []:
        if not is_date(item.get("date")) or not item.get("event"):
            errors.append("every `calendar` entry needs an ISO `date` and an `event`")
    for item in site.get("results") or []:
        if not is_date(item.get("date")) or not item.get("contest") or not item.get("summary"):
            errors.append("every `results` entry needs `date`, `contest`, and `summary`")
        if item.get("url") and not is_url(item["url"]):
            errors.append("`results` urls must be https")
    for item in site.get("out") or []:
        if not item.get("name") or not item.get("note"):
            errors.append("every `out` entry needs `name` and `note`")

    if errors:
        fail(errors)


def record_history(site: Json) -> list[Json]:
    """Upsert this week's odds into history.json and return all snapshots."""
    history: list[Json] = json.loads(HISTORY.read_text()) if HISTORY.exists() else []
    odds = {c["slug"]: c["odds"] for c in site["candidates"]}
    odds[FIELD] = site["field_odds"]
    history = [h for h in history if h["date"] != site["updated"]]
    history.append({"date": site["updated"], "odds": odds})
    history.sort(key=lambda h: h["date"])
    HISTORY.write_text(json.dumps(history, indent=2) + "\n")
    return history


def long_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d:%B} {d.day}, {d.year}"


def short_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d:%b} {d.day}, {d.year}"


def pct(value: float) -> str:
    return f"{value:g}%"


def portrait(slug: str) -> str | None:
    for ext in ("webp", "jpg", "png"):
        if (PORTRAITS / f"{slug}.{ext}").exists():
            return f"/images/portraits/{slug}.{ext}"
    return None


def initials(name: str) -> str:
    parts = [p for p in name.replace(".", " ").split() if p[0].isalpha()]
    return (parts[0][0] + parts[-1][0]).upper()


def avatar(c: Json) -> str:
    src = portrait(c["slug"])
    if src:
        return f'<img src="{src}" alt="" width="40" height="40" loading="lazy">'
    return f'<span class="monogram">{escape(initials(c["name"]))}</span>'


def movement(slug: str, odds: float, previous: Json | None) -> str:
    if previous is None:
        return ""
    if slug not in previous["odds"]:
        return '<span class="delta new">New</span>'
    change = round(odds - previous["odds"][slug], 1)
    if change > 0:
        return f'<span class="delta up">&#9650; {change:g}</span>'
    if change < 0:
        return f'<span class="delta down">&#9660; {abs(change):g}</span>'
    return '<span class="delta flat">&ndash;</span>'


def sparkline(slug: str, history: list[Json]) -> str:
    points = [h["odds"][slug] for h in history if slug in h["odds"]][-26:]
    if len(points) < 2:
        return ""
    width, height = 72, 22
    step = width / (len(points) - 1)
    # Each line gets its own range (at least 5 points wide) so small moves stay visible.
    span = max(max(points) - min(points), 5)
    base = (max(points) + min(points) - span) / 2
    coords = " ".join(
        f"{i * step:.1f},{height - 1 - (p - base) / span * (height - 2):.1f}"
        for i, p in enumerate(points)
    )
    return (
        f'<svg class="spark" viewBox="0 0 {width} {height}" width="{width}" '
        f'height="{height}" role="img" aria-label="Odds trend">'
        f'<polyline points="{coords}"/></svg>'
    )


def render_race(site: Json, history: list[Json]) -> str:
    candidates = site["candidates"]
    previous = next((h for h in reversed(history) if h["date"] < site["updated"]), None)
    scale = float(min(100, max(30, math.ceil((candidates[0]["odds"] + 5) / 10) * 10)))
    tick_step = 10 if scale <= 60 else 25
    ticks = "".join(
        f'<span style="left:{t / scale * 100:g}%">{t}%</span>'
        for t in range(0, int(scale) + 1, tick_step)
    )

    rows = []
    for rank, c in enumerate(candidates, start=1):
        left = min(c["odds"] / scale, 1) * 100
        ghost = ""
        if previous and c["slug"] in previous["odds"]:
            was = min(previous["odds"][c["slug"]] / scale, 1) * 100
            ghost = f'<span class="ghost" style="left:{was:g}%" title="Last update"></span>'
        rows.append(f"""
          <li class="lane status-{c["status"]}">
            <span class="lane-rank">{rank}</span>
            <a class="lane-name" href="#{c["slug"]}">{escape(c["name"])}</a>
            <div class="lane-track">
              <div class="lane-inner">
                <span class="lane-fill" style="width:{left:g}%"></span>
                {ghost}
                <span class="lane-runner" style="left:{left:g}%">{avatar(c)}</span>
              </div>
            </div>
            <span class="lane-odds">{pct(c["odds"])}</span>
            <span class="lane-move">{movement(c["slug"], c["odds"], previous)}</span>
            <span class="lane-spark">{sparkline(c["slug"], history)}</span>
          </li>""")

    field_move = movement(FIELD, site["field_odds"], previous)
    since = f" Hollow markers show where each stood on {short_date(previous['date'])}." if previous else ""
    return f"""
      <section class="panel" id="race" aria-labelledby="race-title">
        <h2 class="panel-title" id="race-title">The Race</h2>
        <p class="panel-note">Our estimate of each hopeful's chance of winning the 2028 Democratic nomination.{since}</p>
        <ol class="race">
          <li class="race-axis" aria-hidden="true"><div class="lane-track"><div class="lane-inner">{ticks}</div></div></li>
          {"".join(rows)}
        </ol>
        <p class="race-field">Someone not listed here: <strong>{pct(site["field_odds"])}</strong> {field_move}</p>
      </section>"""


def render_sourced(items: list[Json], quote: bool) -> str:
    out = []
    for item in items:
        cite = (
            f'<a href="{escape(item["url"], quote=True)}" rel="noopener nofollow">'
            f'{escape(item["source"])}</a>, {short_date(item["date"])}'
        )
        if quote:
            out.append(
                f'<blockquote><p>&ldquo;{escape(item["text"])}&rdquo;</p>'
                f"<footer>{cite}</footer></blockquote>"
            )
        else:
            out.append(f'<li>{escape(item["text"])} <span class="cite">{cite}</span></li>')
    return "\n".join(out)


def render_card(rank: int, c: Json) -> str:
    src = portrait(c["slug"])
    image = (
        f'<img src="{src}" alt="Portrait of {escape(c["name"], quote=True)}" '
        f'width="400" height="400" loading="lazy">'
        if src
        else f'<div class="card-monogram">{escape(initials(c["name"]))}</div>'
    )
    sections = [
        f'<div class="card-section"><h3 class="section-title">Background</h3><p>{escape(c["bio"])}</p></div>',
        f'<div class="card-section"><h3 class="section-title">Outlook</h3><p>{escape(c["outlook"])}</p></div>',
    ]
    if c.get("headlines"):
        sections.append(
            '<div class="card-section"><h3 class="section-title">Recent Headlines</h3>'
            f'<ul>{render_sourced(c["headlines"], quote=False)}</ul></div>'
        )
    if c.get("quotes"):
        sections.append(
            '<div class="card-section"><h3 class="section-title">In Their Words</h3>'
            f'<div class="quotes-container">{render_sourced(c["quotes"], quote=True)}</div></div>'
        )
    credit = c.get("photo_credit")
    if src and credit:
        sections.append(
            f'<p class="photo-credit">Photo: <a href="{escape(credit["url"], quote=True)}" '
            f'rel="noopener nofollow">{escape(credit["author"])}</a>, {escape(credit["license"])}</p>'
        )
    return f"""
          <article class="card" id="{c["slug"]}">
            <div class="card-image-container">
              {image}
              <div class="card-image-overlay"></div>
              <div class="card-badges">
                <span class="badge rank">#{rank}</span>
                <span class="badge odds">{pct(c["odds"])}</span>
              </div>
              <div class="card-image-title">
                <h2>{escape(c["name"])}</h2>
                <p>{escape(c["title"])}</p>
                <span class="status status-{c["status"]}">{STATUSES[c["status"]]}</span>
              </div>
            </div>
            <div class="card-content">
              {"".join(sections)}
            </div>
          </article>"""


def render_dated(title: str, anchor: str, rows: list[str]) -> str:
    if not rows:
        return ""
    return f"""
      <section class="panel" id="{anchor}" aria-labelledby="{anchor}-title">
        <h2 class="panel-title" id="{anchor}-title">{title}</h2>
        <ul class="dated">{"".join(rows)}</ul>
      </section>"""


def render_results(site: Json) -> str:
    rows = []
    for r in sorted(site.get("results") or [], key=lambda r: r["date"], reverse=True):
        link = (
            f' <a class="cite" href="{escape(r["url"], quote=True)}" rel="noopener nofollow">Source</a>'
            if r.get("url")
            else ""
        )
        rows.append(
            f'<li><time datetime="{r["date"]}">{short_date(r["date"])}</time>'
            f'<div><strong>{escape(r["contest"])}</strong>'
            f'<p>{escape(r["summary"])}{link}</p></div></li>'
        )
    return render_dated("Results", "results", rows)


def render_calendar(site: Json) -> str:
    rows = []
    for item in sorted(site.get("calendar") or [], key=lambda i: i["date"]):
        note = f'<p>{escape(item["note"])}</p>' if item.get("note") else ""
        rows.append(
            f'<li><time datetime="{item["date"]}">'
            f'{escape(item.get("label") or short_date(item["date"]))}</time>'
            f'<div><strong>{escape(item["event"])}</strong>{note}</div></li>'
        )
    return render_dated("Key Dates", "calendar", rows)


def render_out(site: Json) -> str:
    if not site.get("out"):
        return ""
    rows = "".join(
        f'<li><strong>{escape(o["name"])}</strong> {escape(o["note"])}</li>' for o in site["out"]
    )
    return f"""
      <section class="panel" id="out" aria-labelledby="out-title">
        <h2 class="panel-title" id="out-title">Out of the Running</h2>
        <ul class="out">{rows}</ul>
      </section>"""


def render_page(site: Json, history: list[Json]) -> str:
    candidates = site["candidates"]
    updated = long_date(site["updated"])
    leaders = ", ".join(c["name"] for c in candidates[:3])
    description = (
        f"Weekly tracker of the 2028 Democratic presidential field: who is running, "
        f"what they are saying, and nomination odds. Current leaders: {leaders}."
    )
    structured = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "Project 2028",
        "url": SITE_URL,
        "description": description,
        "dateModified": site["updated"],
        "mainEntity": {
            "@type": "ItemList",
            "name": "2028 Democratic presidential hopefuls, ranked by nomination odds",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": rank,
                    "item": {"@type": "Person", "name": c["name"], "jobTitle": c["title"]},
                }
                for rank, c in enumerate(candidates, start=1)
            ],
        },
    }
    summary = "".join(f"<p>{escape(p)}</p>" for p in site["summary"])
    cards = "".join(render_card(rank, c) for rank, c in enumerate(candidates, start=1))
    title = "Project 2028: Tracking the 2028 Democratic Presidential Field"

    return f"""<!DOCTYPE html>
<!-- Generated by build.py from data/site.json. Do not edit by hand. -->
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <meta name="description" content="{escape(description, quote=True)}">
    <meta name="theme-color" content="#111827">
    <link rel="canonical" href="{SITE_URL}">
    <meta property="og:type" content="website">
    <meta property="og:url" content="{SITE_URL}">
    <meta property="og:site_name" content="Project 2028">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{escape(description, quote=True)}">
    <meta name="twitter:card" content="summary">
    <link rel="icon" type="image/svg+xml" href="/favicon.svg">
    <link rel="stylesheet" href="styles.css">
    <script type="application/ld+json">{json.dumps(structured).replace("</", "<\\/")}</script>
  </head>
  <body>
    <header>
      <div class="container">
        <h1><span class="gradient-text">Project 2028</span></h1>
        <p class="subtitle">Tracking the 2028 Democratic presidential field, updated weekly</p>
        <nav aria-label="Sections">
          <a href="#race">The Race</a>
          <a href="#hopefuls">The Hopefuls</a>
          <a href="#about">About</a>
        </nav>
      </div>
    </header>

    <main class="container">
      <section class="panel brief" aria-labelledby="brief-title">
        <p class="eyebrow">Week of <time datetime="{site["updated"]}">{updated}</time></p>
        <h2 class="brief-title" id="brief-title">{escape(site["headline"])}</h2>
        {summary}
      </section>
      {render_race(site, history)}
      {render_results(site)}
      {render_calendar(site)}
      <section id="hopefuls" aria-labelledby="hopefuls-title">
        <h2 class="panel-title" id="hopefuls-title">The Hopefuls</h2>
        <div class="grid">{cards}
        </div>
      </section>
      {render_out(site)}
      <section class="panel" id="about" aria-labelledby="about-title">
        <h2 class="panel-title" id="about-title">About This Tracker</h2>
        <p>Project 2028 is researched and written each week by an AI model (Anthropic's Claude), which reads current reporting, polling, and public statements, then rebuilds this page. The odds are the model's own judgment of who wins the Democratic nomination. They are not a poll, a betting market, or an endorsement, and they will be wrong in interesting ways.</p>
        <p>Headlines and quotes link to their sources. If something here is inaccurate, the linked source is the authority.</p>
      </section>
    </main>

    <footer>
      <div class="container">
        <p>Last updated {updated}. Independent and unaffiliated with any candidate, campaign, or party.</p>
        <p class="footer-credit">Created by <a href="https://www.linkedin.com/in/judsonneer/" rel="noopener">Jud Neer</a>. Source on <a href="https://github.com/lordjabez/project-2028" rel="noopener">GitHub</a>.</p>
      </div>
    </footer>
    <script type="module" src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon='{{"token": "{CLOUDFLARE_TOKEN}"}}'></script>
  </body>
</html>
"""


def render_sitemap(updated: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{SITE_URL}</loc>
    <lastmod>{updated}</lastmod>
    <changefreq>weekly</changefreq>
  </url>
</urlset>
"""


def main() -> None:
    site: Json = json.loads(DATA.read_text())
    validate(site)
    site["candidates"].sort(key=lambda c: c["odds"], reverse=True)
    history = record_history(site)
    (ROOT / "index.html").write_text(render_page(site, history))
    (ROOT / "sitemap.xml").write_text(render_sitemap(site["updated"]))
    print(f"Built index.html for {site['updated']} with {len(site['candidates'])} candidates.")


if __name__ == "__main__":
    main()
