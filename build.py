#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Render the site from data/site.json.

Standard library only. Run with `uv run build.py`.
Each run records the current odds and brief in data/history.json, keyed by
the `updated` date, so pages can show week-over-week movement and every
past edition gets a permanent archive page.

Outputs: index.html, sitemap.xml, candidates/<slug>/index.html, and
archive/[<date>/]index.html. The candidates/ and archive/ directories are
build-owned and regenerated from scratch on every run.
"""

from __future__ import annotations

import json
import math
import re
import shutil
import sys
from datetime import date, datetime
from html import escape
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "site.json"
HISTORY = ROOT / "data" / "history.json"
PORTRAITS = ROOT / "images" / "portraits"
SITE_URL = "https://www.project2028.com/"
SITE_NAME = "Project 2028"
CANDIDATES_DIR = ROOT / "candidates"
ARCHIVE_DIR = ROOT / "archive"
OG_IMAGE = ("/images/og.png", 1200, 630)
PORTRAIT_SIZE = (400, 500)  # portraits are 4:5
SITE_TZ = ZoneInfo("America/Los_Angeles")  # editions are dated in Pacific time
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
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
        if not SLUG.match(str(c.get("slug") or "")):
            errors.append(f"{who}: `slug` must be lowercase letters, digits, and single hyphens")
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
    """Upsert this week's snapshot into history.json and return all snapshots.

    Snapshots before archive pages existed have only `date` and `odds`.
    """
    history: list[Json] = json.loads(HISTORY.read_text()) if HISTORY.exists() else []
    odds = {c["slug"]: c["odds"] for c in site["candidates"]}
    odds[FIELD] = site["field_odds"]
    history = [h for h in history if h["date"] != site["updated"]]
    history.append({
        "date": site["updated"],
        "headline": site["headline"],
        "summary": site["summary"],
        "odds": odds,
        "names": {c["slug"]: c["name"] for c in site["candidates"]},
    })
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


def absolute(path: str) -> str:
    """Turn a root-absolute path like /archive/ into a full URL."""
    return SITE_URL.rstrip("/") + path


def candidate_path(slug: str) -> str:
    return f"/candidates/{slug}/"


def archive_path(iso: str) -> str:
    return f"/archive/{iso}/"


def schema_datetime(iso: str) -> str:
    """Structured-data timestamp for a YYYY-MM-DD date: local midnight with its UTC offset.

    Google rejects bare dates in dateModified and datePublished, so emit full ISO 8601.
    """
    return datetime.combine(date.fromisoformat(iso), datetime.min.time(), SITE_TZ).isoformat()


def clip(text: str, limit: int = 160) -> str:
    """Shorten text at a word boundary, for meta descriptions."""
    if len(text) <= limit:
        return text
    return text[: limit - 1].rsplit(" ", 1)[0].rstrip(",;:.") + "\u2026"


def ld_json(data: Json) -> str:
    payload = json.dumps(data).replace("</", "<\\/")
    return f'<script type="application/ld+json">{payload}</script>'


ORGANIZATION = {
    "@type": "Organization",
    "name": SITE_NAME,
    "url": SITE_URL,
    "logo": {"@type": "ImageObject", "url": absolute("/apple-touch-icon.png"), "width": 180, "height": 180},
}


def breadcrumbs(trail: list[tuple[str, str]]) -> Json:
    """BreadcrumbList for a trail of (name, root-absolute path) pairs."""
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i, "name": name, "item": absolute(path)}
            for i, (name, path) in enumerate(trail, start=1)
        ],
    }


def breadcrumb_nav(trail: list[tuple[str, str]]) -> str:
    """Visible breadcrumb; the last entry is the current page."""
    items = [f'<li><a href="{path}">{escape(name)}</a></li>' for name, path in trail[:-1]]
    items.append(f'<li aria-current="page">{escape(trail[-1][0])}</li>')
    return f'<nav class="breadcrumb" aria-label="Breadcrumb"><ol>{"".join(items)}</ol></nav>'


def portrait(slug: str) -> str | None:
    for ext in ("webp", "jpg", "png"):
        if (PORTRAITS / f"{slug}.{ext}").exists():
            return f"/images/portraits/{slug}.{ext}"
    return None


def initials(name: str) -> str:
    parts = [p for p in name.replace(".", " ").split() if p[0].isalpha()]
    return (parts[0][0] + parts[-1][0]).upper()


def thumbnail(slug: str) -> str | None:
    if (PORTRAITS / "thumbs" / f"{slug}.webp").exists():
        return f"/images/portraits/thumbs/{slug}.webp"
    return portrait(slug)


def avatar(c: Json) -> str:
    src = thumbnail(c["slug"])
    if src:
        return f'<img src="{src}" alt="" width="40" height="50" loading="lazy">'
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
            <a class="lane-name" href="{candidate_path(c["slug"])}">{escape(c["name"])}</a>
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


def portrait_image(c: Json, lazy: bool = True) -> str:
    src = portrait(c["slug"])
    if not src:
        return f'<div class="card-monogram">{escape(initials(c["name"]))}</div>'
    width, height = PORTRAIT_SIZE
    loading = ' loading="lazy"' if lazy else ""
    return (
        f'<img src="{src}" alt="Portrait of {escape(c["name"], quote=True)}" '
        f'width="{width}" height="{height}"{loading}>'
    )


def render_details(c: Json) -> list[str]:
    """Bio, outlook, headlines, and quotes, shared by cards and profile pages."""
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
    return sections


def photo_credit(c: Json) -> str:
    credit = c.get("photo_credit")
    if not (credit and portrait(c["slug"])):
        return ""
    return (
        f'<p class="photo-credit">Photo: <a href="{escape(credit["url"], quote=True)}" '
        f'rel="noopener nofollow">{escape(credit["author"])}</a>, {escape(credit["license"])}</p>'
    )


def render_card(rank: int, c: Json) -> str:
    profile = candidate_path(c["slug"])
    sections = render_details(c)
    sections.append(
        f'<p class="card-more"><a href="{profile}">{escape(c["name"])}: odds history and full profile</a></p>'
    )
    return f"""
          <article class="card" id="{c["slug"]}">
            <div class="card-image-container">
              {portrait_image(c)}
              <div class="card-image-overlay"></div>
              <div class="card-badges">
                <span class="badge rank">#{rank}</span>
                <span class="badge odds">{pct(c["odds"])}</span>
              </div>
              <div class="card-image-title">
                <h2><a href="{profile}">{escape(c["name"])}</a></h2>
                <p>{escape(c["title"])}</p>
                <span class="status status-{c["status"]}">{STATUSES[c["status"]]}</span>
              </div>
            </div>
            <div class="card-content">
              {"".join(sections)}{photo_credit(c)}
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


