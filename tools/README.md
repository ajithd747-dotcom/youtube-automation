# tools/ -- the project's own toolchain

Everything the pipeline needs to run lives here, inside the project (gitignored except this file, the conda lock
file and the Blender wrapper). Nothing outside the repo is required except thin symlinks in `~/.local/bin` so the
plain names `blender`, `ffmpeg`, `ffprobe`, `cloudflared`, `micromamba` work on PATH.

| Path | What | How to rebuild |
|---|---|---|
| `blender-4.5.14-linux-x64/` | Blender 4.5 LTS | unpack the tarball from download.blender.org |
| `blender-wrapper.sh` | launcher: X/GL libs + software EGL (llvmpipe) so EEVEE renders headless on CPU | tracked in git |
| `env/` | conda env: X11/GL/Mesa libs, FluidSynth, zstd | `MAMBA_ROOT_PREFIX=$PWD/tools/mamba tools/bin/micromamba create -p tools/env --file tools/environment.lock.txt` |
| `mamba/` | micromamba's package cache for that env | recreated by the command above |
| `bin/` | static `ffmpeg`, `ffprobe` (johnvansickle.com build, has libass but **no drawtext**), `cloudflared`, `micromamba` | download the static builds |
| `hf/` | Hugging Face cache (`HF_HOME`): skytnt/anime-seg ONNX, hysts/anime-face-detector weights | downloaded on first use by the training scripts |
| `torch/` | `TORCH_HOME`: AlexNet weights for the `lpips_holdout` metric | downloaded on first use by training/score_recreation.py |
| `ollama/` | Ollama server + `models/` (llama3.2:1b) | release tarball `ollama-linux-amd64.tar.zst` from github.com/ollama/ollama, unpack with `tools/env/bin/zstd -dc ... | tar -x` |

Python packages live in `.venv` (uv). Beyond the base set, the training measurements need
`uv pip install --python .venv/bin/python anime-face-detector "torch==<installed>"` (adds torchvision; pin torch so it is not replaced), and `lpips` for the perceptual holdout.

Related installs kept beside their users: `agents/tools_bin/` (FluidSynth shim + GeneralUser GS soundfont),
`blender_agent/tools_bin/` (Xvfb, xdotool, software GL for the GUI recorder; `setup_virtual_display.sh` rebuilds it).

Services (systemd --user) are described in `operate/README.md`.
