# Cornell Rugby Website — Developer Maintenance Guide

This guide identifies the current source of truth for routine website updates. It is intended for developers maintaining the application after launch!

## Before Making a Change

1. Work on a branch and review the change before merging.
2. Do not commit `.env` files, production secrets, or credentials. `.gitignore` already excludes these files.
3. Test locally with the application bound to `127.0.0.1`.
4. After production deployment, verify the public URL over HTTPS.

The application is a Flask app. Routes are defined in `app.py`; HTML is in `templates/`; styling and browser behavior are in `static/`; editable roster/schedule records are stored as JSON under `data/`.

## Quick Reference

| Change | Primary file(s) | Current edit location |
|---|---|---|
| Home-page title, tagline, copy, or quick links | `templates/home.html` | Lines 15–20 and 27–50 |
| Header logo, organization name, navigation, footer | `templates/base.html` | Lines 14–23, 30–66, and 77–85 |
| Logo image | `static/images/logo.png` | Replace the file; do not change its path |
| Recruit page wording, highlights, or Google Form | `templates/team/recruit.html` | Lines 6–18, 22–32, and 35–47 |
| Make Players, Coaches, Schedule, or Fan Zone live | Their corresponding template under `templates/team/` | Entire file; currently only renders the placeholder |
| Player data | `data/men/players.json`, `data/women/players.json` | Each JSON object in the array |
| Coach data | `data/men/coaches.json`, `data/women/coaches.json` | Each JSON object in the array |
| Schedule data | `data/men/schedule.json`, `data/women/schedule.json` | Each JSON object in the array |
| Team photos | `static/images/men/`, `static/images/women/` | Add/replace image files and update JSON `photo` value |
| Brand colors, font, layout | `static/css/style.css` | Lines 1–19 for global design variables |
| Mobile navigation and clickable bios | `static/js/main.js` | Lines 1–43 |
| Public URLs / add a page | `app.py` | Lines 50–92 for public routes |
| Admin content-management behavior | `app.py`, `templates/admin/` | Lines 97–305 and associated template |
| Python dependencies | `requirements.txt` | Entire file; use a lock file and scan dependencies before deployment |
| Gunicorn process configuration | `deploy/gunicorn.service` | Lines 5–19 |
| HTTPS / proxy / domain configuration | `deploy/nginx.conf` | Lines 1–39 |

## Content Updates

### Home Page

Edit `templates/home.html`.

- Update the organization name in the hero heading at line 15.
- Update the hero tagline at line 17.
- Update the Men's and Women's introductory text at lines 30 and 43.
- The quick-link lists are at lines 31–37 and 44–50. Each uses Flask `url_for(...)`; preserve the endpoint name unless the matching route in `app.py` has also been changed.

### Global Header, Navigation, and Footer

Edit `templates/base.html`.

- Header logo path and alt text: lines 14–23.
- Men’s menu: lines 35–48.
- Women’s menu: lines 51–64.
- Footer social links and contact email: lines 77–85.

Use complete `https://` URLs for external links. Retain `rel="noopener"` for links opened with `target="_blank"`.

### Logo and Images

- Header and home hero logo: replace `static/images/logo.png`.
- Men's roster images: store files in `static/images/men/`.
- Women's roster images: store files in `static/images/women/`.

Allowed uploaded image types are configured in `app.py` line 16 and validated by `allowed_file()` at lines 27–31. Each image path in a JSON record is relative to `static/`, for example `"images/men/player-name.jpg"`.

### Recruit Page and Google Form

Edit `templates/team/recruit.html`.

- Team-specific introductory text: lines 8–15.
- Email link: line 17.
- Program highlights: lines 25–31.
- Google Form embed: lines 35–47.

The iframe `src` must be the Google Form’s `/viewform?embedded=true` URL. The current form ID is `1FAIpQLSewyCgz_R2Fvdw66yf3-mziAXMPK4CiKpLNe9SldwgTV8bRew`. To replace it, update only the iframe `src` at line 37 and retain the `title`. Test the form for both `/men/recruit` and `/women/recruit` after changing it.

## Placeholder Pages

The following public templates intentionally contain only the shared site shell and an **Under Construction** heading:

- `templates/team/players.html`
- `templates/team/coaches.html`
- `templates/team/schedule.html`
- `templates/team/fan.html`

They are used by both Men’s and Women’s routes. Although `app.py` still loads player, coach, and schedule JSON for its corresponding routes (lines 57–78), the current placeholders do not display that data.