def render_layout(
    path: str,
    title: str,
    description: str,
    body: str,
    updated: str,
    structured: Json,
    og_type: str = "website",
    og_image: tuple[str, int, int, str] | None = None,
) -> str:
    """Wrap a page body in the shared head, header, and footer.

    `path` is root-absolute (e.g. /candidates/gavin-newsom/). The homepage gets
    the site name as its h1; every other page supplies its own h1 in `body`.
    """
    image, width, height, alt = og_image or (*OG_IMAGE, "Project 2028: tracking the 2028 Democratic presidential field")
    home = path == "/"
    brand = (
        f'<h1><span class="gradient-text">{SITE_NAME}</span></h1>'
        if home
        else f'<p class="site-name"><a href="/"><span class="gradient-text">{SITE_NAME}</span></a></p>'
    )
    return f"""<!DOCTYPE html>
<!-- Generated by build.py from data/site.json. Do not edit by hand. -->
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape(title)}</title>
    <meta name="description" content="{escape(description, quote=True)}">
    <meta name="robots" content="max-image-preview:large">
    <meta name="theme-color" content="#111827">
    <link rel="canonical" href="{absolute(path)}">
    <meta property="og:type" content="{og_type}">
    <meta property="og:url" content="{absolute(path)}">
    <meta property="og:site_name" content="{SITE_NAME}">
    <meta property="og:title" content="{escape(title, quote=True)}">
    <meta property="og:description" content="{escape(description, quote=True)}">
    <meta property="og:image" content="{absolute(image)}">
    <meta property="og:image:width" content="{width}">
    <meta property="og:image:height" content="{height}">
    <meta property="og:image:alt" content="{escape(alt, quote=True)}">
    <meta name="twitter:card" content="summary_large_image">
    <link rel="icon" href="/favicon.ico" sizes="48x48">
    <link rel="icon" type="image/png" href="/favicon-96.png" sizes="96x96">
    <link rel="icon" type="image/svg+xml" href="/favicon.svg">
    <link rel="apple-touch-icon" href="/apple-touch-icon.png">
    <link rel="stylesheet" href="/styles.css">
    {ld_json(structured)}
  </head>
  <body>
    <header>
      <div class="container">
        {brand}
        <p class="subtitle">Tracking the 2028 Democratic presidential field, updated weekly</p>
        <nav aria-label="Sections">
          <a href="/#race">The Race</a>
          <a href="/#hopefuls">The Hopefuls</a>
          <a href="/archive/">Past Editions</a>
          <a href="/#about">About</a>
        </nav>
      </div>
    </header>

    <main class="container">{body}
    </main>

    <footer>
      <div class="container">
        <p>Last updated {long_date(updated)}. Independent and unaffiliated with any candidate, campaign, or party.</p>
        <p class="footer-credit"><a href="/archive/">Past editions</a>. Created by <a href="https://www.linkedin.com/in/judsonneer/" rel="noopener">Jud Neer</a>. Source on <a href="https://github.com/lordjabez/project-2028" rel="noopener">GitHub</a>.</p>
      </div>
    </footer>
    <script type="module" src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon='{{"token": "{CLOUDFLARE_TOKEN}"}}'></script>
  </body>
</html>
"""


