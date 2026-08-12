# Zagreb Developers Drinkup

One drinkup, several Zagreb developer meetup groups, same place and time.

Site: **https://zagreb-developers.github.io/drinkup/** — this is the only URL that goes into announcements. It never changes.

## Repo

```
docs/index.html          the site + the group list (inline JSON near the bottom)
text/announcement.txt Croatian and English announcement
```

No build step. GitHub Pages serves `/docs` from `main`.

## Posting

Paste the whole announcement (hr or en) into Meetup or Luma and post or edit to your liking. The URL on its own line auto-links in both editors, so there's no formatting to redo per group and no links to check.

## Adding or removing a group

Edit the JSON block at the bottom of `docs/index.html` and open a pull request:

```json
{ "name": "Your Group", "url": "https://www.meetup.com/your-group/" }
```

Keep the list alphabetical. It's valid JSON — double quotes, no trailing commas.

Groups that sit an edition out get removed for that edition and added back later. Nobody removes their own group from the list: every group posts the same text and links to the same complete list.

## Running an edition

1. Update `event` in `docs/index.html` — date, time, venue, map link. If the date isn't set yet, empty the object (`"event": {}`) and the page says so instead of showing a stale date.
2. Update the date and venue lines in both `text/` files. Nothing else in them should need changing — the group list isn't in the text, only the link.
3. Freeze the lineup about a week out, then tell all groups to post.

The `text/` files contain only pasteable text, no comments or instructions — anything in there might end up in a Meetup post.
