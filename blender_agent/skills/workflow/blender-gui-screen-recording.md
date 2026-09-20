---
id: blender-gui-screen-recording
name: 'Record real Blender UI: scripted tour + ffmpeg x11grab on Xvfb'
category: workflow
kind: technique
status: verified
applies_to:
- any
when_to_use: A tutorial / how-to / 'show the software' video needs authentic Blender GUI footage (properties, node
  editors, effects) instead of mock-ups.
triggers:
- tutorial
- screen recording
- how to
- blender interface
- gui
- walkthrough
- screencast
- demonstrate
- ui footage
source:
- 'own-experience: tutorial recreation benchmark (2026-09-19)'
version: 1
tags:
- gui
- ffmpeg
- tutorial
---
## Procedure (recreate/tutorial_gui.py + record_gui.py)
1. `record_gui.py` starts a 1920x1080 Xvfb virtual display (`tools_bin/Xvfb :99`), then `ffmpeg -f x11grab -framerate 24 -draw_mouse 0 -video_size 1920x1080 -i :99 -vf scale=1280:720 -c:v libx264 -preset ultrafast -crf 18`, then launches `tools_bin/blender-gui --python tutorial_gui.py -- <speed> <log>` with `DISPLAY=:99` (quote paths with spaces!).
2. Dismiss the first-run splash: `xdotool mousemove` away, then `xdotool mousemove 958 747 click 1` where Continue sits on the centred splash; park the pointer in a corner.
3. Inside Blender: `bpy.ops.wm.window_fullscreen_toggle()` (16:9 capture), `preferences.view.ui_scale = 1.25`, viewport `shading.type='RENDERED'` + camera view so effects show live.
4. Timeline engine: a `bpy.app.timers` tick every 0.05 s runs (t, function) steps and tweens (lerp of a property between two times) so sliders visibly move while the narration explains them; every step is try/except + logged.
5. Editors: `area.spaces.active.context = 'OBJECT'|'OUTPUT'|...` picks the Properties tab; `bpy.context.window.workspace = bpy.data.workspaces['Compositing']` switches workspace; `with bpy.context.temp_override(window, area, region): bpy.ops.node.view_all()` keeps new nodes in view.
6. Log `TOUR START` (wall clock) and the recorder start time: trim with `-ss offset`.
7. ALWAYS dry-run with `--speed 20` (27 s) and look at a contact sheet before the real 9-minute run.
## Pitfalls
- The machine is unusable while recording (fullscreen); nobody may click. The capture is 1920x1080 physical even if the display is scaled.
- Properties tab enum lists only tabs valid for the ACTIVE object: the Effects tab needs the Grease Pencil object active (adding a camera afterwards stole the active object).
- Setting `default_value` on a socket that does not exist prints thousands of `RNA_float_set` lines: guard tweens.
