import io
import logging
import threading
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS

from backend import database, scheduler
from backend.image_api import NanoBananaClient
from backend.scheduler import run_daily_generation
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
    today = datetime.now().strftime("%Y-%m-%d")
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
    success = run_daily_generation()
    if success:
        today = datetime.now().strftime("%Y-%m-%d")
        content = database.get_content(today)
        return jsonify({"ok": True, "content": content})
    return jsonify({"error": "שגיאה ביצירת תוכן, בדוק את הלוגים"}), 500


@app.route("/api/history", methods=["GET"])
def history():
    return jsonify(database.get_history())


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
