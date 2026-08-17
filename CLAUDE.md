# CLAUDE.md

A one-page static site for a joint drinkup of Zagreb's developer meetup groups, plus one
script that checks which groups have published the event. Read `README.md` first — it is
the human-facing runbook and stays authoritative for how an edition is run.

## Layout

```
index.html                the whole site: markup, CSS, JS, and the content as inline JSON
announcement.txt          pasteable Croatian + English announcement, nothing else
event_cover_image.jpeg    cover image, also the og:image
scripts/check_groups.py   checks who has posted, patches index.html, downloads logos
logos/                    downloaded logos, a local copy for posters — the page does not use them
docs/                     design notes
drinkup-report.json       written by the script, gitignored
```

## Rules of the project

**No build step, no dependencies.** GitHub Pages serves the repo root from `main`, so
`index.html` is shipped exactly as written. Do not add a bundler, a framework, npm, or an
external JS/CSS dependency. The only things loaded from elsewhere are the Barlow webfont and
the group logos, which are hotlinked from each platform. The script is Python 3 standard
library only — keep it that way.

**Content lives in the JSON block, not in code.** `index.html` ends with
`<script type="application/json" id="data">` holding `event`, `feedback` and `groups`. Any
change to dates, venue, survey link or the group list goes there. It must stay valid JSON
(double quotes, no trailing commas, no comments), because the page parses it at runtime and
the script rewrites the `groups` array with a regex on `\n  "groups": [\n ... \n  ]\n` —
reformatting that block will break the patcher.

**`logo` and `event` are generated.** Humans write only `name` and `url` for a group;
`scripts/check_groups.py` fills in the other two on every run. Don't hand-edit them, and
keep the list alphabetical.

**Everything user-facing is bilingual.** Croatian and English strings both exist in the DOM;
`body[data-lang]` hides one set via `[lang="hr"]` / `[lang="en"]`. New copy needs both
languages — in the `COPY` table for scripted text, or as a `hr`/`en` element pair in the
markup. Croatian is the default. Note the plural rule in `COPY.count.hr` (1 grupa, 2–4
grupe, 5+ grupa).

**Match the existing style.** The JS is ES5 in an IIFE: `var`, `function () {}`, no arrows,
no `const`/`let`, no template literals. Colours come from the custom properties in `:root`
(`--blue`, `--red`, `--ink`, …) — no raw hex in rules. The script uses `os.path` and plain
`%` formatting.

## The script

```
python3 scripts/check_groups.py                 # normal run
python3 scripts/check_groups.py --no-patch      # look, don't touch index.html
```

`ROOT` is the repo root, one level above `scripts/`; every path is derived from it, so the
script runs from any working directory. It reads the group list from `index.html`, fetches
each group page (Meetup, Luma, GDG, or a group's own site, following the platform link it
finds there), and matches a keyword — `drinkup` by default — against upcoming events.

Status handling is deliberate and worth preserving: `published` writes the event URL,
`none`/`unknown` drop it so the page never links a dead event, and `error` keeps whatever
was there because a failed fetch proves nothing. ZgPHP renders client-side and is always
`unknown` — that is expected, not a bug. A run that finds the same results leaves
`index.html` byte-identical.

## Editing announcement.txt

It contains only text meant to be pasted into Meetup and Luma. Never add comments,
instructions or TODOs to it — anything in that file can end up in a public post. The group
list is not in the announcement, only the site URL, which never changes.
