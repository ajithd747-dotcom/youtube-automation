---
id: backlit-sunset-mood
name: Warm backlit sunset with rim light and long shadows
category: lighting
kind: technique
status: verified
applies_to:
- cinematic
- 3d
when_to_use: Golden hour, sunrise/sunset, dramatic warm light, a hopeful or epic tone.
triggers:
- sunset
- golden hour
- sunrise
- warm light
- dusk
- backlit
- dramatic
- epic
- silhouette
tags:
- mood
source:
- 'own-experience: ada_chain_reaction (Blender 4.5, 2026-09-19)'
version: 1
---
## Procedure
1. Sky texture (MULTIPLE_SCATTERING), `sun_elevation = 7 deg`, `sun_rotation = 28 deg` so the sun is **behind** the subjects (camera looks toward +Y, sun at +Y).
2. Sun light: energy 2.2, colour `#ff9a55`, angle 1.2 deg; aligned to the sky sun direction.
3. Fill: AREA light 500 W, size 6, `#ffd2a8` from the camera side at (-4, -9, 4) so backlit faces keep detail.
4. **Exposure -1.5** (`view_settings.exposure`), AgX "Medium High Contrast" look.
5. Dark floor, low fog (<= 0.15) - a bright floor and haze turn the shot to milk.

## Pitfalls
- With the sun in front of the camera (rotation 150-210 deg) shadows fall behind objects and the image looks flat.
- Exposure 0 with a sunset sky clips the horizon to white; -0.9 was still washed out with fog 0.5; -1.5 with fog <= 0.2 worked.
- Reflected sun in glossy floors needs clamping (see compositor-glare-bloom).
