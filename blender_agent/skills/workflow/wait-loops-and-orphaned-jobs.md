---
id: wait-loops-and-orphaned-jobs
name: Waiting on long jobs - self-matching loops and orphaned children
category: workflow
kind: pitfall
status: verified
applies_to:
- any
when_to_use: Driving long renders or batch jobs in the background and waiting for them
  to finish before starting the next stage.
triggers:
- background job
- wait for
- until loop
- pgrep
- process check
- taskkill
- stop task
- orphaned process
- job never finishes
- race condition
tags:
- workflow
- shell
- process
source:
- 'own-experience: FlipaClip anime-clip recreation (2026-09-20)'
version: 1
---
## Rules

**1. A process check that names the processes will match itself.**

```bash
# WRONG - the powershell/pgrep process's own command line contains these words,
# so the condition is always true and the loop never exits.
until ! powershell -c "Get-CimInstance Win32_Process |
      Where-Object { \$_.CommandLine -match 'render|export|blender' }" | grep -q .; do sleep 20; done
```
Match on the **process name** instead of a command-line substring, or exclude the
checker's own PID:

```bash
until ! powershell -c "Get-Process blender,python -ErrorAction SilentlyContinue" | grep -q .; do sleep 20; done
```
Symptom: the waiting job sits forever while nothing is actually running, and its output
file stays empty. Check for real work with a process listing before assuming it is busy.

**2. Stopping a background task does not stop what it spawned.**
Cancelling a backgrounded shell script kills the tracked task, not its children. One kept
running for ~20 minutes after being "stopped" and raced a foreground run over the same
output files, leaving one shot built from stale inputs. Kill the tree and verify:

```bash
taskkill /PID <root> /T /F        # Windows
pkill -TERM -P <root>; kill <root>  # POSIX
```
Then list processes again, and treat every artefact written during the overlap as
suspect. The stale shot was only caught by checking a content invariant (`ink == []`
counts), not by any error.

**3. Redirected python output is block-buffered.**
`python foo.py > log` shows nothing for minutes, which looks identical to a hang. Use
`python -u` (or `flush=True`) in anything whose progress you intend to watch, and in the
meantime track progress by the mtimes of the files the job writes.
