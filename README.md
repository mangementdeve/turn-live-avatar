# TURN — Live Avatar Studio

A lightweight, static browser interface for the TURN live-avatar project.

## Current prototype
- Responsive TURN studio interface.
- Local camera preview using browser camera permission.
- Microphone permission check (does not record or transmit audio).
- Avatar portrait image selection and preview.

## Important status
This is the website frontend prototype only. It does **not** yet perform AI face reenactment, real-time lip-sync, remote GPU inference, WebRTC streaming, or virtual-camera output. Those require a separately deployed backend and a streaming integration.

## Run
Open `index.html` from a static web host. Camera access generally requires HTTPS or localhost.

## Deployment
The repository can be connected to a static host later. Vercel is not required to develop the frontend.
