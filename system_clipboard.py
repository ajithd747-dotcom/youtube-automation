"""Copy text to / read text from the desktop clipboard on Linux (Wayland or X11).

A headless server has no clipboard at all; both functions then say so (False / None) instead of raising, and the
caller decides what to do instead.
"""
import os
import shutil
import subprocess


def _clipboard_commands():
    """(copy command, paste command) for the first clipboard tool that matches the running session, else None."""
    if os.environ.get("WAYLAND_DISPLAY") and shutil.which("wl-copy") and shutil.which("wl-paste"):
        return ["wl-copy"], ["wl-paste", "--no-newline"]
    if os.environ.get("DISPLAY"):
        if shutil.which("xclip"):
            return ["xclip", "-selection", "clipboard"], ["xclip", "-selection", "clipboard", "-o"]
        if shutil.which("xsel"):
            return ["xsel", "--clipboard", "--input"], ["xsel", "--clipboard", "--output"]
    return None


def copy_text_to_clipboard(text: str) -> bool:
    cmds = _clipboard_commands()
    if cmds is None:
        return False
    try:
        subprocess.run(cmds[0], input=text.encode("utf-8"), check=True, timeout=5)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def read_text_from_clipboard():
    """The clipboard text, or None when there is no clipboard to read."""
    cmds = _clipboard_commands()
    if cmds is None:
        return None
    try:
        return subprocess.run(cmds[1], capture_output=True, check=True, timeout=5).stdout.decode("utf-8", "ignore")
    except (OSError, subprocess.SubprocessError):
        return None
