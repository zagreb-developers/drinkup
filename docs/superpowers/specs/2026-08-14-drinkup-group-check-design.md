# check_groups.py — did the groups post the drinkup?

Design, 2026-08-14.

## Problem

Running an edition means telling ten groups to post the announcement, then chasing
the ones that haven't. Checking by hand means opening ten pages. Separately, the
site has no group logos, and there's no record of where each group's logo lives.

One script answers both: for each group in `index.html`, has an upcoming event
matching "drinkup" been published, and what is the group's logo?

## Scope

- Reports status; it does not post, remind, or gate anything. Exit code is always 0.
- Reads the group list from `index.html`. No second copy of the list anywhere.
- Python 3, standard library only. No `pip install`, no headless browser.
  All four platforms serve their event data in the initial HTML response, verified
  by probe on 2026-08-14.

## Flow

1. Read `index.html`, extract `<script type="application/json" id="data">`, parse
   `groups`.
2. For each group, fetch its URL with a browser `User-Agent` (`urllib.request`,
   20s timeout, 2 retries with backoff).
3. Dispatch on hostname to an adapter. Each adapter returns
   `(events, logo_url)`, where an event is `{title, description, url, starts_at}`.
4. Match: case-insensitive substring search for the keyword in title +
   description, restricted to events with `starts_at` in the future.
5. Emit the four outputs.

Groups are fetched sequentially. Ten requests is a few seconds and keeps the
failure output readable; concurrency would buy nothing here.

## Adapters

| Host | Events | Logo |
|---|---|---|
| `meetup.com` | fetch `<url>events/`, parse `<script id="__NEXT_DATA__">`, take `props.pageProps.__APOLLO_STATE__` entries keyed `Event:*` (`title`, `description`, `dateTime`, `eventUrl`) | JSON-LD `Organization.logo`, fallback `og:image` |
| `lu.ma` | `__NEXT_DATA__`, collect objects with `name` + `start_at`; event URL is `https://lu.ma/<url>` | `og:image` |
| `gdg.community.dev` | `__NEXT_DATA__` → `props.pageProps.chapterData.upcomingEvents` | `chapterData` picture/logo field, fallback `og:image` |
| anything else | follow the first Meetup/Luma/GDG link on the page and use that adapter; if there is none, strip tags and search the visible text | `og:image`, fallback `<link rel="icon">` |

Adapters are independent functions behind one signature. When a platform changes
its markup, exactly one function changes, and the others keep working.

## Statuses

| Status | Meaning |
|---|---|
| `published` | An upcoming event matched the keyword |
| `none` | Fetched fine, no upcoming event matched |
| `unknown` | Keyword found, but the adapter cannot prove the event is upcoming |
| `error` | Fetch or parse failed; the message is printed |

`unknown` exists because keyword matching alone is not enough. RubyZG's page
history contains "RubyZG July Drinkup" and "December drinkup @ Fakin Craft Bar".
On Meetup, Luma and GDG the adapter has real dates and filters those out. The
generic adapter has no dates, so a hit there is reported for a human to check
rather than counted as published.

A group on its own domain is the case the text fallback handles worst, and it
is the one most likely to recur as groups move off Meetup. Such a site almost
always still links to the platform it runs events on, so the generic adapter
follows that link and delegates, keeping the group's own logo. RubyZG moved to
`rubyzg.org` on 2026-08-14 and this is what keeps its event link working.

`www.zg-php.org` serves a 1.7 KB JavaScript shell with an empty `<body>` — its
content is rendered client-side. It will report `unknown` on every run, and its
logo comes from the favicon. That is the correct answer for that site, not a bug
to fix; ZgPHP has to be checked by hand.

## Outputs

All four run by default.

1. **Console table** — group, status, matched event title and URL, with a summary
   line (`3 published, 6 none, 1 unknown`).
2. **`logos/<slug>.<ext>`** — logo downloaded per group. Slug from the group name,
   lowercased, non-alphanumerics collapsed to `-`. Extension from the response
   `Content-Type`, defaulting to the URL suffix.
3. **`drinkup-report.json`** — `{group, url, status, event_title, event_url, logo_url, error}`
   per group, plus the keyword and a run timestamp.
4. **`index.html` patched** — a `"logo"` field holding the *remote* URL is added to
   each group entry. The page keeps a stable local copy in `logos/` while the
   inline JSON points at the hosted image, so the repo does not grow a second
   binary per group per edition.

The rendering JS and CSS are not touched. The page looks identical after a run.

### index.html rewriting

The group entries are currently single column-aligned lines. Logo URLs are too
long for that, so a patched entry becomes three lines:

```json
    { "name": "RubyZG",
      "url":  "https://www.meetup.com/rubyzg/",
      "logo": "https://secure.meetupstatic.com/photos/event/3/2/3/5/600_517452853.webp" },
```

The whole `groups` array is re-emitted by a small formatter rather than
patched line by line, so repeated runs are idempotent: a second run with the same
logos produces a byte-identical file. Groups with no logo found keep the
two-line form and are left without a `logo` field. Only the `groups` array is
rewritten — `event` and `feedback` keep their exact original text.

## Flags

| Flag | Effect |
|---|---|
| `--keyword TEXT` | Match something other than `drinkup` |
| `--no-logos` | Skip downloading into `logos/` |
| `--no-patch` | Leave `index.html` alone |
| `--json PATH` | Write the report elsewhere (default `drinkup-report.json`) |

## Errors

A group that fails to fetch or parse gets `error` status with the exception
message and does not stop the run — the other nine still report. Logo download
failures are reported but do not change the group's event status.

## Testing

Run against the live ten groups and check by hand. Expected on 2026-08-14, from
the probes already done: RubyZG `published`
("RubyZg @ Zagreb Developers Drinkup, August 2026", 2026-08-28), Elixir Zagreb
`published` ("ElixirZg @ Zagreb Developers Drinkup, August 2026", 2026-08-28),
ZgPHP `unknown`. Spot-check that the downloaded logos are the right images and
that a second run leaves `index.html` byte-identical.

No unit test suite. The script is a thin shell around live HTML whose shape is
the thing most likely to change; tests against captured fixtures would pass while
the real thing broke.

**Verified 2026-08-14:** 5 published (Elixir Zagreb, Golang ZG, RubyZG, Testival,
Zagreb Software Crafters), 4 not posted, ZgPHP `unknown`, 0 errors. All ten logos
downloaded as valid images. A second run left `index.html` byte-identical.

One thing the probes did not predict: what a platform calls the group logo is
sometimes a photo. Golang ZG and Testival serve real logos; RubyZG's Meetup group
photo is a crowd shot from a past meetup, and GDG Zagreb has never replaced the
platform's default chapter thumbnail. The script collects what each platform
serves, which is the most it can do.