To make one of these pages live, replace the entire placeholder template with the approved page markup. Do not add live content to only one team unless the route/template architecture is changed: both teams currently share each template and use the `team` variable to differentiate output.

## Roster, Coaches, and Schedule Data

### Recommended Update Method: Admin UI

The admin routes are implemented in `app.py`:

- Players: lines 104–173
- Coaches: lines 178–241
- Schedule: lines 246–305

The dashboard is `templates/admin/dashboard.html`. The add/edit form fields are in `templates/admin/player_form.html`, `templates/admin/coach_form.html`, and `templates/admin/schedule_form.html`.

**Security requirement:** Do not expose `/admin/` publicly until authentication, authorization, and CSRF protection have been implemented. Administrative routes currently use the data mutation functions above but have no visible authentication guard in `app.py`.

### Direct JSON Edits

When the admin UI is unavailable, edit the team-specific JSON file directly and keep valid JSON syntax.

Player object structure:

```json
{
  "id": "unique-stable-id",
  "name": "Full Name",
  "number": "7",
  "position": "Flanker",
  "year": "Junior",
  "hometown": "Ithaca, NY",
  "bio": "Short player biography.",
  "photo": "images/men/full-name.jpg"
}
```

Coach object structure:

```json
{
  "id": "unique-stable-id",
  "name": "Full Name",
  "role": "Head Coach",
  "bio": "Short coach biography.",
  "photo": "images/women/full-name.jpg"
}
```

Schedule object structure:

```json
{
  "date": "2026-09-12",
  "opponent": "Opponent Name",
  "location": "Home",
  "venue": "Venue, City ST",
  "result": ""
}
```

Use dates in `YYYY-MM-DD` format. `location` should be `Home` or `Away`. Leave `result` blank for an upcoming game; use values such as `W 34-12` or `L 10-21` after a match. The admin add/edit routes sort schedule records by `date` at `app.py` lines 268 and 289.

JSON is loaded and written through `helpers.py`: `load_json()` (lines 5–11) and atomic `save_json()` (lines 14–26). Retain atomic writes if altering the persistence implementation.

## Application Behavior

### Routes and Endpoint Names

Public routes are defined in `app.py`:

- `/`: `home()` at lines 50–52
- `/<team>/players`: `players()` at lines 57–62
- `/<team>/coaches`: `coaches()` at lines 65–70
- `/<team>/schedule`: `schedule()` at lines 73–78
- `/<team>/recruit`: `recruit()` at lines 81–85
- `/<team>/fan`: `fan()` at lines 88–92

Only `men` and `women` are accepted as `team` values, configured by `VALID_TEAMS` at line 15. If adding a new team, update `VALID_TEAMS`, create all corresponding JSON files and image folders, and add matching navigation links.

### Styles and Browser JavaScript

- Global color, font, dimensions: CSS variables at `static/css/style.css` lines 1–19.
- Navigation/dropdown styles begin at line 36.
- Generic page headers begin at line 188.
- Recruit-page styles begin at line 356.
- Responsive rules begin near line 470.
- Mobile nav and team dropdown behavior: `static/js/main.js` lines 1–35.
- Player/coach bio-panel toggle behavior: `static/js/main.js` lines 37–43. This behavior will have no visible effect while roster and coach templates remain placeholders.

## Production Operations

### Environment Variables and Service

- Flask reads `SECRET_KEY` from the environment at `app.py` line 13. Set a unique production value outside version control; never rely on the development fallback.
- Configure the production service account, working directory, secret, and Gunicorn virtual-environment path in `deploy/gunicorn.service` lines 5–19.
- Gunicorn is bound only to `127.0.0.1:8000` at line 18. Keep it local; Nginx is the public HTTPS entry point.

### Domain and HTTPS

Edit `deploy/nginx.conf` only on the server:

- Actual domain names: lines 2–14.
- Let’s Encrypt certificate paths: lines 16–20.
- Absolute static-files path: lines 23–28.
- Local Gunicorn upstream: lines 30–38.

After deploying an approved change, use the deployment/update commands in `README.md` lines 139–145. Validate Nginx configuration before reloading it and verify HTTPS after DNS changes.

## Minimum Checks Before Release

From the repository root:

```bash
python3 -m compileall app.py helpers.py
```

Then start the site locally and check:

- `/`
- `/men/recruit` and `/women/recruit`
- each placeholder page shows **Under Construction**
- navigation works on desktop and mobile widths
- no secrets or `.env` files are included in the changes

For a production release, also confirm the web server serves the site over HTTPS, the `SECRET_KEY` is set, and the admin interface is not exposed without approved access controls.
