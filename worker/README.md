# NTRU Kaggle GPU worker

This worker connects the existing NTRU website to the LivePortrait models already installed in the Kaggle session. It caches the uploaded source identity once, tracks the webcam face between periodic detections, and returns processed frames over a secure WebSocket tunnel.

## Start it in the existing Kaggle notebook

Do not restart the notebook kernel if it contains unsaved work. Run these cells in order.

**Cell 1 — clone the NTRU worker files**

```python
!git clone https://github.com/mangementdeve/turn-live-avatar.git /kaggle/working/turn-live-avatar
```

If that folder already exists, update it instead:

```python
!git -C /kaggle/working/turn-live-avatar pull
```

**Cell 2 — install the small web-server dependencies**

```python
!pip -q install "fastapi>=0.115" "uvicorn[standard]>=0.30"
```

The worker expects the LivePortrait repository at `/kaggle/working/LivePortrait`, with its existing pretrained weights, and the installed `onnxruntime-gpu` package. It deliberately launches in a fresh Python process so the notebook's already-imported CPU-only ONNX Runtime 1.23 module does not get reused.

**Cell 3 — launch the worker and secure tunnel**

```python
%run /kaggle/working/turn-live-avatar/worker/kaggle_start.py
```

Wait for the output line `Worker URL: https://....trycloudflare.com`.

## Connect NTRU

1. Open https://turn-live-avatar.vercel.app.
2. Choose your authorized source portrait.
3. Under **03 / Animation pipeline**, paste the printed Worker URL into **Kaggle GPU worker address**.
4. Tick the permission checkbox.
5. Click **Start live face replacement**.
6. Wait for **GPU worker ready · cuda:0** and then move your head and speak.

The worker sends the processed video frames back to the NTRU canvas. Open the ManyCam output window from NTRU to capture that canvas. Select your real microphone directly in the video-call application; this first worker does not transmit audio.

## Important operating limits

- The Kaggle notebook and tunnel must remain running. Closing, idling out, or stopping the Kaggle session disconnects NTRU.
- The free Cloudflare quick tunnel URL changes when restarted. Paste the new URL into NTRU after each restart.
- This is an initial live streaming bridge, not a guaranteed always-on production host. Actual frame rate depends on Kaggle GPU load and network latency; the previous tracked-video benchmark was 4.42 FPS before CUDA ONNX landmark tracking was integrated. Do not assume 25 FPS until measured end-to-end.
- Media is sent to the worker URL you provide. Use a portrait you own or have permission to animate. Frames are processed in memory; the worker does not intentionally save them.
- The original microphone is not uploaded. Select the actual microphone as the call app's audio input.
- Logs: `/kaggle/working/turn-logs/worker.log` and `tunnel.log`.