def news_article(snapshot: Json, path: str) -> Json:
    """NewsArticle for one weekly brief; `path` is where the brief lives."""
    return {
        "@type": "NewsArticle",
        "headline": snapshot["headline"],
        "description": clip(snapshot["summary"][0]),
        "url": absolute(path),
        "datePublished": schema_datetime(snapshot["date"]),
        "dateModified": schema_datetime(snapshot["date"]),
        "image": [absolute(OG_IMAGE[0])],
        "author": ORGANIZATION,
        "publisher": ORGANIZATION,
    }


def render_page(site: Json, history: list[Json]) -> str:
    candidates = site["candidates"]
    leaders = ", ".join(c["name"] for c in candidates[:3])
    description = (
        f"Weekly tracker of the 2028 Democratic presidential field: who is running, "
        f"what they are saying, and nomination odds. Current leaders: {leaders}."
    )
    brief = {"date": site["updated"], "headline": site["headline"], "summary": site["summary"]}
    structured = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebSite",
                "name": SITE_NAME,
                "url": SITE_URL,
                "description": description,
                "dateModified": schema_datetime(site["updated"]),
                "publisher": ORGANIZATION,
            },
            {
                "@type": "ItemList",
                "name": "2028 Democratic presidential hopefuls, ranked by nomination odds",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": rank,
                        "url": absolute(candidate_path(c["slug"])),
                        "item": {"@type": "Person", "name": c["name"], "jobTitle": c["title"]},
                    }
                    for rank, c in enumerate(candidates, start=1)
                ],
            },
            news_article(brief, archive_path(site["updated"])),
        ],
    }
    summary = "".join(f"<p>{escape(p)}</p>" for p in site["summary"])
    cards = "".join(render_card(rank, c) for rank, c in enumerate(candidates, start=1))
    body = f"""
      <section class="panel brief" aria-labelledby="brief-title">
        <p class="eyebrow">Week of <time datetime="{site["updated"]}">{long_date(site["updated"])}</time></p>
        <h2 class="brief-title" id="brief-title">{escape(site["headline"])}</h2>
        {summary}
        <p class="brief-more"><a href="/archive/">Past editions</a></p>
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
      </section>"""
    title = "Project 2028: Tracking the 2028 Democratic Presidential Field"
    return render_layout("/", title, description, body, site["updated"], structured)


