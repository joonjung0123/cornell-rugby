import csv
import io
import os
import re
import uuid
from datetime import datetime
from flask import (
    Flask, render_template, abort,
    redirect, url_for, request, flash, session
)
from werkzeug.utils import secure_filename

import helpers

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-change-me-in-production")

VALID_TEAMS = {"men", "women"}
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}

# ── Admin password helper ──────────────────────────────────────────────────────

def _admin_password() -> str:
    """Return the admin password from the environment, with a safe fallback."""
    return os.environ.get("ADMIN_PASSWORD", "cornellrugby-change-me")

def _admin_logged_in() -> bool:
    return session.get("admin_logged_in") is True

def _require_admin():
    """Return a redirect to the login page if not authenticated, else None."""
    if not _admin_logged_in():
        return redirect(url_for("admin_login", next=request.path))
    return None

# Make Python's enumerate available in Jinja2 templates
app.jinja_env.globals["enumerate"] = enumerate


@app.context_processor
def inject_now():
    return {"now": datetime.utcnow()}


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def save_upload(file, team, subfolder=""):
    """Save an uploaded image to static/images/<team>/[subfolder]/ and return the relative path."""
    if not file or file.filename == "":
        return None
    if not allowed_file(file.filename):
        return None
    ext = file.filename.rsplit(".", 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    parts = ["static", "images", team]
    if subfolder:
        parts.append(subfolder)
    save_dir = os.path.join(*parts)
    os.makedirs(save_dir, exist_ok=True)
    file.save(os.path.join(save_dir, unique_name))
    rel_parts = ["images", team]
    if subfolder:
        rel_parts.append(subfolder)
    rel_parts.append(unique_name)
    return "/".join(rel_parts)


# ── Home ──────────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    return render_template("home.html")


# ── Public team pages ─────────────────────────────────────────────────────────

@app.route("/<team>/players")
def players(team):
    if team not in VALID_TEAMS:
        abort(404)
    data = helpers.load_json(f"data/{team}/players.json")
    return render_template("team/players.html", team=team, players=data)


@app.route("/<team>/coaches")
def coaches(team):
    if team not in VALID_TEAMS:
        abort(404)
    data = helpers.load_json(f"data/{team}/coaches.json")
    return render_template("team/coaches.html", team=team, coaches=data)


@app.route("/<team>/schedule")
def schedule(team):
    if team not in VALID_TEAMS:
        abort(404)
    data = helpers.load_json(f"data/{team}/schedule.json")
    return render_template("team/schedule.html", team=team, schedule=data)


@app.route("/<team>/recruit")
def recruit(team):
    if team not in VALID_TEAMS:
        abort(404)
    return render_template("team/recruit.html", team=team)


@app.route("/<team>/fan")
def fan(team):
    if team not in VALID_TEAMS:
        abort(404)
    return render_template("team/fan.html", team=team)


# ── Admin: Login / Logout ─────────────────────────────────────────────────────

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("password") == _admin_password():
            session["admin_logged_in"] = True
            return redirect(request.args.get("next") or url_for("admin_dashboard"))
        flash("Incorrect password.", "error")
    return render_template("admin/login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))


# ── Admin: Dashboard ─────────────────────────────────────────────────────────

@app.route("/admin/")
def admin_dashboard():
    if (r := _require_admin()): return r
    return render_template("admin/dashboard.html")


# ── Admin: Players ────────────────────────────────────────────────────────────

@app.route("/admin/<team>/players")
def admin_players(team):
    if (r := _require_admin()): return r
    if team not in VALID_TEAMS:
        abort(404)
    data = helpers.load_json(f"data/{team}/players.json")
    return render_template("admin/players_list.html", team=team, players=data)


@app.route("/admin/<team>/players/add", methods=["GET", "POST"])
def admin_player_add(team):
    if (r := _require_admin()): return r
    if team not in VALID_TEAMS:
        abort(404)
    if request.method == "POST":
        photo_path = ""
        if "photo" in request.files:
            saved = save_upload(request.files["photo"], team)
            if saved:
                photo_path = saved
        entry = {
            "id": request.form.get("id", "").strip() or uuid.uuid4().hex[:8],
            "name":     request.form.get("name", "").strip(),
            "number":   request.form.get("number", "").strip(),
            "position": request.form.get("position", "").strip(),
            "year":     request.form.get("year", "").strip(),
            "hometown": request.form.get("hometown", "").strip(),
            "bio":      request.form.get("bio", "").strip(),
            "photo":    photo_path,
        }
        data = helpers.load_json(f"data/{team}/players.json")
        data.append(entry)
        helpers.save_json(f"data/{team}/players.json", data)
        flash(f"Player '{entry['name']}' added successfully.", "success")
        return redirect(url_for("admin_players", team=team))
    return render_template("admin/player_form.html", team=team, player=None, action="Add")


@app.route("/admin/<team>/players/edit/<player_id>", methods=["GET", "POST"])
def admin_player_edit(team, player_id):
    if (r := _require_admin()): return r
    if team not in VALID_TEAMS:
        abort(404)
    data = helpers.load_json(f"data/{team}/players.json")
    player = next((p for p in data if p["id"] == player_id), None)
    if player is None:
        abort(404)
    if request.method == "POST":
        if "photo" in request.files and request.files["photo"].filename:
            saved = save_upload(request.files["photo"], team)
            if saved:
                player["photo"] = saved
        player["name"]     = request.form.get("name", "").strip()
        player["number"]   = request.form.get("number", "").strip()
        player["position"] = request.form.get("position", "").strip()
        player["year"]     = request.form.get("year", "").strip()
        player["hometown"] = request.form.get("hometown", "").strip()
        player["bio"]      = request.form.get("bio", "").strip()
        helpers.save_json(f"data/{team}/players.json", data)
        flash(f"Player '{player['name']}' updated.", "success")
        return redirect(url_for("admin_players", team=team))
    return render_template("admin/player_form.html", team=team, player=player, action="Edit")


@app.route("/admin/<team>/players/delete/<player_id>", methods=["POST"])
def admin_player_delete(team, player_id):
    if (r := _require_admin()): return r
    if team not in VALID_TEAMS:
        abort(404)
    data = helpers.load_json(f"data/{team}/players.json")
    data = [p for p in data if p["id"] != player_id]
    helpers.save_json(f"data/{team}/players.json", data)
    flash("Player deleted.", "info")
    return redirect(url_for("admin_players", team=team))


# ── Admin: Coaches ────────────────────────────────────────────────────────────

@app.route("/admin/<team>/coaches")
def admin_coaches(team):
    if (r := _require_admin()): return r
    if team not in VALID_TEAMS:
        abort(404)
    data = helpers.load_json(f"data/{team}/coaches.json")
    return render_template("admin/coaches_list.html", team=team, coaches=data)


@app.route("/admin/<team>/coaches/add", methods=["GET", "POST"])
def admin_coach_add(team):
    if (r := _require_admin()): return r
    if team not in VALID_TEAMS:
        abort(404)
    if request.method == "POST":
        photo_path = ""
        if "photo" in request.files:
            saved = save_upload(request.files["photo"], team)
            if saved:
                photo_path = saved
        entry = {
            "id":    request.form.get("id", "").strip() or uuid.uuid4().hex[:8],
            "name":  request.form.get("name", "").strip(),
            "role":  request.form.get("role", "").strip(),
            "bio":   request.form.get("bio", "").strip(),
            "photo": photo_path,
        }
        data = helpers.load_json(f"data/{team}/coaches.json")
        data.append(entry)
        helpers.save_json(f"data/{team}/coaches.json", data)
        flash(f"Coach '{entry['name']}' added.", "success")
        return redirect(url_for("admin_coaches", team=team))
    return render_template("admin/coach_form.html", team=team, coach=None, action="Add")


@app.route("/admin/<team>/coaches/edit/<coach_id>", methods=["GET", "POST"])
def admin_coach_edit(team, coach_id):
    if (r := _require_admin()): return r
    if team not in VALID_TEAMS:
        abort(404)
    data = helpers.load_json(f"data/{team}/coaches.json")
    coach = next((c for c in data if c["id"] == coach_id), None)
    if coach is None:
        abort(404)
    if request.method == "POST":
        if "photo" in request.files and request.files["photo"].filename:
            saved = save_upload(request.files["photo"], team)
            if saved:
                coach["photo"] = saved
        coach["name"] = request.form.get("name", "").strip()
        coach["role"] = request.form.get("role", "").strip()
        coach["bio"]  = request.form.get("bio", "").strip()
        helpers.save_json(f"data/{team}/coaches.json", data)
        flash(f"Coach '{coach['name']}' updated.", "success")
        return redirect(url_for("admin_coaches", team=team))
    return render_template("admin/coach_form.html", team=team, coach=coach, action="Edit")


@app.route("/admin/<team>/coaches/delete/<coach_id>", methods=["POST"])
def admin_coach_delete(team, coach_id):
    if (r := _require_admin()): return r
    if team not in VALID_TEAMS:
        abort(404)
    data = helpers.load_json(f"data/{team}/coaches.json")
    data = [c for c in data if c["id"] != coach_id]
    helpers.save_json(f"data/{team}/coaches.json", data)
    flash("Coach deleted.", "info")
    return redirect(url_for("admin_coaches", team=team))


# ── Admin: Schedule ───────────────────────────────────────────────────────────

@app.route("/admin/<team>/schedule")
def admin_schedule(team):
    if (r := _require_admin()): return r
    if team not in VALID_TEAMS:
        abort(404)
    data = helpers.load_json(f"data/{team}/schedule.json")
    return render_template("admin/schedule_list.html", team=team, schedule=data)


@app.route("/admin/<team>/schedule/add", methods=["GET", "POST"])
def admin_schedule_add(team):
    if (r := _require_admin()): return r
    if team not in VALID_TEAMS:
        abort(404)
    if request.method == "POST":
        logo_path = ""
        if "logo" in request.files:
            saved = save_upload(request.files["logo"], team, subfolder="logos")
            if saved:
                logo_path = saved
        entry = {
            "date":       request.form.get("date", "").strip(),
            "opponent":   request.form.get("opponent", "").strip(),
            "location":   request.form.get("location", "Home"),
            "venue":      request.form.get("venue", "").strip(),
            "result":     request.form.get("result", "").strip(),
            "photos_url": request.form.get("photos_url", "").strip(),
            "logo":       logo_path,
        }
        data = helpers.load_json(f"data/{team}/schedule.json")
        data.append(entry)
        data.sort(key=lambda g: g["date"])
        helpers.save_json(f"data/{team}/schedule.json", data)
        flash(f"Game vs {entry['opponent']} added.", "success")
        return redirect(url_for("admin_schedule", team=team))
    return render_template("admin/schedule_form.html", team=team, game=None, action="Add")


@app.route("/admin/<team>/schedule/edit/<int:idx>", methods=["GET", "POST"])
def admin_schedule_edit(team, idx):
    if (r := _require_admin()): return r
    if team not in VALID_TEAMS:
        abort(404)
    data = helpers.load_json(f"data/{team}/schedule.json")
    if idx < 0 or idx >= len(data):
        abort(404)
    game = data[idx]
    if request.method == "POST":
        if "logo" in request.files and request.files["logo"].filename:
            saved = save_upload(request.files["logo"], team, subfolder="logos")
            if saved:
                game["logo"] = saved
        game["date"]       = request.form.get("date", "").strip()
        game["opponent"]   = request.form.get("opponent", "").strip()
        game["location"]   = request.form.get("location", "Home")
        game["venue"]      = request.form.get("venue", "").strip()
        game["result"]     = request.form.get("result", "").strip()
        game["photos_url"] = request.form.get("photos_url", "").strip()
        data.sort(key=lambda g: g["date"])
        helpers.save_json(f"data/{team}/schedule.json", data)
        flash("Game updated.", "success")
        return redirect(url_for("admin_schedule", team=team))
    return render_template("admin/schedule_form.html", team=team, game=game, idx=idx, action="Edit")


@app.route("/admin/<team>/schedule/delete/<int:idx>", methods=["POST"])
def admin_schedule_delete(team, idx):
    if (r := _require_admin()): return r
    if team not in VALID_TEAMS:
        abort(404)
    data = helpers.load_json(f"data/{team}/schedule.json")
    if 0 <= idx < len(data):
        data.pop(idx)
        helpers.save_json(f"data/{team}/schedule.json", data)
    flash("Game deleted.", "info")
    return redirect(url_for("admin_schedule", team=team))


# ── Admin: CSV Upload ─────────────────────────────────────────────────────────

# Map every variant the Google Form uses for team names → our internal keys
_TEAM_MAP = {
    "men's team": "men",
    "men":        "men",
    "women's team": "women",
    "women":      "women",
}

# Google Form column header → internal key (lowercase, stripped for matching)
_COL = {
    "name as it appears on the website":              "name",
    "for which team are you playing/coaching?":       "_team",
    "position":                                        "position",
    "graduation year":                                 "year",
    "hometown, state/province/country (example; ithaca, new york or toronto, ontario or christchurch, new zealand) \n\ndon't use abbreviations for state, i.e. ny should be spelled out to new york": "hometown",
    # shorter fallback key matched by substring below
    "full bio (optional but encouraged)":              "bio",
    "height in feet and inch (example 5'5\" or 6'0\")": "height",
    'weight in pounds (lbs)\n\nmen\'s team only\nwomen\'s team member, please enter 0': "weight",
    "major\n\nexample: mechanical engineering or undeclared": "major",
    "college or school enrolled":                      "college",
    "social media - instagram (optional)":             "instagram",
}

def _find_col(header: str) -> str | None:
    """Return the internal key for a CSV header, using exact then substring match."""
    h = header.strip().lower()
    if h in _COL:
        return _COL[h]
    # substring fallbacks for long/multiline headers
    if h.startswith("hometown"):
        return "hometown"
    if "full bio" in h:
        return "bio"
    if "weight in pounds" in h or "weight in lbs" in h:
        return "weight"
    if h.startswith("height"):
        return "height"
    if h.startswith("major"):
        return "major"
    if "college or school" in h:
        return "college"
    return None


def _make_id(name: str) -> str:
    """Turn a name into a URL-safe id slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or uuid.uuid4().hex[:8]


def _build_bio(row: dict, team: str = "men") -> str:
    """Combine height/weight/major/college into the bio if present.
    Weight is only included for the men's team."""
    parts = []
    h = row.get("height", "").strip()
    w = row.get("weight", "").strip()
    if h:
        parts.append(h)
    if team == "men" and w and w not in ("0", ""):
        parts.append(f"{w} lbs")
    major   = row.get("major",   "").strip()
    college = row.get("college", "").strip()
    if major:
        parts.append(major)
    if college:
        parts.append(college)
    extra = row.get("bio", "").strip()
    prefix = " · ".join(parts)
    if prefix and extra:
        return f"{prefix}\n{extra}"
    return prefix or extra


@app.route("/admin/upload-csv", methods=["GET", "POST"])
def admin_upload_csv():
    if (r := _require_admin()): return r
    if request.method == "POST":
        f = request.files.get("csvfile")
        if not f or f.filename == "":
            flash("No file selected.", "error")
            return redirect(url_for("admin_upload_csv"))

        replace_mode = request.form.get("replace") == "1"

        # Read as UTF-8 text (handle BOM from Excel exports)
        raw = f.read().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(raw))

        # Build a normalised header→key mapping once from this file's actual headers
        col_map = {}  # actual_header → internal_key
        for header in (reader.fieldnames or []):
            key = _find_col(header)
            if key:
                col_map[header] = key

        added    = {"men": 0, "women": 0}
        skipped  = 0
        # In replace mode, track which teams have been wiped so we only do it once
        wiped    = set()
        # Accumulate all rows first so we can wipe-then-write atomically per team
        rows_by_team = {"men": [], "women": []}

        for raw_row in reader:
            # Normalise row using col_map
            row = {}
            for header, key in col_map.items():
                row[key] = raw_row.get(header, "").strip()

            name = row.get("name", "").strip()
            if not name:
                skipped += 1
                continue

            team_raw = row.get("_team", "").strip().lower()
            team = _TEAM_MAP.get(team_raw)
            if team is None:
                # try partial match
                for k, v in _TEAM_MAP.items():
                    if k in team_raw:
                        team = v
                        break
            if team is None:
                skipped += 1
                continue

            rows_by_team[team].append(row)

        # Now write each team's data
        for team, team_rows in rows_by_team.items():
            if not team_rows:
                continue

            path = f"data/{team}/players.json"

            if replace_mode:
                # Start with a clean slate
                players = []
            else:
                players = helpers.load_json(path)

            for row in team_rows:
                name = row.get("name", "").strip()
                player = {
                    "id":       _make_id(name),
                    "name":     name,
                    "number":   "",
                    "position": row.get("position", ""),
                    "year":     row.get("year", ""),
                    "hometown": row.get("hometown", ""),
                    "bio":      _build_bio(row, team),
                    "photo":    "",
                }

                existing = next((i for i, p in enumerate(players)
                                 if p.get("id") == player["id"]), None)
                if existing is not None:
                    # Preserve manually-set number and photo
                    player["number"] = players[existing].get("number", "")
                    player["photo"]  = players[existing].get("photo", "")
                    players[existing] = player
                else:
                    players.append(player)
                    added[team] += 1

            helpers.save_json(path, players)

        parts = []
        for team in ("men", "women"):
            if added[team]:
                parts.append(f"{added[team]} player(s) added to {team}'s roster")
        if skipped:
            parts.append(f"{skipped} row(s) skipped (missing name or unrecognised team)")
        flash(". ".join(parts) if parts else "No new players found in file.", "success")
        return redirect(url_for("admin_upload_csv"))

    return render_template("admin/upload_csv.html")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
