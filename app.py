import os
import uuid
import socket
import io
import threading
from datetime import datetime
from flask import (
    Flask, render_template, request, send_file,
    jsonify, redirect, url_for
)
from werkzeug.utils import secure_filename
import qrcode

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = os.environ.get("UPLOAD_FOLDER") or os.path.join(os.path.dirname(__file__), "uploads")
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024
app.config["BASE_URL"] = os.environ.get("BASE_URL")

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

DB_PATH = os.path.join(app.config["UPLOAD_FOLDER"], "files.json")
FILES_DB = {}

if os.path.exists(DB_PATH):
    try:
        import json
        with open(DB_PATH) as f:
            FILES_DB = json.load(f)
    except Exception:
        FILES_DB = {}


def save_db():
    import json
    with open(DB_PATH, "w") as f:
        json.dump(FILES_DB, f, indent=2)


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def format_size(size_bytes):
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def get_file_icon(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    icons = {
        "pdf": "fa-file-pdf", "doc": "fa-file-word", "docx": "fa-file-word",
        "xls": "fa-file-excel", "xlsx": "fa-file-excel",
        "ppt": "fa-file-powerpoint", "pptx": "fa-file-powerpoint",
        "zip": "fa-file-zipper", "rar": "fa-file-zipper", "7z": "fa-file-zipper",
        "mp3": "fa-file-audio", "wav": "fa-file-audio", "flac": "fa-file-audio",
        "mp4": "fa-file-video", "avi": "fa-file-video", "mkv": "fa-file-video",
        "jpg": "fa-file-image", "jpeg": "fa-file-image", "png": "fa-file-image",
        "gif": "fa-file-image", "svg": "fa-file-image", "webp": "fa-file-image",
        "py": "fa-file-code", "js": "fa-file-code", "html": "fa-file-code",
        "css": "fa-file-code", "java": "fa-file-code", "cpp": "fa-file-code",
    }
    return icons.get(ext, "fa-file")


def get_base_url():
    return app.config.get("BASE_URL") or f"http://{get_local_ip()}:5000"


@app.route("/")
def index():
    files = []
    for fid, info in FILES_DB.items():
        files.append({
            "id": fid,
            "name": info["name"],
            "size": format_size(info["size"]),
            "icon": get_file_icon(info["name"]),
            "uploaded": info["uploaded"],
            "downloads": info["downloads"],
        })
    files.sort(key=lambda x: x["uploaded"], reverse=True)
    return render_template("index.html", files=files, base_url=get_base_url(), local_ip=get_local_ip())


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file selected"}), 400
    uploaded = request.files.getlist("file")
    results = []
    for f in uploaded:
        if f.filename == "":
            continue
        filename = secure_filename(f.filename)
        if not filename:
            filename = f"file_{uuid.uuid4().hex[:8]}"
        file_id = uuid.uuid4().hex[:12]
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{file_id}_{filename}")
        f.save(save_path)
        size = os.path.getsize(save_path)
        FILES_DB[file_id] = {
            "name": filename,
            "path": save_path,
            "size": size,
            "uploaded": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "downloads": 0,
        }
        save_db()
        results.append({"id": file_id, "name": filename, "size": format_size(size)})
    return jsonify({"files": results})


@app.route("/download/<file_id>")
def download(file_id):
    if file_id not in FILES_DB:
        return jsonify({"error": "File not found"}), 404
    info = FILES_DB[file_id]
    info["downloads"] += 1
    save_db()
    return send_file(info["path"], as_attachment=True, download_name=info["name"])


@app.route("/preview/<file_id>")
def preview(file_id):
    if file_id not in FILES_DB:
        return jsonify({"error": "File not found"}), 404
    info = FILES_DB[file_id]
    ext = info["name"].rsplit(".", 1)[-1].lower()
    mime_types = {
        "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
        "gif": "image/gif", "svg": "image/svg+xml", "webp": "image/webp",
        "pdf": "application/pdf", "txt": "text/plain",
        "mp3": "audio/mpeg", "wav": "audio/wav",
        "mp4": "video/mp4",
    }
    mime = mime_types.get(ext, "application/octet-stream")
    return send_file(info["path"], mimetype=mime)


@app.route("/delete/<file_id>", methods=["DELETE"])
def delete(file_id):
    if file_id not in FILES_DB:
        return jsonify({"error": "File not found"}), 404
    info = FILES_DB[file_id]
    if os.path.exists(info["path"]):
        os.remove(info["path"])
    del FILES_DB[file_id]
    save_db()
    return jsonify({"success": True})


@app.route("/qr/<file_id>")
def qr(file_id):
    if file_id not in FILES_DB:
        return jsonify({"error": "File not found"}), 404
    base = get_base_url()
    url = f"{base}/download/{file_id}"
    qr_img = qrcode.make(url, box_size=8, border=2)
    buf = io.BytesIO()
    qr_img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


@app.route("/tunnel-status")
def tunnel_status():
    return jsonify({
        "public_url": app.config.get("BASE_URL"),
        "local_ip": get_local_ip(),
        "online": app.config.get("BASE_URL") is not None
    })


@app.route("/stats")
def stats():
    total_size = sum(info["size"] for info in FILES_DB.values())
    total_downloads = sum(info["downloads"] for info in FILES_DB.values())
    return jsonify({
        "files": len(FILES_DB),
        "total_size": format_size(total_size),
        "total_downloads": total_downloads,
    })


def start_ngrok():
    try:
        from pyngrok import ngrok
        tunnel = ngrok.connect(5000, bind_tls=True)
        public_url = tunnel.public_url.replace("https://", "http://")
        app.config["BASE_URL"] = public_url
        log(f"Public URL: {public_url}  (internet)")
    except Exception as e:
        log(f"Internet tunnel not available: {e}")
        if not os.environ.get("FILE_SHARE_BG"):
            print("    Run: ngrok config add-authtoken <your-token>")


LOG_FILE = os.path.join(os.path.dirname(__file__), "fileshare.log")


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{ts}] {msg}\n")
    if not os.environ.get("FILE_SHARE_BG"):
        print(msg)


if __name__ == "__main__":
    on_cloud = os.environ.get("FLY_APP_NAME") is not None
    background = os.environ.get("FILE_SHARE_BG") == "1"
    port = int(os.environ.get("PORT", 5000))

    log("=" * 50)
    log("FileShare - Workspace File Sharing")
    log("=" * 50)

    if on_cloud:
        log(f"Running on Fly.io: {os.environ.get('FLY_APP_NAME')}")
        log(f"Base URL: {app.config.get('BASE_URL', 'not set')}")
    else:
        local_ip = get_local_ip()
        log(f"Local:   http://127.0.0.1:{port}")
        log(f"Network: http://{local_ip}:{port}")
        threading.Thread(target=start_ngrok, daemon=True).start()

    log("=" * 50)
    app.run(host="0.0.0.0", port=port, debug=not background, use_reloader=not background)
