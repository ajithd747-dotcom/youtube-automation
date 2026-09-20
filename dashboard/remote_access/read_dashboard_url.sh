#!/usr/bin/env bash
# Print the dashboard's current public URL, read from the tunnel's journal (it changes on every restart).
url=$(journalctl --user -u youtube-dashboard-tunnel --no-pager 2>/dev/null | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' | tail -1)
if [ -z "$url" ]; then echo "NO URL: tunnel not running or has not printed one yet" >&2; exit 1; fi
echo "$url"
