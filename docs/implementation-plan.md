# TURN implementation plan

## Product decision

- Animation mode: **webcam + real microphone voice**.
- Quality priority: **maximum preservation of the uploaded source identity and natural skin detail**.
- Source portrait is replaceable at any time.
- Use only portraits owned by the user or covered by explicit permission.
- Do not generate a replacement identity, beautify, smooth skin, or alter skin tone.

## Existing repository and hosting

- GitHub: `mangementdeve/turn-live-avatar`, branch `main`.
- Vercel: existing `turn-live-avatar` project.
- The current frontend is static HTML/CSS/JavaScript. Vercel is for the interface and lightweight request/signaling endpoints only, not GPU inference.
- The browser currently checks camera and microphone permissions. The microphone check does not record or transmit audio.
- Portrait selection is local to the browser tab. No image upload endpoint exists yet.

## Proposed media flow

1. Browser captures the driving webcam video and microphone audio after explicit user action.
2. Browser sends the selected portrait and media stream over an authenticated, encrypted connection to a remote GPU worker.
3. Worker uses the webcam frames as driving motion and the uploaded portrait as the identity source.
4. Worker returns the animated video stream.
5. Original microphone audio is forwarded as an audio track and synchronized with the returned video.
6. TURN renders the returned audio/video in the browser.
7. ManyCam captures the TURN output; the call application selects ManyCam as its camera.

The preferred transport is WebRTC (media tracks plus a signaling channel). A WebSocket/JPEG-frame prototype may be used for an early latency experiment, but it is not the intended final transport.

## Model choice and technical caveat

### First candidate: LivePortrait

LivePortrait is the first model to evaluate because its source-image + driving-video workflow matches the desired identity-transfer design. Its published implementation is built around image/video inference and Gradio examples. It does not provide a complete, production-ready webcam-to-WebRTC streaming service.

Therefore the first AI milestone is a short source-image + webcam-driving-video test. Only after the result passes the identity/texture review should engineering proceed to a persistent per-frame or short-window streaming adapter.

The official model card identifies an MIT license for the model repository. Review licenses for every downloaded dependency and pretrained weight separately before deployment or redistribution.

### Audio synchronization strategy

First use webcam-driven mouth motion and pass through the user's original microphone audio. This preserves natural timing between the driving face and speech without introducing a second face-generation stage.

Evaluate an audio-driven lip-sync model only if the webcam-driven mouth motion does not meet the synchronization target. Additional models can change lip shape, texture and timing, so they should not be added pre-emptively.

## Remote compute decision

- The user's PC (Celeron N4120, 4 GB RAM, Intel UHD 600) must not run the neural animation model.
- Use a remote GPU for inference.
- A Hugging Face ZeroGPU Space may be used for an initial queued demonstration if account eligibility and Space availability permit.
- Queued shared GPU execution is not assumed to support continuous live video. Do not promise a five-minute live call based solely on a daily GPU quota.
- For dependable live use, plan for a persistent GPU service with a stable WebRTC endpoint. Cost and free-tier availability must be measured before choosing a host.
- Keep all access tokens in server-side secrets. Never expose tokens in the browser or repository.

## Privacy and safety requirements

- The user must confirm they own the source portrait or have permission to animate it before remote processing.
- Do not commit portraits, camera frames, audio, generated video, access tokens, or session secrets to GitHub.
- Use short-lived in-memory media buffers where possible; avoid permanent storage by default.
- Provide a clear stop/disconnect control that stops browser tracks and closes the remote session.
- Do not log raw media. Log technical metrics only (connection state, frame timing, errors, resource usage).
- Clearly label the output as an AI-animated avatar in the interface; do not build deceptive impersonation features.

## Staged workflow and acceptance tests

### Milestone 1 — Frontend identity handling (current)

- [x] Select any supported portrait.
- [x] Replace portrait at any time.
- [x] Remove portrait.
- [x] Validate supported image formats and file size.
- [x] Display image dimensions and preview locally.
- [x] Explicitly disclose that the portrait is not uploaded yet.
- [ ] Add an explicit permission/consent confirmation before remote processing.
- [ ] Test the deployed interface in Chrome after Vercel reports READY.

Acceptance: selecting, replacing and removing images works; no image is sent to a server; camera and microphone permission checks remain functional.

### Milestone 2 — Offline model quality test

- [ ] Provision a remote GPU environment.
- [ ] Pin a known LivePortrait revision and its model weights.
- [ ] Run a short test using a user-authorized portrait and a webcam driving clip.
- [ ] Compare the output with the source for facial identity, skin texture, skin tone, eye/lip geometry, expression range and artifacts.
- [ ] Reject the model/configuration if it materially changes identity or applies smoothing/beautification.
- [ ] Measure per-frame inference time and memory use.

Acceptance: the source identity remains recognizably the same, natural texture is retained as far as the model permits, and quality is approved before live streaming work begins.

### Milestone 3 — Webcam-driven remote prototype

- [ ] Capture webcam frames in the browser.
- [ ] Send frames to a remote worker using a test transport.
- [ ] Return processed frames to the browser.
- [ ] Measure end-to-end latency, FPS, dropped frames and GPU usage.
- [ ] Confirm that the browser PC performs no neural inference.

Acceptance: continuous movement is demonstrated for a short test session without pretending that the system is production-ready.

### Milestone 4 — Live audio/video and WebRTC

- [ ] Capture webcam and microphone with one explicit user action.
- [ ] Transport original microphone audio.
- [ ] Synchronize returned avatar video with the original audio track.
- [ ] Add reconnect, mute, stop and session cleanup.
- [ ] Test echo, drift, jitter and network interruption.

Acceptance: video and voice remain synchronized during a sustained test.

### Milestone 5 — ManyCam integration

- [ ] Render the returned stream in a dedicated TURN output view.
- [ ] Test whether ManyCam 4.11.2 can capture that view reliably.
- [ ] Verify no recursive camera feedback.
- [ ] Verify the call application receives the intended video and audio devices.

Acceptance: an external call app receives the processed avatar video while the user's real audio remains synchronized.

### Milestone 6 — Hardening

- [ ] Test multiple authorized source portraits.
- [ ] Test lighting, glasses, facial hair, head turns and varied expressions.
- [ ] Optimize GPU allocation and streaming latency.
- [ ] Add usage controls and clear failure messages.
- [ ] Review privacy, dependency licenses and hosting cost.

## Current status

The frontend identity-selection milestone has been implemented in `index.html`. The AI worker, live stream and ManyCam pipeline are not yet implemented. Do not mark them complete until the corresponding acceptance tests pass.
