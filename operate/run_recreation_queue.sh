#!/bin/bash
# Run every unfinished job in operate/recreation_queue.txt, in order. Started at boot by youtube-recreation-queue.service,
# so a reboot resumes the queue: recreate_video.py skips shots whose frames are already rendered.
# A job that fails stops the queue (exit 1) so systemd can retry it; finished jobs leave a marker and are never re-run.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
DONE_DIR=training/runs/queue_done
mkdir -p "$DONE_DIR"
while read -r log_name args; do
  [[ -z "$log_name" || "$log_name" == \#* ]] && continue
  marker="$DONE_DIR/$log_name"
  if [[ -f "$marker" ]]; then echo "skip $log_name (finished $(cat "$marker"))"; continue; fi
  log="training/runs/$log_name.log"
  [[ -s "$log" ]] && mv "$log" "training/runs/${log_name}_$(date +%Y%m%d-%H%M%S).log"
  echo "start $log_name: recreate_video.py $args"
  # shellcheck disable=SC2086
  if .venv/bin/python -u training/recreate_video.py $args > "$log" 2>&1 && grep -q "recreation.mp4" "$log"; then
    date -Is > "$marker"; echo "done $log_name"
  else
    echo "FAILED $log_name -- see $log"; exit 1
  fi
done < operate/recreation_queue.txt
echo "queue empty"