def ranked(snapshot: Json) -> list[tuple[str, float]]:
    """A snapshot's (slug, odds) pairs, highest first, without the field."""
    pairs = [(slug, odds) for slug, odds in snapshot["odds"].items() if slug != FIELD]
    return sorted(pairs, key=lambda pair: pair[1], reverse=True)


def odds_chart(name: str, points: list[tuple[str, float]]) -> str:
    """Inline SVG line chart of (date, odds) points, oldest first; needs two or more."""
    width, height = 560, 240
    left, right, top, bottom = 44, 20, 14, 30
    plot_w, plot_h = width - left - right, height - top - bottom
    days = [date.fromisoformat(d).toordinal() for d, _ in points]
    peak = max(odds for _, odds in points)
    step = 5 if peak <= 20 else 10 if peak <= 60 else 20
    ceiling = min(100, max(2 * step, math.ceil(peak / step) * step))

    def x(day: int) -> float:
        return left + (day - days[0]) / (days[-1] - days[0]) * plot_w

    def y(odds: float) -> float:
        return top + plot_h - odds / ceiling * plot_h

    grid = "".join(
        f'<line class="chart-grid" x1="{left}" x2="{width - right}" y1="{y(t):.1f}" y2="{y(t):.1f}"/>'
        f'<text class="chart-label" x="{left - 8}" y="{y(t) + 4:.1f}" text-anchor="end">{t}%</text>'
        for t in range(0, ceiling + 1, step)
    )
    dates = (
        f'<text class="chart-label" x="{left}" y="{height - 8}" text-anchor="start">{short_date(points[0][0])}</text>'
        f'<text class="chart-label" x="{width - right}" y="{height - 8}" text-anchor="end">{short_date(points[-1][0])}</text>'
    )
    coords = " ".join(f"{x(day):.1f},{y(odds):.1f}" for day, (_, odds) in zip(days, points))
    dots = "".join(
        f'<circle class="chart-dot" cx="{x(day):.1f}" cy="{y(odds):.1f}" r="3.5"/>'
        for day, (_, odds) in zip(days, points)
    )
    label = (
        f"{name}'s nomination odds from {short_date(points[0][0])} to {short_date(points[-1][0])}: "
        f"{pct(points[0][1])} to {pct(points[-1][1])}"
    )
    return (
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(label, quote=True)}">'
        f'{grid}{dates}<polyline class="chart-line" points="{coords}"/>{dots}</svg>'
    )


