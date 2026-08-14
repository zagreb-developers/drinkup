# Zagreb Developers Drinkup

One drinkup, several Zagreb developer meetup groups, same place and time.

Site: **https://zagreb-developers.github.io/drinkup/** — this is the only URL that goes into announcements. It never changes.

## Repo

```
index.html               the site + the group list (inline JSON near the bottom)
announcement.txt         Croatian and English announcement
event_cover_image.jpeg   cover image (on the page and in social link previews)
check_groups.py          checks who has posted, collects group logos
logos/                   group logos, downloaded by the script
```

No build step. GitHub Pages serves the repo root from `main`.

## Posting

Paste the whole announcement (hr or en) into Meetup or Luma and post or edit to your liking. The URL on its own line auto-links in both editors, so there's no formatting to redo per group and no links to check.

## Adding or removing a group

Edit the JSON block at the bottom of `index.html` and open a pull request:

```json
{ "name": "Your Group",
  "url":  "https://www.meetup.com/your-group/" },
```

Keep the list alphabetical. It's valid JSON — double quotes, no trailing commas. Leave `logo` out; `check_groups.py` fills it in.

Groups that sit an edition out get removed for that edition and added back later. Nobody removes their own group from the list: every group posts the same text and links to the same complete list.

## Running an edition

1. Update `event` in `index.html` — date, time, venue, map link. If the date isn't set yet, empty the object (`"event": {}`) and the page says so instead of showing a stale date.
2. Update the date and venue lines in both languages in `announcement.txt`. Nothing else in it should need changing — the group list isn't in the text, only the link.
3. Freeze the lineup about a week out, then tell all groups to post.
4. Run `python3 check_groups.py` to see who actually posted, and chase the rest.

`announcement.txt` contains only pasteable text, no comments or instructions — anything in there might end up in a Meetup post.

## Checking who posted

```
python3 check_groups.py
```

Python 3, standard library only — nothing to install. It reads the group list from `index.html`, opens every group page, and looks for an upcoming event mentioning "drinkup":

```
  Golang ZG                      PUBLISHED   GolangZG @ Zagreb Developers Drinkup, August 2026
                                             https://www.meetup.com/golang-zg/events/316072304/
  Karlovac Developers            not posted  0 upcoming event(s), none matching
  ZgPHP                          unknown     page renders client-side, cannot read it

  5 published, 4 not posted, 1 unknown, 0 errors
```

`unknown` means the script couldn't tell — check that group by hand. ZgPHP is always `unknown` because its site renders in the browser and there's nothing to read in the HTML.

Every run also downloads each group's logo into `logos/`, writes `drinkup-report.json` (gitignored), and adds a `"logo"` URL to each group in `index.html`. Nothing on the page changes — the field is there for whenever we want to show logos. Re-running with the same results leaves `index.html` untouched.

| Flag | |
|---|---|
| `--keyword TEXT` | look for something other than "drinkup" |
| `--no-logos` | skip the `logos/` download |
| `--no-patch` | leave `index.html` alone |
| `--json PATH` | write the report somewhere else |

The logo is whatever each platform serves as the group image, so quality varies — some groups have set a real logo, others a photo from a past meetup.
