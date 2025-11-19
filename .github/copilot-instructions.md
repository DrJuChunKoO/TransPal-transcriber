# Copilot / AI Agent Instructions for TransPal-transcriber

Summary
- TransPal-transcriber is a Slack bot that schedules audio transcription + speaker diarization using a hosted WhisperX pipeline running in Modal.
- Two major components:
  - `main.py` — Slack Bolt app / webhook that receives events and forwards audio URL + bot token to Modal. Posts messages and uploads results back to Slack.
  - `run_whisperx.py` — Modal app that contains GPU-enabled `transcribe` function running whisperX + diarization.

Key integration points
- Modal function name: app `whisperx-transpal`, function `transcribe` — called by `modal.Function.from_name("whisperx-transpal", "transcribe")` in `main.py`.
- Secrets & cache:
  - Modal secret: `my-huggingface-secret` must have `HUGGINGFACE_ACCESS_TOKEN`.
  - Modal volume: `whisper-cache` is used at `/cache` for model download cache.
- Environment variables (important): `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, `SLACK_BOT_CHANNEL`, `SLACK_SIGNING_SECRET`, `MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET`.
  - `main.py` loads from `.env` locally and uses `K_SERVICE` to detect Cloud Run.

Result / message shape & contract
- `run_whisperx.py` returns a dict with:
  - `segments`: list of segments with fields `start`, `end`, `text`, and (after diarization) `speaker`.
  - `info`: object containing `download_time`, `transcode_time`, `transcribe_time`, `diarize_time`.
- `main.py` expects segments to include `speaker`; it filters out segments without a `speaker` key and constructs `result` JSON for upload.
- If you change any property shape in `run_whisperx.py`, update `main.py` accordingly to avoid KeyErrors and mismatches.

Developer workflows (how I would iterate)
- Local dev (Slack bot):
  - Create `.env` with the Slack tokens and channel and add bot to channel.
  - Install dependencies in `requirements.txt`.
  - Run: `python main.py` (starts Bolt app at port 3000).
  - Use ngrok / Cloud Run or Slack event subscription to route events to the local dev app.
- Modal dev (WhisperX GPU function):
  - Prepare Modal secrets (name: `my-huggingface-secret`) with `HUGGINGFACE_ACCESS_TOKEN`.
  - Deploy to modal: `modal deploy run_whisperx.py` (as documented in README).
  - The modal app uses GPU and the image uses pinned PyTorch and whisperX fork; keep those pinned versions unless you bump them intentionally.
- Deploy Slack bot via Docker image (CI builds):
  - GitHub Actions builds and pushes Docker image to ghcr.io — see `.github/workflows/build.yaml`.
  - Run Docker with env vars as in README: `docker run -e SLACK_BOT_TOKEN='<token>' -e SLACK_APP_TOKEN='<token>' ... ghcr.io/drjuchunkoo/transpal-transcriber:latest`

Project-specific conventions and patterns
- Language / comment mixture: Code is mostly English with some Chinese comments/messages — be mindful of strings when updating user-facing text.
- Environment detection: `K_SERVICE` check indicates whether running locally or Cloud Run; do not rely on `.env` in production.
- Slack channel filtering: `main.py` processes only channel messages for `SLACK_BOT_CHANNEL`.
- Remote invocation style: use `modal.Function.from_name` and `.remote(...)` instead of direct imports — this helps keep GPU workload remote.

Common changes you may need to make and patterns to follow
- If you add new fields to the `transcribe` return payload, update `main.py` to present them in the Slack message blocks or file uploads.
- If you change the GPU model or memory profile, update `run_whisperx.py`'s `image` and `GPU_CONFIG` accordingly.
- When adding new dependencies, update `requirements.txt` and consider adding them to the GPU container image/pip requirements in `run_whisperx.py`.
- For small-scale testing of `transcribe` function locally, you can extract the logic in `run_whisperx.py` into a local script that runs without the `@app.function` decorator and pass a local wav file to validate diarization and segments.

Debugging tips
- Log statements in `run_whisperx.py` (prints) are used for function-level timings; check Modal logs for function runs.
- Slack posts and file uploads are visible to users and provide partial troubleshooting information.
- The `slack_bolt` app starts with `app.start(port=int(os.environ.get("PORT", 3000)))` — change port for debugging as needed.

Notes & constraints
- `run_whisperx.py` pins `torch==2.0.0` and other libs; GPU image uses CUDA 12.4.0 in the tag. These are deliberate for compatibility — be conservative when updating.
- `transcribe` uses compute_type `float16` by default and `batch_size=16`. If you run into OOM issues on certain GPUs, lower `batch_size` or change compute_type to `int8` with caution.

Where to look for more context
- `README.md` — setup + deployment steps.
- `main.py` — Slack bot event handling and upload logic.
- `run_whisperx.py` — Modal GPU function, model loading, diarization and returning the result shape.
- `.github/workflows/build.yaml` — Docker build + CI pipeline.

If you want me to add example tests, a small harness for local debugging of `transcribe`, or extend the returned payload with additional metadata, tell me which area you'd like to evolve and I'll prepare a PR with code and README updates.