def render_candidate(rank: int, c: Json, site: Json, history: list[Json]) -> str:
    slug, name = c["slug"], c["name"]
    path = candidate_path(slug)
    weeks = [h for h in history if slug in h["odds"]]
    previous = next((h for h in reversed(history) if h["date"] < site["updated"]), None)
    field_size = len(site["candidates"])

    rows = []
    for h in reversed(weeks):
        week = short_date(h["date"])
        if h.get("headline"):
            week = f'<a href="{archive_path(h["date"])}">{week}</a>'
        week_rank = [s for s, _ in ranked(h)].index(slug) + 1
        rows.append(
            f'<tr><td><time datetime="{h["date"]}">{week}</time></td>'
            f'<td class="num">{week_rank}</td><td class="num">{pct(h["odds"][slug])}</td></tr>'
        )
    table = (
        f'<table class="odds-table"><caption>{escape(name)}\'s odds by week</caption>'
        '<thead><tr><th scope="col">Week</th><th scope="col" class="num">Rank</th>'
        f'<th scope="col" class="num">Odds</th></tr></thead><tbody>{"".join(rows)}</tbody></table>'
    )
    if len(weeks) >= 2:
        chart = odds_chart(name, [(h["date"], h["odds"][slug]) for h in weeks])
    else:
        chart = '<p class="panel-note">A chart appears here once there are two weeks of odds to compare.</p>'

    src = portrait(slug)
    if src:
        image = (src, *PORTRAIT_SIZE, f"Portrait of {name}")
    else:
        image = None
    description = clip(
        f"Our odds that {name} wins the 2028 Democratic nomination: {pct(c['odds'])}, "
        f"#{rank} of {field_size} in the field. {c['title']}. Odds history, outlook, and the latest news.",
        220,
    )
    person: Json = {"@type": "Person", "name": name, "jobTitle": c["title"]}
    if src:
        person["image"] = absolute(src)
    trail = [("Home", "/"), (name, path)]
    structured = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "ProfilePage",
                "url": absolute(path),
                "name": f"{name} 2028",
                "dateModified": schema_datetime(site["updated"]),
                "mainEntity": person,
            },
            breadcrumbs(trail),
        ],
    }
    move = movement(slug, c["odds"], previous)
    if move and previous:
        move = f'<p class="profile-move">{move} <span class="profile-since">since {short_date(previous["date"])}</span></p>'
    body = f"""
      {breadcrumb_nav(trail)}
      <section class="panel profile" aria-labelledby="profile-name">
        <div class="profile-photo">{portrait_image(c, lazy=False)}</div>
        <div class="profile-intro">
          <p class="eyebrow">#{rank} of {field_size} in the race</p>
          <h1 class="profile-name" id="profile-name">{escape(name)}</h1>
          <p class="profile-title">{escape(c["title"])}</p>
          <span class="status status-{c["status"]}">{STATUSES[c["status"]]}</span>
          <p class="profile-odds"><strong>{pct(c["odds"])}</strong> chance of winning the Democratic nomination, by our estimate as of <time datetime="{site["updated"]}">{long_date(site["updated"])}</time>.</p>
          {move}
        </div>
      </section>
      <section class="panel" aria-labelledby="history-title">
        <h2 class="panel-title" id="history-title">Odds History</h2>
        {chart}
        <details class="odds-details"{" open" if len(weeks) < 2 else ""}>
          <summary>Week-by-week odds</summary>
          {table}
        </details>
      </section>
      <section class="panel profile-details" aria-label="Background and news">
        {"".join(render_details(c))}{photo_credit(c)}
      </section>
      <p class="back-links"><a href="/#{slug}">Back to the full field</a></p>"""
    title = f"{name} 2028: Odds and News | {SITE_NAME}"
    return render_layout(path, title, description, body, site["updated"], structured, "profile", image)


def snapshot_name(slug: str, snapshot: Json, current: dict[str, str]) -> str:
    return snapshot.get("names", {}).get(slug) or current.get(slug) or slug.replace("-", " ").title()


def render_edition(snapshot: Json, previous: Json | None, site: Json) -> str:
    iso = snapshot["date"]
    path = archive_path(iso)
    current = {c["slug"]: c["name"] for c in site["candidates"]}
    rows = []
    for rank, (slug, odds) in enumerate(ranked(snapshot), start=1):
        name = escape(snapshot_name(slug, snapshot, current))
        if slug in current:
            name = f'<a href="{candidate_path(slug)}">{name}</a>'
        rows.append(
            f'<tr><td class="num">{rank}</td><td>{name}</td>'
            f'<td class="num">{pct(odds)}</td><td class="num">{movement(slug, odds, previous)}</td></tr>'
        )
    field = snapshot["odds"].get(FIELD)
    if field is not None:
        rows.append(
            f'<tr><td></td><td>Someone not listed</td><td class="num">{pct(field)}</td>'
            f'<td class="num">{movement(FIELD, field, previous)}</td></tr>'
        )
    trail = [("Home", "/"), ("Past Editions", "/archive/"), (long_date(iso), path)]
    structured = {
        "@context": "https://schema.org",
        "@graph": [news_article(snapshot, path), breadcrumbs(trail)],
    }
    note = (
        "This is the current edition."
        if iso == site["updated"]
        else 'This edition is archived. <a href="/">Read the latest edition</a>.'
    )
    summary = "".join(f"<p>{escape(p)}</p>" for p in snapshot["summary"])
    body = f"""
      {breadcrumb_nav(trail)}
      <article class="panel brief" aria-labelledby="brief-title">
        <p class="eyebrow">Week of <time datetime="{iso}">{long_date(iso)}</time></p>
        <h1 class="brief-title" id="brief-title">{escape(snapshot["headline"])}</h1>
        {summary}
        <p class="brief-more">{note}</p>
      </article>
      <section class="panel" aria-labelledby="odds-title">
        <h2 class="panel-title" id="odds-title">The Race That Week</h2>
        <table class="odds-table">
          <caption>Nomination odds as of {long_date(iso)}</caption>
          <thead><tr><th scope="col" class="num">Rank</th><th scope="col">Candidate</th><th scope="col" class="num">Odds</th><th scope="col" class="num">Change</th></tr></thead>
          <tbody>{"".join(rows)}</tbody>
        </table>
      </section>
      <p class="back-links"><a href="/archive/">All past editions</a></p>"""
    title = f"{snapshot['headline']} | {SITE_NAME}, {short_date(iso)}"
    description = clip(snapshot["summary"][0])
    image = (*OG_IMAGE, f"{SITE_NAME} weekly brief for {long_date(iso)}")
    return render_layout(path, title, description, body, site["updated"], structured, "article", image)


