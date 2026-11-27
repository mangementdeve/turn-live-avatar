# NTRU — Live Avatar Studio

A lightweight browser frontend for a consent-based, identity-preserving live portrait animation project.

## Current website milestone

- Responsive NTRU studio interface.
- Local camera preview and stop control.
- Dedicated clean output window that mirrors the current NTRU canvas for ManyCam window capture.
- Microphone permission check (does not record or transmit audio).
- Replaceable portrait selection with JPG, PNG and WebP validation.
- Local portrait preview, image dimensions and file-size display.
- Remove selected portrait and release its browser object URL.
- Explicit status showing that true AI identity animation and remote streaming are not connected yet.

The portrait selection is currently browser-local. Images are not uploaded to an AI service, stored in an account, or committed to this repository. The ManyCam output window mirrors the current local canvas only; it does not turn the existing face-crop overlay into AI animation.


## Remote LivePortrait worker connector

The site now has a consent-gated WebSocket client for the NTRU GPU worker. It can send the selected portrait once, stream webcam frames to the worker, and render returned LivePortrait frames in the existing output canvas. The original microphone is intentionally not uploaded; select the real microphone separately in the calling application.

The worker implementation and Kaggle launcher are in [worker/](worker/README.md). The user must start the worker in their existing Kaggle GPU session and paste its HTTPS tunnel URL and private session token into NTRU. The worker uses a per-session random token and periodic 203-point landmark tracking between face detections.

**Status:** the code path is implemented in the repository but has not yet been run end-to-end from the deployed site against the user's live Kaggle session. Kaggle is temporary compute, not an always-on free production host. Previous tracked processing was 4.42 FPS before integrating the CUDA ONNX landmark provider; real browser-to-worker throughput must be measured before claiming real-time call quality.

## Product requirements

NTRU is intended to animate a user-selected source portrait while preserving the source person's identity and natural appearance. The webcam is the driving-motion source (head pose, expression, blinking and mouth movement); the user's real microphone audio is passed through and synchronized with the returned video. The system must not replace the source identity with a newly generated face or apply beauty/smoothing filters.

Only use a portrait that you own or have explicit permission to animate. Do not use the system to impersonate or mislead people.

## Architecture decision

- **Frontend:** this static website, hosted by Vercel.
- **Source control:** this GitHub repository.
- **Portrait animation candidate:** LivePortrait, initially evaluated with a short driving-video test.
- **Remote inference:** a persistent remote GPU worker; the user's low-spec PC only captures camera/microphone, displays the returned stream, and passes it to ManyCam.
- **Media transport:** WebRTC is the target for synchronized, low-latency audio/video. A queued Gradio demo is suitable for an offline quality test, not a continuous live-call transport.
- **Audio strategy:** first pass through the original microphone audio and use webcam-driven mouth movement. Add a separate audio-driven lip-sync model only if testing proves that webcam-driven mouth movement is insufficient.

LivePortrait is an image/video portrait-animation implementation; it is not, by itself, a ready-made browser webcam-to-WebRTC service. A streaming adapter and persistent GPU worker still need to be engineered and benchmarked.

## Not implemented yet

- Remote AI inference or GPU session management.
- Real-time webcam-driven portrait animation.
- Live microphone transport and synchronized output.
- WebRTC signaling/media server.
- ManyCam integration test.
- Authentication, consent enforcement and secure server-side upload handling.

See [docs/implementation-plan.md](docs/implementation-plan.md) for the staged engineering plan, free-compute assessment and acceptance tests.

## Development and deployment

The frontend is plain HTML/CSS/JavaScript. No local Python or VS Code installation is required on the user's PC. Changes are committed to the `main` branch; Vercel is connected to the repository for deployment.

Camera and microphone APIs require HTTPS or localhost. Do not put Hugging Face tokens, GPU credentials, or other secrets in browser JavaScript or GitHub source files.
