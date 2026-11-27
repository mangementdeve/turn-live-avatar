"""
NTRU LivePortrait WebSocket worker.
Run inside the existing Kaggle LivePortrait environment.
The browser sends one portrait at session start, then JPEG webcam frames.
The worker returns JPEG avatar frames. Original microphone audio stays local
and should be selected separately in the calling application.
"""
import os, io, json, base64, time, asyncio
from typing import Optional

import cv2
import numpy as np
import torch
import onnxruntime as ort
ort.preload_dlls(cuda=False, cudnn=False)
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

ROOT = os.environ.get("LIVEPORTRAIT_ROOT", "/kaggle/working/LivePortrait")
os.chdir(ROOT)
from src.config.inference_config import InferenceConfig
from src.config.crop_config import CropConfig
from src.live_portrait_pipeline import LivePortraitPipeline
from src.utils.cropper import crop_image

app = FastAPI(title="NTRU LivePortrait Worker")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
pipeline = None
wrapper = cropper = None
inf_cfg = crop_cfg = None
device = None
module = None
gpu_lock = asyncio.Lock()

def load_engine():
    global pipeline, wrapper, cropper, inf_cfg, crop_cfg, device, module
    if pipeline is not None:
        return
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU is required for NTRU inference.")
    if "CUDAExecutionProvider" not in ort.get_available_providers():
        raise RuntimeError("ONNX Runtime CUDA provider is unavailable. Install onnxruntime-gpu in the Kaggle environment.")
    inf_cfg = InferenceConfig(device_id=0, flag_use_half_precision=True,
        flag_stitching=True, flag_relative_motion=True, flag_pasteback=True,
        flag_do_crop=True, flag_do_rot=True, driving_option="pose-friendly",
        driving_multiplier=1.0, flag_normalize_lip=False, flag_do_torch_compile=False)
    crop_cfg = CropConfig(device_id=0, det_thresh=0.15)
    pipeline = LivePortraitPipeline(inference_cfg=inf_cfg, crop_cfg=crop_cfg)
    wrapper, cropper, device = pipeline.live_portrait_wrapper, pipeline.cropper, pipeline.live_portrait_wrapper.device
    import src.live_portrait_pipeline as pm
    module = pm

