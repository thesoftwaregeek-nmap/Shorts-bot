"""
Shorts Bot — Mobile PWA
Flask web app, mobile-first, converts videos to shorts
"""

import os
import uuid
import threading
import time
from pathlib import Path
from flask import Flask, request, jsonify, render_template, send_file, session
from werkzeug.utils import secure_filename
from license.validator import validate_license
from processor.converter import process_video, check_ffmpeg

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "shorts_bot_secret_2024")

UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("output")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

ALLOWED = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv", ".m4v"}
MAX_SIZE_MB = 200

jobs = {}  # job_id -> status dict


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/activate", methods=["POST"])
def activate():
    key = request.json.get("key", "").strip()
    valid, msg = validate_license(key, session_id=session.get("sid"))
    if valid:
        session["activated"] = True
        session["license_msg"] = msg
        session["sid"] = session.get("sid") or str(uuid.uuid4())
    return jsonify({"valid": valid, "message": msg})


@app.route("/api/check-license")
def check_license():
    sid = session.get("sid")
    if not sid:
        return jsonify({"valid": False, "message": "No license found."})
    valid, msg = validate_license(session_id=sid)
    return jsonify({"valid": valid, "message": msg})


@app.route("/api/upload", methods=["POST"])
def upload():
    if not session.get("activated"):
        return jsonify({"error": "Not activated"}), 403

    if "video" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["video"]
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED:
        return jsonify({"error": f"Unsupported format: {ext}"}), 400

    # Check size
    file.seek(0, 2)
    size_mb = file.tell() / 1024 / 1024
    file.seek(0)
    if size_mb > MAX_SIZE_MB:
        return jsonify({"error": f"File too large ({size_mb:.0f}MB). Max {MAX_SIZE_MB}MB."}), 400

    job_id = str(uuid.uuid4())[:8]
    filename = secure_filename(f"{job_id}{ext}")
    input_path = UPLOAD_DIR / filename

    file.save(str(input_path))

    jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "message": "Queued...",
        "output": None,
        "caption": None,
        "title": Path(file.filename).stem
    }

    add_captions = request.form.get("add_captions", "true") == "true"
    thread = threading.Thread(
        target=_process_job,
        args=(job_id, str(input_path), add_captions),
        daemon=True
    )
    thread.start()

    return jsonify({"job_id": job_id})


def _process_job(job_id: str, input_path: str, add_captions: bool):
    jobs[job_id]["status"] = "processing"

    def progress_cb(pct, msg):
        jobs[job_id]["progress"] = pct
        jobs[job_id]["message"] = msg

    try:
        result = process_video(
            input_path=input_path,
            output_dir=str(OUTPUT_DIR),
            add_caption=add_captions,
            progress_callback=progress_cb
        )
        jobs[job_id]["status"] = "done"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["message"] = "Complete!"
        jobs[job_id]["output"] = Path(result["output"]).name
        jobs[job_id]["caption"] = result.get("caption_text", "")
        jobs[job_id]["size_mb"] = result.get("size_mb", 0)

        # Cleanup input
        try:
            os.remove(input_path)
        except:
            pass

    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["message"] = str(e)


@app.route("/api/job/<job_id>")
def job_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.route("/api/download/<filename>")
def download(filename):
    if not session.get("activated"):
        return jsonify({"error": "Not activated"}), 403
    path = OUTPUT_DIR / secure_filename(filename)
    if not path.exists():
        return jsonify({"error": "File not found"}), 404
    return send_file(str(path), as_attachment=True)


# Auto-cleanup old files every hour
def cleanup_loop():
    while True:
        time.sleep(3600)
        now = time.time()
        for folder in [UPLOAD_DIR, OUTPUT_DIR]:
            for f in folder.iterdir():
                if now - f.stat().st_mtime > 7200:  # 2 hours
                    try:
                        f.unlink()
                    except:
                        pass


threading.Thread(target=cleanup_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
