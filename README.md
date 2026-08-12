# Zagreb Developers Drinkup

One drinkup, several Zagreb developer meetup groups, same place and time.

Site: **https://zagreb-developers.github.io/drinkup/** — this is the only URL that goes into announcements. It never changes.

## Repo

```
index.html               the site + the group list (inline JSON near the bottom)
announcement.txt         Croatian and English announcement
event_cover_image.jpeg   cover image (on the page and in social link previews)
```

No build step. GitHub Pages serves the repo root from `main`.

## Posting

Paste the whole announcement (hr or en) into Meetup or Luma and post or edit to your liking. The URL on its own line auto-links in both editors, so there's no formatting to redo per group and no links to check.

## Adding or removing a group

Edit the JSON block at the bottom of `index.html` and open a pull request:

```json
{ "name": "Your Group", "url": "https://www.meetup.com/your-group/" }
```

Keep the list alphabetical. It's valid JSON — double quotes, no trailing commas.

Groups that sit an edition out get removed for that edition and added back later. Nobody removes their own group from the list: every group posts the same text and links to the same complete list.

## Running an edition

1. Update `event` in `index.html` — date, time, venue, map link. If the date isn't set yet, empty the object (`"event": {}`) and the page says so instead of showing a stale date.
2. Update the date and venue lines in both languages in `announcement.txt`. Nothing else in it should need changing — the group list isn't in the text, only the link.
3. Freeze the lineup about a week out, then tell all groups to post.

`announcement.txt` contains only pasteable text, no comments or instructions — anything in there might end up in a Meetup post.
