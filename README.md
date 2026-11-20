# CrackVision Image Analyzer

Standalone crack image analysis site. This folder is separate from `D:\DP_website`; it contains no Raspberry Pi, camera, or live-stream code.

## Included model and settings

`models/best.pt` is copied from `D:\DP\runs\crack_yolo11n_seg\weights\best.pt`. Inference uses Ultralytics YOLO segmentation with image size 416, confidence 0.15, NMS IoU 0.50, CPU, and rendered segmentation masks plus bounding boxes.

## Run locally on Windows

From PowerShell:

```powershell
cd D:\DP_image_analyzer
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

Open <http://127.0.0.1:5001>. The first model load can take a little while. If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process Bypass` in that terminal and activate again. Alternatively, run the installed Python executable directly: `python app.py`.

## Deploy to Vercel

Commit this folder as its own Git repository, import that repository as a Vercel project, and deploy with the root directory set to the repository root. The root `app.py`, `requirements.txt`, and `vercel.json` are included for Flask detection. Vercel's Flask runtime runs the app as a Python Function; check its current function limits and deployment build log before sharing the deployed URL. Large PyTorch/Ultralytics dependencies and CPU inference time can affect build size and cold-start latency. The app limits uploads to 4 MB and sends a compressed output preview to avoid storing files between function calls.

## Endpoints

- `GET /` — analyzer interface
- `GET /api/health` — app/model configuration status
- `POST /api/analyze` — multipart image field named `image`

The returned annotated JPEG is included in the JSON response. No uploaded image or result is saved on the server.
