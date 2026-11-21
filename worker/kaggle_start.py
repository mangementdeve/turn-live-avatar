import os
import re
import sys
import time
import stat
import urllib.request
import subprocess
from pathlib import Path

ROOT = Path("/kaggle/working/LivePortrait")
WORKER = Path("/kaggle/working/turn-live-avatar/worker/live_worker.py")
PORT = 7860
LOG_DIR = Path("/kaggle/working/turn-logs")
LOG_DIR.mkdir(exist_ok=True)

if not ROOT.exists() or not (ROOT / "inference.py").exists():
    raise SystemExit("LivePortrait repository not found at /kaggle/working/LivePortrait.")
if not WORKER.exists():
    raise SystemExit("TURN worker file missing. Clone mangementdeve/turn-live-avatar first.")

# Kaggle's already-running notebook kernel may have an older CPU-only ONNX
# module loaded. This starts a fresh Python process, which imports the installed
# onnxruntime-gpu package and initializes CUDA cleanly.
cloudflared = Path("/kaggle/working/cloudflared")
if not cloudflared.exists():
    url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
    print("Downloading Cloudflare Tunnel client…")
    urllib.request.urlretrieve(url, cloudflared)
    cloudflared.chmod(cloudflared.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

worker_log = open(LOG_DIR / "worker.log", "w")
worker = subprocess.Popen(
    [sys.executable, str(WORKER)],
    cwd=str(ROOT),
    stdout=worker_log,
    stderr=subprocess.STDOUT,
    start_new_session=True,
)
print("Starting TURN LivePortrait worker (model loading can take 1–2 minutes)…")

import urllib.request
for _ in range(180):
    if worker.poll() is not None:
        print((LOG_DIR / "worker.log").read_text(errors="ignore")[-6000:])
        raise SystemExit("TURN worker exited before becoming ready.")
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2) as response:
            print("Worker health:", response.read().decode())
            break
    except Exception:
        time.sleep(1)
else:
    raise SystemExit("Worker did not become ready within 3 minutes. Check /kaggle/working/turn-logs/worker.log.")

tunnel_log = open(LOG_DIR / "tunnel.log", "w")
tunnel = subprocess.Popen(
    [str(cloudflared), "tunnel", "--url", f"http://127.0.0.1:{PORT}", "--no-autoupdate"],
    stdout=tunnel_log,
    stderr=subprocess.STDOUT,
    start_new_session=True,
)
print("Opening secure public tunnel…")
public_url = None
for _ in range(60):
    if tunnel.poll() is not None:
        print((LOG_DIR / "tunnel.log").read_text(errors="ignore")[-4000:])
        raise SystemExit("Cloudflare Tunnel exited.")
    try:
        content = (LOG_DIR / "tunnel.log").read_text(errors="ignore")
        match = re.search(r"https://[a-z0-9-]+\\.trycloudflare\\.com", content)
        if match:
            public_url = match.group(0)
            break
    except Exception:
        pass
    time.sleep(1)

if not public_url:
    print((LOG_DIR / "tunnel.log").read_text(errors="ignore")[-4000:])
    raise SystemExit("Tunnel URL not found. Check /kaggle/working/turn-logs/tunnel.log.")

print("\\nTURN GPU WORKER IS AVAILABLE")
print("Worker URL:", public_url)
print("Paste this URL into TURN Studio → Animation pipeline → Kaggle GPU worker address.")
print("Keep this Kaggle session running while using TURN. Stopping the session stops the worker.")
print("Worker PID:", worker.pid, "| Tunnel PID:", tunnel.pid)
