import os
import uuid
from datetime import datetime
from flask import (
    Flask, render_template, abort,
    redirect, url_for, request, flash
)
from werkzeug.utils import secure_filename

import helpers

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-change-me-in-production")

VALID_TEAMS = {"men", "women"}
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}

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
    """Save an uploaded image to static/images/<team>/ and return the relative path."""
    if not file or file.filename == "":
        return None
    if not allowed_file(file.filename):
        return None
    ext = file.filename.rsplit(".", 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    save_dir = os.path.join("static", "images", team)
    os.makedirs(save_dir, exist_ok=True)
    file.save(os.path.join(save_dir, unique_name))
    return f"images/{team}/{unique_name}"


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


# ── Admin: Dashboard ─────────────────────────────────────────────────────────

@app.route("/admin/")
def admin_dashboard():
    return render_template("admin/dashboard.html")


# ── Admin: Players ────────────────────────────────────────────────────────────

@app.route("/admin/<team>/players")
def admin_players(team):
    if team not in VALID_TEAMS:
        abort(404)
    data = helpers.load_json(f"data/{team}/players.json")
    return render_template("admin/players_list.html", team=team, players=data)


@app.route("/admin/<team>/players/add", methods=["GET", "POST"])
def admin_player_add(team):
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
    if team not in VALID_TEAMS:
        abort(404)
    data = helpers.load_json(f"data/{team}/coaches.json")
    return render_template("admin/coaches_list.html", team=team, coaches=data)


@app.route("/admin/<team>/coaches/add", methods=["GET", "POST"])
def admin_coach_add(team):
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
    if team not in VALID_TEAMS:
        abort(404)
    data = helpers.load_json(f"data/{team}/schedule.json")
    return render_template("admin/schedule_list.html", team=team, schedule=data)


@app.route("/admin/<team>/schedule/add", methods=["GET", "POST"])
def admin_schedule_add(team):
    if team not in VALID_TEAMS:
        abort(404)
    if request.method == "POST":
        entry = {
            "date":     request.form.get("date", "").strip(),
            "opponent": request.form.get("opponent", "").strip(),
            "location": request.form.get("location", "Home"),
            "venue":    request.form.get("venue", "").strip(),
            "result":   request.form.get("result", "").strip(),
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
    if team not in VALID_TEAMS:
        abort(404)
    data = helpers.load_json(f"data/{team}/schedule.json")
    if idx < 0 or idx >= len(data):
        abort(404)
    game = data[idx]
    if request.method == "POST":
        game["date"]     = request.form.get("date", "").strip()
        game["opponent"] = request.form.get("opponent", "").strip()
        game["location"] = request.form.get("location", "Home")
        game["venue"]    = request.form.get("venue", "").strip()
        game["result"]   = request.form.get("result", "").strip()
        data.sort(key=lambda g: g["date"])
        helpers.save_json(f"data/{team}/schedule.json", data)
        flash("Game updated.", "success")
        return redirect(url_for("admin_schedule", team=team))
    return render_template("admin/schedule_form.html", team=team, game=game, idx=idx, action="Edit")


@app.route("/admin/<team>/schedule/delete/<int:idx>", methods=["POST"])
def admin_schedule_delete(team, idx):
    if team not in VALID_TEAMS:
        abort(404)
    data = helpers.load_json(f"data/{team}/schedule.json")
    if 0 <= idx < len(data):
        data.pop(idx)
        helpers.save_json(f"data/{team}/schedule.json", data)
    flash("Game deleted.", "info")
    return redirect(url_for("admin_schedule", team=team))


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
