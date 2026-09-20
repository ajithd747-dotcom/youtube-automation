# operate/ -- running the always-on services

Three `systemd --user` services keep the project reachable. Their unit files are kept in the repo and copied to
`~/.config/systemd/user/` (the one place systemd reads from).

| Service | Unit file (in repo) | What it does |
|---|---|---|
| `youtube-dashboard` | `dashboard/remote_access/youtube-dashboard.service` | video review dashboard on `127.0.0.1:8765`, password-protected, upload page |
| `youtube-dashboard-tunnel` | `dashboard/remote_access/youtube-dashboard-tunnel.service` | Cloudflare quick tunnel to the dashboard; the public URL **changes on every restart** |
| `youtube-ollama` | `operate/youtube-ollama.service` | local LLM server on `127.0.0.1:11434`; models live in `tools/ollama/models` |

```bash
cp dashboard/remote_access/*.service operate/*.service ~/.config/systemd/user/ && systemctl --user daemon-reload
systemctl --user enable --now youtube-dashboard youtube-dashboard-tunnel youtube-ollama
systemctl --user status youtube-dashboard youtube-dashboard-tunnel youtube-ollama
dashboard/remote_access/read_dashboard_url.sh        # current public dashboard URL
```

## Dashboard password

`DASHBOARD_PASSWORD` lives in `~/.config/youtube-automation/dashboard.env` (mode 600, deliberately **outside** the repo
because it is a secret). Every request needs it (HTTP Basic, any username). Without it the server is open, which is only
acceptable while nothing but this machine can reach the port.

## Uploading reference videos

Open the dashboard, press **Upload reference videos** (or drag files onto the page). They are sent in 16 MB chunks and
land in `reference vedios/`, then appear in the **Reference** group. Restarting the tunnel changes the URL, not the data.

## After a reboot

`enable` makes all three start on boot only if user lingering is on: `loginctl enable-linger $USER`.

## Toolchain

Binaries and libraries: see `tools/README.md`.