def decode_image(data: bytes):
    arr = np.frombuffer(data, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError("Invalid image frame.")
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

def prepare_identity(portrait_bytes: bytes):
    rgb = decode_image(portrait_bytes)
    rgb = module.resize_to_limit(rgb, inf_cfg.source_max_dim, inf_cfg.source_division)
    crop = cropper.crop_source_image(rgb, crop_cfg)
    if crop is None:
        raise ValueError("No face detected in the uploaded portrait.")
    I_s = wrapper.prepare_source(crop["img_crop_256x256"])
    info = wrapper.get_kp_info(I_s)
    with torch.inference_mode():
        feature = wrapper.extract_feature_3d(I_s)
        keypoints = wrapper.transform_keypoint(info)
    rotation = module.get_rotation_matrix(info["pitch"], info["yaw"], info["roll"])
    return {"feature": feature, "info": info, "kp": keypoints,
            "kp_c": info["kp"], "rotation": rotation, "reference": None}

def clone_info(info):
    return {k: v.clone() if torch.is_tensor(v) else v for k, v in info.items()}

def render_frame(frame_rgb, identity, state, index):
    h, w = frame_rgb.shape[:2]
    # Re-detect periodically; track landmarks between detections.
    detect = state["landmarks"] is None or index % 30 == 0
    runner = cropper.human_landmark_runner
    if detect:
        faces = cropper.face_analysis_wrapper.get(
            cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR),
            flag_do_landmark_2d_106=True,
            direction=crop_cfg.direction,
            max_face_num=crop_cfg.max_face_num,
        )
        if not faces:
            return None
        landmarks = runner.run(frame_rgb, faces[0].landmark_2d_106)
    else:
        landmarks = runner.run(frame_rgb, state["landmarks"])
    state["landmarks"] = landmarks
    crop = crop_image(
        frame_rgb, landmarks, dsize=crop_cfg.dsize, scale=crop_cfg.scale,
        vx_ratio=crop_cfg.vx_ratio, vy_ratio=crop_cfg.vy_ratio,
        flag_do_rot=crop_cfg.flag_do_rot,
    )
    crop["img_crop_256x256"] = cv2.resize(
        crop["img_crop"], (256, 256), interpolation=cv2.INTER_AREA
    )
    driving = wrapper.prepare_source(crop["img_crop_256x256"])
    d_info = wrapper.get_kp_info(driving)
    R_d = module.get_rotation_matrix(d_info["pitch"], d_info["yaw"], d_info["roll"])
    if state["reference"] is None:
        state["R0"] = R_d.clone()
        state["d0"] = clone_info(d_info)
        state["reference"] = True
    d0, s = state["d0"], identity["info"]
    with torch.inference_mode():
        delta = s["exp"].clone() + (d_info["exp"] - d0["exp"])
        R_new = (R_d @ state["R0"].permute(0, 2, 1)) @ identity["rotation"]
        scale = s["scale"] * (d_info["scale"] / d0["scale"])
        t = s["t"] + (d_info["t"] - d0["t"])
        t[..., 2].fill_(0)
        kp_new = scale * (identity["kp_c"] @ R_new + delta) + t
        if inf_cfg.flag_stitching:
            kp_new = wrapper.stitching(identity["kp"], kp_new)
        kp_new = identity["kp"] + (kp_new - identity["kp"]) * inf_cfg.driving_multiplier
        generated = wrapper.warp_decode(identity["feature"], identity["kp"], kp_new)
        face = wrapper.parse_output(generated["out"])[0]
    mask = module.prepare_paste_back(inf_cfg.mask_crop, crop["M_c2o"], dsize=(w, h))
    result = module.paste_back(face, crop["M_c2o"], frame_rgb, mask)
    return cv2.cvtColor(result, cv2.COLOR_RGB2BGR)

@app.get("/health")
def health():
    return {"ok": True, "engine_loaded": pipeline is not None,
            "cuda": bool(torch.cuda.is_available()), "device": str(device) if device else None}

@app.websocket("/ws")
async def stream(ws: WebSocket):
    expected = os.environ.get("TURN_WORKER_TOKEN", "")
    supplied = ws.query_params.get("token", "")
    if not expected or supplied != expected:
        await ws.close(code=1008, reason="Invalid worker token")
        return
    await ws.accept()
    try:
        hello = await ws.receive_text()
        cfg = json.loads(hello)
        if cfg.get("type") != "init" or not cfg.get("portrait"):
            await ws.send_json({"type":"error","message":"Send an init message with a portrait first."})
            await ws.close()
            return
        load_engine()
        portrait = base64.b64decode(cfg["portrait"].split(",", 1)[-1])
        async with gpu_lock:
            identity = prepare_identity(portrait)
        state = {"landmarks": None, "reference": None, "R0": None, "d0": None}
        await ws.send_json({"type":"ready","message":"NTRU GPU worker ready","device":str(device)})
        count = 0
        while True:
            payload = await ws.receive_bytes()
            started = time.perf_counter()
            frame = decode_image(payload)
            async with gpu_lock:
                output = render_frame(frame, identity, state, count)
            count += 1
            if output is None:
                await ws.send_json({"type":"dropped","frame":count})
                continue
            ok, encoded = cv2.imencode(".jpg", output, [cv2.IMWRITE_JPEG_QUALITY, 88])
            if ok:
                await ws.send_bytes(encoded.tobytes())
                if count % 30 == 0:
                    await ws.send_json({"type":"stats","frames":count,
                        "worker_ms":round((time.perf_counter()-started)*1000,1)})
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await ws.send_json({"type":"error","message":str(exc)})
        except Exception:
            pass
    finally:
        pass

if __name__ == "__main__":
    load_engine()
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "7860")))
