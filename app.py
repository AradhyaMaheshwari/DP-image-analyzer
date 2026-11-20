"""Image-only crack analyzer using the DP YOLO segmentation checkpoint."""
import base64
import io
import os
import threading
import time
from pathlib import Path

import numpy as np
from flask import Flask, jsonify, render_template, request
from PIL import Image, UnidentifiedImageError
from dotenv import load_dotenv
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
MODEL_PATH = Path(os.getenv("MODEL_PATH", str(ROOT / "models" / "best.pt")))
if not MODEL_PATH.is_absolute():
    MODEL_PATH = ROOT / MODEL_PATH
IMAGE_SIZE = int(os.getenv("MODEL_INPUT_SIZE", "416"))
CONFIDENCE = float(os.getenv("DETECTION_CONFIDENCE", "0.15"))
IOU = float(os.getenv("DETECTION_IOU", "0.5"))
MAX_UPLOAD_BYTES = 4 * 1024 * 1024
MAX_OUTPUT_EDGE = 1280
_model = None
_model_lock = threading.Lock()
_infer_lock = threading.Lock()

app = Flask(__name__, template_folder="templates", static_folder="public", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES


def get_model():
    global _model
    with _model_lock:
        if _model is None:
            if not MODEL_PATH.is_file():
                raise FileNotFoundError(f"Model checkpoint not found: {MODEL_PATH}")
            _model = YOLO(str(MODEL_PATH), task="segment")
    return _model


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/api/health")
def health():
    return jsonify(status="ok", model="available" if MODEL_PATH.is_file() else "missing",
                   image_size=IMAGE_SIZE, confidence=CONFIDENCE, iou=IOU)


@app.post("/api/analyze")
def analyze():
    upload = request.files.get("image")
    if upload is None or not upload.filename:
        return jsonify(error="Choose an image to analyze."), 400
    try:
        raw = upload.read(MAX_UPLOAD_BYTES + 1)
        if len(raw) > MAX_UPLOAD_BYTES:
            return jsonify(error="Image is larger than the 4 MB upload limit."), 413
        image = Image.open(io.BytesIO(raw))
        if image.format not in {"JPEG", "PNG"}:
            return jsonify(error="Use a JPG, JPEG, or PNG image."), 415
        image = image.convert("RGB")
        width, height = image.size
    except (UnidentifiedImageError, OSError, ValueError):
        return jsonify(error="This image could not be opened. Choose a valid JPG or PNG."), 400

    try:
        started = time.perf_counter()
        with _infer_lock:
            result = get_model().predict(source=image, imgsz=IMAGE_SIZE, conf=CONFIDENCE,
                                         iou=IOU, device="cpu", verbose=False)[0]
        boxes = result.boxes
        count = len(boxes) if boxes is not None else 0
        confidences = boxes.conf.detach().cpu().tolist() if count else []
        # Ultralytics returns a BGR array; reverse channels for a browser-ready RGB image.
        rendered = Image.fromarray(np.asarray(result.plot(boxes=True))[:, :, ::-1].copy())
        rendered.thumbnail((MAX_OUTPUT_EDGE, MAX_OUTPUT_EDGE), Image.Resampling.LANCZOS)
        output = io.BytesIO()
        rendered.save(output, format="JPEG", quality=72, optimize=True)
        encoded = base64.b64encode(output.getvalue()).decode("ascii")
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        return jsonify(detected=bool(count), count=count,
                       confidence=max(confidences) if confidences else None,
                       processing_ms=elapsed_ms, width=width, height=height,
                       model=MODEL_PATH.name, image_size=IMAGE_SIZE, iou=IOU,
                       visualization="segmentation masks and bounding boxes",
                       output_image=f"data:image/jpeg;base64,{encoded}")
    except Exception as exc:
        app.logger.exception("Image inference failed")
        return jsonify(error=f"Analysis failed: {exc}" if isinstance(exc, FileNotFoundError)
                       else "Analysis failed. Check that the model and dependencies are available."), 503


@app.errorhandler(413)
def upload_too_large(_error):
    return jsonify(error="Image is larger than the 4 MB upload limit."), 413


if __name__ == "__main__":
    app.run(host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "5001")), debug=False)
