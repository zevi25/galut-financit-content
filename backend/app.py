import io
import logging
import threading
import uuid
import zipfile
from pathlib import Path

from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS

from backend import database, scheduler, data_fetcher, content_generator
from backend.config import today_israel
from backend.image_api import NanoBananaClient
from backend.scheduler import run_daily_generation, run_market_refresh
from backend.video_studio import generate_scene_prompts

log = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

app = Flask(__name__, static_folder=str(FRONTEND_DIR))
CORS(app)


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)


@app.route("/api/content/<date>", methods=["GET"])
def get_content(date):
    content = database.get_content(date)
    if not content:
        return jsonify({"error": "לא נמצא תוכן לתאריך זה"}), 404
    return jsonify(content)


@app.route("/api/content/today", methods=["GET"])
def get_today():
    today = today_israel()
    content = database.get_content(today)
    if not content:
        return jsonify({"error": "אין תוכן להיום עדיין", "date": today}), 404
    return jsonify(content)


@app.route("/api/content/<date>/section/<section>", methods=["PUT"])
def update_section(date, section):
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "חסר שדה text"}), 400
    try:
        database.update_section(date, section, data["text"])
        return jsonify({"ok": True})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/content/<date>/approve/<section>", methods=["POST"])
def approve_section(date, section):
    try:
        database.approve_section(date, section)
        return jsonify({"ok": True})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/generate", methods=["POST"])
def generate_now():
    today = today_israel()
    existing = database.get_content(today)
    req_data = request.get_json(silent=True) or {}
    force_all = req_data.get("force_all", False)

    if existing and not force_all:
        # Content already exists today → only refresh market summary
        success = run_market_refresh()
        mode = "market_refresh"
    else:
        # First time today (or force) → generate everything
        success = run_daily_generation()
        mode = "full_generation"

    if success:
        content = database.get_content(today)
        return jsonify({"ok": True, "content": content, "mode": mode})
    return jsonify({"error": "שגיאה ביצירת תוכן, בדוק את הלוגים"}), 500


@app.route("/api/generate/section/<section>", methods=["POST"])
def generate_section_now(section):
    """Regenerate a single section without touching anything else."""
    import json as _json

    today = today_israel()
    try:
        market_data = data_fetcher.fetch_market_data()
        news = data_fetcher.fetch_globes_news()

        generators = {
            "market_summary":      lambda: content_generator.generate_market_summary(market_data),
            "investment_tip":      lambda: content_generator.generate_investment_tip(),
            "news_analysis":       lambda: content_generator.generate_news_analysis(news),
            "stock_of_week":       lambda: content_generator.generate_stock_of_week(market_data),
            "investor_psychology": lambda: content_generator.generate_investor_psychology(),
            "weekly_events":       lambda: content_generator.generate_weekly_events(),
            "facebook_post":       lambda: content_generator.generate_facebook_post(market_data, news),
            "instagram_carousel":  lambda: content_generator.generate_instagram_carousel(market_data),
            "instagram_story":     lambda: content_generator.generate_instagram_story(market_data),
        }

        if section not in generators:
            return jsonify({"error": f"Unknown section: {section}"}), 400

        text = generators[section]()
        # Ensure row exists for today before updating
        if not database.get_content(today):
            database.save_draft(date=today)
        database.update_section(today, section, text)
        return jsonify({"ok": True, "text": text})
    except Exception as exc:
        log.exception("Section generation failed: %s", section)
        return jsonify({"error": str(exc)}), 500


@app.route("/api/history", methods=["GET"])
def history():
    return jsonify(database.get_history())


@app.route("/api/debug/market", methods=["GET"])
def debug_market():
    """Returns raw market data — for debugging only."""
    raw = data_fetcher.fetch_market_data()
    formatted = data_fetcher.format_market_for_prompt(raw)
    return jsonify({"raw": raw, "formatted": formatted})


# ---------------------------------------------------------------------------
# Video Studio routes
# ---------------------------------------------------------------------------

# In-memory job store  {job_id: {"status": "...", "scenes": [...], "error": "..."}}
_jobs: dict[str, dict] = {}
_image_client = NanoBananaClient()


@app.route("/api/video/generate-prompts", methods=["POST"])
def video_generate_prompts():
    data = request.get_json()
    if not data or not data.get("script"):
        return jsonify({"error": "חסר שדה script"}), 400

    num_scenes = min(max(int(data.get("num_scenes", 15)), 5), 20)

    try:
        scenes = generate_scene_prompts(data["script"], num_scenes)
        return jsonify({"ok": True, "scenes": scenes})
    except Exception as exc:
        log.exception("generate_scene_prompts failed")
        return jsonify({"error": str(exc)}), 500


@app.route("/api/video/start", methods=["POST"])
def video_start():
    data = request.get_json()
    if not data or not data.get("script"):
        return jsonify({"error": "חסר שדה script"}), 400

    num_scenes = min(max(int(data.get("num_scenes", 15)), 5), 20)
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "generating_prompts", "scenes": [], "error": None}

    def run():
        try:
            scenes = generate_scene_prompts(data["script"], num_scenes)
            _jobs[job_id]["status"] = "generating_images"
            _jobs[job_id]["scenes"] = [
                {**s, "image_b64": None, "done": False} for s in scenes
            ]

            for i, scene in enumerate(_jobs[job_id]["scenes"]):
                img_b64 = _image_client.generate_image_b64(scene["english_prompt"])
                _jobs[job_id]["scenes"][i]["image_b64"] = img_b64
                _jobs[job_id]["scenes"][i]["done"] = True

            _jobs[job_id]["status"] = "done"
        except Exception as exc:
            log.exception("Video job %s failed", job_id)
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["error"] = str(exc)

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"ok": True, "job_id": job_id})


@app.route("/api/video/status/<job_id>", methods=["GET"])
def video_status(job_id):
    job = _jobs.get(job_id)
    if not job:
        return jsonify({"error": "job not found"}), 404

    scenes_out = []
    for s in job["scenes"]:
        scenes_out.append({
            "scene_number": s.get("scene_number"),
            "hebrew_text": s.get("hebrew_text"),
            "english_prompt": s.get("english_prompt"),
            "image_b64": s.get("image_b64"),
            "done": s.get("done", False),
        })

    return jsonify({
        "status": job["status"],
        "error": job["error"],
        "scenes": scenes_out,
        "total": len(scenes_out),
        "completed": sum(1 for s in scenes_out if s["done"]),
    })


@app.route("/api/video/download/<job_id>", methods=["GET"])
def video_download(job_id):
    job = _jobs.get(job_id)
    if not job or job["status"] != "done":
        return jsonify({"error": "job not ready"}), 404

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for scene in job["scenes"]:
            if scene.get("image_b64"):
                import base64
                img_bytes = base64.b64decode(scene["image_b64"])
                filename = f"scene_{scene['scene_number']:02d}.jpg"
                zf.writestr(filename, img_bytes)
    buf.seek(0)

    return send_file(
        buf,
        mimetype="application/zip",
        as_attachment=True,
        download_name="video_frames.zip",
    )


def create_app():
    database.init_db()
    scheduler.start()
    return app
