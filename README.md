# Zagreb Developers Drinkup

One drinkup, several Zagreb developer meetup groups, same place and time.

Site: **https://zgdev.hr** — this is the only URL that goes into announcements. It never changes.

## Repo

```
docs/index.html          the site + the group list (inline JSON near the bottom)
text/announcement.hr.txt Croatian announcement, paste as-is
text/announcement.en.txt English announcement, paste as-is
```

No build step. GitHub Pages serves `/docs` from `main`.

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

## Posting

Paste the whole file into Meetup or Luma. The URL on its own line auto-links in both editors, so there's no formatting to redo per group and no links to check.

## Who maintains this

One person per edition, rotating. Current: **[name]**.

## Feedback form

The "How was it?" band on the site is hidden until a URL is set. The morning after the drinkup, paste the survey link into `"feedback"` in `docs/index.html`:

```json
"feedback": "https://docs.google.com/forms/d/e/FORM_ID/viewform",
```

Set it back to `""` before the next edition's announcement goes out.

Strip `?usp=sharing&ouid=...` from Google Forms links before committing them — `ouid` is the account ID of whoever copied the link and doesn't belong in a public repo.