def render_archive_index(editions: list[Json], site: Json) -> str:
    rows = "".join(
        f'<li><time datetime="{e["date"]}">{short_date(e["date"])}</time>'
        f'<div><a href="{archive_path(e["date"])}">{escape(e["headline"])}</a></div></li>'
        for e in reversed(editions)
    )
    trail = [("Home", "/"), ("Past Editions", "/archive/")]
    description = "Every weekly edition of Project 2028, with that week's brief and nomination odds for the 2028 Democratic field."
    structured = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "name": f"Past Editions | {SITE_NAME}",
                "url": absolute("/archive/"),
                "description": description,
                "dateModified": schema_datetime(site["updated"]),
            },
            breadcrumbs(trail),
        ],
    }
    body = f"""
      {breadcrumb_nav(trail)}
      <section class="panel" aria-labelledby="archive-title">
        <h1 class="panel-title" id="archive-title">Past Editions</h1>
        <p class="panel-note">Each week's brief and odds, frozen as published. Newest first.</p>
        <ul class="dated">{rows}</ul>
      </section>"""
    return render_layout("/archive/", f"Past Editions | {SITE_NAME}", description, body, site["updated"], structured)


def render_sitemap(pages: list[tuple[str, str]]) -> str:
    urls = "".join(
        f"""
  <url>
    <loc>{absolute(path)}</loc>
    <lastmod>{lastmod}</lastmod>
  </url>"""
        for path, lastmod in pages
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}
</urlset>
"""


def write_page(path: str, html: str) -> None:
    target = ROOT / path.strip("/") / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html)


def main() -> None:
    site: Json = json.loads(DATA.read_text())
    validate(site)
    site["candidates"].sort(key=lambda c: c["odds"], reverse=True)
    history = record_history(site)
    updated = site["updated"]

    # Build-owned directories: wipe and regenerate so dropped candidates disappear.
    for generated in (CANDIDATES_DIR, ARCHIVE_DIR):
        if generated.is_dir():
            shutil.rmtree(generated)

    (ROOT / "index.html").write_text(render_page(site, history))
    pages = [("/", updated), ("/archive/", updated)]

    for rank, c in enumerate(site["candidates"], start=1):
        path = candidate_path(c["slug"])
        write_page(path, render_candidate(rank, c, site, history))
        pages.append((path, updated))

    editions = []
    for i, snapshot in enumerate(history):
        if not snapshot.get("headline"):
            continue
        previous = history[i - 1] if i else None
        path = archive_path(snapshot["date"])
        write_page(path, render_edition(snapshot, previous, site))
        pages.append((path, snapshot["date"]))
        editions.append(snapshot)
    write_page("/archive/", render_archive_index(editions, site))

    (ROOT / "sitemap.xml").write_text(render_sitemap(pages))
    print(
        f"Built the site for {updated}: {len(site['candidates'])} candidate pages, "
        f"{len(editions)} archived editions."
    )


if __name__ == "__main__":
    main()
