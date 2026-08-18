#!/usr/bin/env python3
"""Check whether each group in index.html has published the drinkup, and collect logos.

Reads the group list from the inline JSON in index.html, fetches every group page,
and looks for an upcoming event matching a keyword (default "drinkup"). Writes a
console table, downloads logos into logos/, writes drinkup-report.json, and adds a
"logo" field to each group in index.html.

Standard library only. Run it from anywhere:

    python3 scripts/check_groups.py
    python3 scripts/check_groups.py --keyword drinkup --no-patch
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html import unescape
from urllib.parse import urljoin, urlparse

# The repo root, one level up from scripts/ — every path below is relative to it.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "index.html")
LOGO_DIR = os.path.join(ROOT, "logos")

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
TIMEOUT = 20
RETRIES = 2

PUBLISHED, NONE, UNKNOWN, ERROR = "published", "none", "unknown", "error"

# Enough visible text that "the keyword isn't here" means something.
READABLE_TEXT_MIN = 500


# --------------------------------------------------------------------------- http

def fetch(url):
    """GET a URL, following redirects. Returns (body_bytes, final_url, content_type)."""
    last = None
    for attempt in range(RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml,image/*;q=0.8,*/*;q=0.5",
                "Accept-Language": "en-US,en;q=0.9,hr;q=0.8",
            })
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return resp.read(), resp.geturl(), resp.headers.get("Content-Type", "")
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            last = exc
            if attempt < RETRIES:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(str(last))


def fetch_html(url):
    body, final_url, _ = fetch(url)
    return body.decode("utf-8", "replace"), final_url


# --------------------------------------------------------------------- html digging

def script_json(html, pattern):
    """Parse the JSON body of the first <script> tag matching a regex on its attributes."""
    m = re.search(r'<script[^>]*%s[^>]*>(.*?)</script>' % pattern, html, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1).strip())
    except json.JSONDecodeError:
        return None


def next_data(html):
    return script_json(html, r'id="__NEXT_DATA__"')


def ld_json_blocks(html):
    out = []
    for raw in re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S):
        try:
            parsed = json.loads(raw.strip())
        except json.JSONDecodeError:
            continue
        out.extend(parsed if isinstance(parsed, list) else [parsed])
    return out


def meta_content(html, prop):
    m = re.search(r'<meta[^>]+(?:property|name)="%s"[^>]+content="([^"]*)"' % re.escape(prop), html)
    if not m:
        m = re.search(r'<meta[^>]+content="([^"]*)"[^>]+(?:property|name)="%s"' % re.escape(prop), html)
    return unescape(m.group(1)) if m else None


def icon_href(html):
    for m in re.finditer(r'<link[^>]+rel="([^"]*icon[^"]*)"[^>]*>', html, re.I):
        href = re.search(r'href="([^"]+)"', m.group(0))
        if href:
            return unescape(href.group(1))
    return None


def visible_text(html):
    body = re.sub(r'(?is)<(script|style|noscript)\b.*?</\1>', " ", html)
    body = re.sub(r'(?s)<!--.*?-->', " ", body)
    body = re.sub(r'(?s)<[^>]+>', " ", body)
    return re.sub(r'\s+', " ", unescape(body)).strip()


def walk(node):
    """Yield every dict nested anywhere inside a parsed JSON structure."""
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)


def parse_dt(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# -------------------------------------------------------------------------- adapters
#
# Each adapter takes the group URL and returns (events, logo_url, dated).
#   events -> list of {title, description, url, starts_at}
#   dated  -> True when starts_at is trustworthy, so past events can be ruled out.

def adapter_meetup(url):
    events_url = url if url.rstrip("/").endswith("/events") else url.rstrip("/") + "/events/"
    html, _ = fetch_html(events_url)

    events = []
    data = next_data(html)
    if data:
        state = data.get("props", {}).get("pageProps", {}).get("__APOLLO_STATE__", {})
        for key, node in state.items():
            if not key.startswith("Event:") or not isinstance(node, dict):
                continue
            events.append({
                "title": node.get("title") or "",
                "description": node.get("description") or "",
                "url": node.get("eventUrl") or events_url,
                "starts_at": parse_dt(node.get("dateTime")),
            })

    logo = None
    for block in ld_json_blocks(html):
        if block.get("@type") != "Organization" or block.get("name") == "Meetup":
            continue
        candidate = block.get("logo") or block.get("image")
        if isinstance(candidate, dict):
            candidate = candidate.get("url")
        if candidate:
            logo = candidate
            break
    return events, logo or meta_content(html, "og:image"), True


def adapter_luma(url):
    html, final_url = fetch_html(url)

    events, seen = [], set()
    data = next_data(html)
    for node in walk(data or {}):
        name, start = node.get("name"), node.get("start_at")
        if not isinstance(name, str) or not isinstance(start, str):
            continue
        slug = node.get("url") or node.get("api_id") or name
        if slug in seen:
            continue
        seen.add(slug)
        events.append({
            "title": name,
            "description": node.get("description") or node.get("one_liner") or "",
            "url": urljoin("https://lu.ma/", str(node.get("url") or "")) if node.get("url") else final_url,
            "starts_at": parse_dt(start),
        })

    logo = None
    for node in walk(data or {}):
        candidate = node.get("avatar_url") or node.get("cover_url")
        if isinstance(candidate, str) and candidate.startswith("http"):
            logo = candidate
            break
    return events, logo or meta_content(html, "og:image"), True


def adapter_gdg(url):
    html, final_url = fetch_html(url)
    data = next_data(html) or {}
    props = data.get("props", {}).get("pageProps", {})

    events = []
    upcoming = props.get("prerenderData", {}).get("upcomingEvents") or {}
    for node in upcoming.get("results") or []:
        events.append({
            "title": node.get("title") or "",
            "description": " ".join(filter(None, [
                node.get("description_short") or "",
                node.get("description") or "",
            ])),
            "url": node.get("url") or final_url,
            "starts_at": parse_dt(node.get("start_date")),
        })

    chapter = props.get("chapterData") or {}
    logo = chapter.get("cropped_logo_url") or chapter.get("logo") or None
    return events, logo or meta_content(html, "og:image"), True


# A group on its own domain usually still runs its events on a platform, and
# links to it. Following that link gets us real dates instead of a text guess.
PLATFORM_LINKS = [
    (re.compile(r'https?://(?:www\.)?meetup\.com/([A-Za-z0-9][A-Za-z0-9_-]*)', re.I),
     "https://www.meetup.com/%s/"),
    (re.compile(r'https?://lu\.ma/([A-Za-z0-9][A-Za-z0-9_-]*)', re.I),
     "https://lu.ma/%s"),
    (re.compile(r'https?://gdg\.community\.dev/([A-Za-z0-9][A-Za-z0-9_-]*)', re.I),
     "https://gdg.community.dev/%s/"),
]

# Meetup paths that are site chrome rather than a group.
NOT_A_GROUP = {"find", "pro", "help", "about", "members", "topics", "cities", "blog", "home"}


def linked_platform_url(html):
    """The group page of the first event platform this page links to, if any."""
    for pattern, template in PLATFORM_LINKS:
        for m in pattern.finditer(html):
            slug = m.group(1)
            if slug.lower() in NOT_A_GROUP:
                continue
            return template % slug
    return None


def adapter_generic(url):
    """Fallback: no structured events, so read the page text and stay honest about it."""
    html, final_url = fetch_html(url)

    # On a group's own site the app icon is the group mark, square and sized for
    # a small box. og:image is a share banner — often a wide lockup that shrinks
    # to nothing in the tile — so it is only the fallback here.
    icon = icon_href(html)
    logo = urljoin(final_url, icon) if icon else meta_content(html, "og:image")

    linked = linked_platform_url(html)
    if linked and (urlparse(linked).hostname or "").lower() != (urlparse(final_url).hostname or "").lower():
        delegate = adapter_for(linked)
        if delegate is not adapter_generic:
            events, platform_logo, dated = delegate(linked)
            # The group's own site is the better source for its logo.
            return events, logo or platform_logo, dated

    text = visible_text(html)
    events = [{"title": "", "description": text, "url": final_url, "starts_at": None}] if text else []
    return events, logo, False


ADAPTERS = [
    ("meetup.com", adapter_meetup),
    ("lu.ma", adapter_luma),
    ("gdg.community.dev", adapter_gdg),
]


def adapter_for(url):
    host = (urlparse(url).hostname or "").lower()
    for suffix, fn in ADAPTERS:
        if host == suffix or host.endswith("." + suffix):
            return fn
    return adapter_generic


# ---------------------------------------------------------------------------- check

def check_group(group, keyword):
    url = group["url"]
    result = {
        "group": group["name"],
        "url": url,
        "status": ERROR,
        "detail": "",
        "event_title": None,
        "event_url": None,
        "logo_url": None,
        "error": None,
    }

    try:
        events, logo, dated = adapter_for(url)(url)
    except Exception as exc:                              # noqa: BLE001 - reported, never fatal
        result["error"] = str(exc)
        result["detail"] = str(exc)
        return result

    result["logo_url"] = logo
    needle = keyword.lower()
    now = datetime.now(timezone.utc)

    if dated:
        matches = [
            e for e in events
            if needle in (e["title"] + " " + e["description"]).lower()
            and e["starts_at"] and e["starts_at"] >= now
        ]
        matches.sort(key=lambda e: e["starts_at"])
        if matches:
            hit = matches[0]
            result.update(status=PUBLISHED, event_title=hit["title"], event_url=hit["url"],
                          detail=hit["starts_at"].strftime("%Y-%m-%d"))
        else:
            result["status"] = NONE
            result["detail"] = "%d upcoming event(s), none matching" % sum(
                1 for e in events if e["starts_at"] and e["starts_at"] >= now)
        return result

    # Undated source: absence of the keyword only means something if we could read the page.
    text = events[0]["description"] if events else ""
    if needle in text.lower():
        result.update(status=UNKNOWN, event_url=url, detail="keyword on page, no date to check")
    elif len(text) >= READABLE_TEXT_MIN:
        result.update(status=NONE, detail="no mention on page")
    else:
        result.update(status=UNKNOWN, detail="page renders client-side, cannot read it")
    return result


# --------------------------------------------------------------------------- outputs

def slugify(name):
    return re.sub(r'-+', "-", re.sub(r'[^a-z0-9]+', "-", name.lower())).strip("-")


def download_logos(results):
    os.makedirs(LOGO_DIR, exist_ok=True)
    for r in results:
        if not r["logo_url"]:
            continue
        try:
            body, final_url, ctype = fetch(r["logo_url"])
        except Exception as exc:                          # noqa: BLE001
            print("  ! logo download failed for %s: %s" % (r["group"], exc))
            continue
        ext = {
            "image/webp": ".webp", "image/jpeg": ".jpg", "image/png": ".png",
            "image/gif": ".gif", "image/svg+xml": ".svg",
        }.get(ctype.split(";")[0].strip().lower())
        if not ext:
            ext = os.path.splitext(urlparse(final_url).path)[1] or ".img"
        path = os.path.join(LOGO_DIR, slugify(r["group"]) + ext)
        with open(path, "wb") as fh:
            fh.write(body)
        r["logo_file"] = os.path.relpath(path, ROOT)


GROUP_FIELDS = ("name", "url", "logo", "event")


def render_groups(groups):
    """Re-emit the groups array. Same input always produces the same bytes."""
    lines = []
    for i, g in enumerate(groups):
        tail = "" if i == len(groups) - 1 else ","
        fields = [(k, g[k]) for k in GROUP_FIELDS if g.get(k)]
        width = max(len('"%s":' % k) for k, _ in fields)
        for j, (key, value) in enumerate(fields):
            open_brace = "    { " if j == 0 else "      "
            close = " }" + tail if j == len(fields) - 1 else ","
            lines.append("%s%-*s %s%s" % (open_brace, width, '"%s":' % key,
                                          json.dumps(value), close))
    return "\n".join(lines)


def patch_index(html, groups, results):
    by_name = {r["group"]: r for r in results}
    updated = []
    for g in groups:
        entry = {"name": g["name"], "url": g["url"]}
        result = by_name.get(g["name"], {})

        # Keep the previous logo when this run could not find one.
        logo = result.get("logo_url") or g.get("logo")
        if logo:
            entry["logo"] = logo

        # Only a confirmed upcoming event earns a link. A group that has since
        # unpublished loses it — except after an error, where we know nothing.
        if result.get("status") == PUBLISHED:
            entry["event"] = result["event_url"]
        elif result.get("status") == ERROR and g.get("event"):
            entry["event"] = g["event"]

        updated.append(entry)

    m = re.search(r'(\n  "groups": \[\n)(.*?)(\n  \]\n)', html, re.S)
    if not m:
        raise RuntimeError('could not find the "groups" array in index.html')
    return html[:m.start(2)] + render_groups(updated) + html[m.end(2):]


STATUS_LABEL = {
    PUBLISHED: "PUBLISHED",
    NONE: "not posted",
    UNKNOWN: "unknown",
    ERROR: "ERROR",
}


def print_table(results, keyword):
    width = max(len(r["group"]) for r in results)
    print('\nMatching "%s" in upcoming events\n' % keyword)
    for r in results:
        print("  %-*s  %-10s  %s" % (width, r["group"], STATUS_LABEL[r["status"]],
                                     r["event_title"] or r["detail"]))
        if r["event_url"] and r["status"] == PUBLISHED:
            print("  %-*s  %-10s  %s" % (width, "", "", r["event_url"]))

    counts = {s: sum(1 for r in results if r["status"] == s) for s in (PUBLISHED, NONE, UNKNOWN, ERROR)}
    print("\n  %d published, %d not posted, %d unknown, %d errors\n" % (
        counts[PUBLISHED], counts[NONE], counts[UNKNOWN], counts[ERROR]))


# ------------------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser(
        description="Check whether each group has published the drinkup, and collect logos.")
    ap.add_argument("--keyword", default="drinkup", help='what to look for (default: "drinkup")')
    ap.add_argument("--no-logos", action="store_true", help="skip downloading into logos/")
    ap.add_argument("--no-patch", action="store_true", help="leave index.html alone")
    ap.add_argument("--json", dest="json_path", default=os.path.join(ROOT, "drinkup-report.json"),
                    help="where to write the report (default: drinkup-report.json)")
    args = ap.parse_args()

    with open(INDEX, encoding="utf-8") as fh:
        html = fh.read()
    block = re.search(r'<script type="application/json" id="data">(.*?)</script>', html, re.S)
    if not block:
        sys.exit("could not find the inline data block in index.html")
    groups = json.loads(block.group(1)).get("groups", [])
    if not groups:
        sys.exit("no groups listed in index.html")

    results = []
    for g in groups:
        print("checking %s ..." % g["name"])
        results.append(check_group(g, args.keyword))

    if not args.no_logos:
        print("\ndownloading logos ...")
        download_logos(results)

    print_table(results, args.keyword)

    with open(args.json_path, "w", encoding="utf-8") as fh:
        json.dump({
            "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "keyword": args.keyword,
            "groups": results,
        }, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print("report: %s" % os.path.relpath(args.json_path, ROOT))

    if not args.no_patch:
        patched = patch_index(html, groups, results)
        if patched != html:
            with open(INDEX, "w", encoding="utf-8") as fh:
                fh.write(patched)
            print("index.html: logo URLs updated")
        else:
            print("index.html: already up to date")


if __name__ == "__main__":
    main()
