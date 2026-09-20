# youtube automation

Pipeline stages, in order:

1. **research/** — agent uses Playwright MCP (browser) + WebSearch to gather topic data. Save notes as `research/<topic>.md`.
2. **scripts/** — `python scripts/generate_script.py research/<topic>.md` turns notes into a video script via the local Ollama model.
3. **video/** — turns a script into a video file (`video/assemble.py`: stock/stickman). **blender_agent/** — paste a script, get an animated Blender video (stickman / kinetic text / 3D). See `blender_agent/README.md`.
3b. **dashboard/** — `python dashboard/server.py` opens a local review page to play every created/test video, run pre-upload checks, approve/reject, and copy the upload command.
4. **upload/** — `python upload/youtube_upload.py <video> "<title>" "<description>"` publishes to YouTube via the official Data API (OAuth2). Setup: see `config/README.md`.

Current automation mode: **fully autonomous** (no human-review checkpoint). Note: YouTube actively enforces policies against mass-produced/repetitious/inauthentic content and requires disclosure of realistic AI-generated content — worth keeping in mind for monetization risk even though the pipeline itself runs unattended.

## Local LLM (Ollama)

Ollama is installed locally and serves models at `http://localhost:11434`.

- Model in use: `llama3.2:1b` (chosen for this machine's specs: 2-core CPU, ~6GB RAM, no discrete GPU)
- Start the server if it's not already running: `ollama serve`
- Test from the CLI: `ollama run llama3.2:1b`
- Test from Python: `python ollama_client.py`

To use a different/larger model later: `ollama pull <model>` (see https://ollama.com/library).
