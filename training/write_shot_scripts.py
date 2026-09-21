"""Layer B of the per-frame script: one script per shot, built ONLY from the measured rows of Layer A.

    .venv/bin/python training/write_shot_scripts.py <slug-or-fragment> [--shots 3,7-9]

Writes under training/reference/<slug>/:  shots/shot_XX.json   sheets/shot_XX.jpg   script.json (index)
Rule (CLAUDE.md 2): a value is measured or the text "NOT MEASURED". Inferences (a particle "type", a camera move name)
are labelled `inferred` with their evidence and a confidence; they never replace the underlying measurement.
`semantic` stays NOT MEASURED until a vision pass (the frame-script-writer agent) fills it from the contact sheets.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "reference"
ROOT = HERE.parent
NM = "NOT MEASURED"


def r(x, n=4):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), n)


def series(rows, path):
    """Values along a dotted path; None (NOT MEASURED) becomes NaN so it never counts as zero."""
    out = []
    for row in rows:
        v = row
        for p in path.split("."):
            v = v.get(p) if isinstance(v, dict) else None
        out.append(float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else float("nan"))
    return np.array(out)


def nz(a, fn, default=None):
    a = a[~np.isnan(a)]
    return r(fn(a)) if a.size else default


def circular_mean_deg(angles, weights):
    m = ~np.isnan(angles) & ~np.isnan(weights) & (weights > 0)
    if not m.any():
        return None
    a = np.radians(angles[m])
    return r(math.degrees(math.atan2((np.sin(a) * weights[m]).sum(), (np.cos(a) * weights[m]).sum())) % 360, 1)


# ----------------------------------------------------------------------------- sections
def timing_section(rows, fps):
    newd = np.array([bool(x["motion"]["new_drawing"]) if x["motion"]["new_drawing"] is not None else False for x in rows])
    idx = np.flatnonzero(newd)
    holds = np.diff(np.append(idx, len(rows))) if idx.size else np.array([])
    return {"frames": len(rows), "seconds": r(len(rows) / fps), "distinct_drawings": int(newd.sum()),
            "cadence_on_n": int(np.median(holds)) if holds.size else NM,
            "hold_length_histogram": {int(k): int(v) for k, v in zip(*np.unique(holds, return_counts=True))} if holds.size else NM}


def camera_section(rows, fps):
    dx, dy, zm, roll = (series(rows, f"camera.{k}") for k in ("dx", "dy", "zoom", "roll_deg"))
    ok = ~np.isnan(dx)
    if ok.sum() < 3:
        return {"move": NM, "path_keyframes": NM, "evidence": "fewer than 3 frames with a camera model"}
    cdx, cdy, czm, croll = (np.nancumsum(a) for a in (dx, dy, zm, roll))
    total = {"dx": r(cdx[-1]), "dy": r(cdy[-1]), "zoom": r(czm[-1]), "roll_deg": r(croll[-1], 2)}
    move, why = "static", []
    if abs(czm[-1]) > 0.02:
        move = "push_in" if czm[-1] > 0 else "pull_out"; why.append(f"cumulative zoom {czm[-1]:+.3f}")
    if math.hypot(cdx[-1], cdy[-1]) > 0.02:
        horiz = abs(cdx[-1]) >= abs(cdy[-1])
        # the image moves opposite to the camera: content sliding left means the camera pans right
        move = ("pan_right" if cdx[-1] < 0 else "pan_left") if horiz else ("tilt_down" if cdy[-1] < 0 else "tilt_up")
        why.append(f"cumulative image shift ({cdx[-1]:+.3f}, {cdy[-1]:+.3f}) frame widths")
    if abs(croll[-1]) > 3:
        move += "+roll"; why.append(f"roll {croll[-1]:+.1f} deg")
    k = max(3, min(len(rows) // 6, 9))
    win = np.ones(k) / k
    hx = dx - np.convolve(np.nan_to_num(dx), win, "same")
    hy = dy - np.convolve(np.nan_to_num(dy), win, "same")
    shake = float(np.sqrt(np.nanmean(hx ** 2 + hy ** 2)))
    keys = np.linspace(0, len(rows) - 1, min(9, len(rows))).astype(int)
    speed = np.hypot(np.nan_to_num(dx), np.nan_to_num(dy)) + np.abs(np.nan_to_num(zm))
    easing = NM
    if move != "static" and len(rows) >= 12:
        seg = np.array([s.sum() for s in np.array_split(speed, 4)])
        peak = int(np.argmax(seg))
        easing = {"inferred": "ease_out" if peak == 0 else "ease_in" if peak == 3 else "ease_in_out",
                  "evidence": f"motion share per quarter {[r(x / (seg.sum() + 1e-12), 2) for x in seg]}"}
    return {"move": {"inferred": move, "evidence": "; ".join(why) or "no cumulative motion above thresholds"}, "total": total,
            "easing": easing, "shake_rms_frame_widths": r(shake, 5), "handheld_shake": bool(shake > 0.002),
            "path_keyframes": [{"frame": int(i), "dx": r(cdx[i]), "dy": r(cdy[i]), "zoom": r(czm[i]), "roll_deg": r(croll[i], 2)} for i in keys],
            "units": "cumulative image shift in frame widths (image moves opposite to the camera); zoom = cumulative scale-1"}


def shimmer_stats(rows):
    """Temporal std of each 3x3 cell's luma over the shot: dappled light, flickering neon, moving shadows. Cuts inside the shot
    would inflate it, so frame-to-frame changes larger than 0.15 are excluded."""
    grid = np.array([x["lighting"]["luma_grid3x3"] for x in rows if x["lighting"].get("luma_grid3x3")])
    if len(grid) < 8:
        return NM
    d = np.diff(grid, axis=0)
    d[np.abs(d) > 0.15] = np.nan
    cell = np.nanstd(d, axis=0)
    moving = np.nanmedian(series(rows, "motion.moving_share"))
    return {"per_cell_frame_to_frame_std": [r(v, 4) for v in cell], "max_cell": r(np.nanmax(cell), 4),
            "confounded_by_subject_motion": bool(moving > 0.1), "subject_moving_share": r(moving, 3),
            "inferred": "local_light_variation_present" if np.nanmax(cell) > 0.006 else "steady_light", "cells": "row-major 3x3, top-left first"}


def lighting_section(rows, fps):
    g = lambda k: series(rows, f"lighting.{k}")
    luma, p5, p95 = g("luma_mean"), g("luma_p5"), g("luma_p95")
    delta = g("exposure_delta")
    keys = np.linspace(0, len(rows) - 1, min(9, len(rows))).astype(int)
    d2 = delta[~np.isnan(delta)]
    flicker = float(np.sqrt(np.mean((d2 - np.convolve(d2, np.ones(3) / 3, "same")) ** 2))) if d2.size > 6 else None
    strength = g("key_gradient_strength")
    return {
        "exposure_luma": {"median": nz(luma, np.median), "keyframes": [{"frame": int(i), "luma": r(luma[i])} for i in keys]},
        "contrast_luma_std": nz(g("luma_std"), np.median),
        "key_to_fill_proxy": r(np.nanmedian(p95) / max(np.nanmedian(p5), 0.02)),
        "ambient_luma_p5": nz(p5, np.median), "highlight_luma_p95": nz(p95, np.median),
        "key_direction_screen_deg": {"angle": circular_mean_deg(g("key_gradient_angle_deg"), strength), "strength": nz(strength, np.median),
                                     "meaning": "screen-space direction toward the brighter side; 0 = right, 90 = down"},
        "brightest_region": {"x": nz(g("brightest_x"), np.median), "y": nz(g("brightest_y"), np.median), "area": nz(g("brightest_area"), np.median)},
        "top_minus_bottom": nz(g("top_minus_bottom"), np.median), "left_minus_right": nz(g("left_minus_right"), np.median),
        "warmth_r_over_b": nz(g("warmth_r_over_b"), np.median), "lab_a": nz(g("lab_a"), np.median), "lab_b": nz(g("lab_b"), np.median),
        "bloom": nz(g("bloom"), np.median), "vignette_corner_over_centre": nz(g("vignette_corner_over_centre"), np.median),
        "clipped_highlights": nz(g("clipped_highlights"), np.median), "crushed_shadows": nz(g("crushed_shadows"), np.median),
        "flicker_rms": r(flicker, 5), "flash_frames": [int(i) for i in np.flatnonzero(np.abs(np.nan_to_num(delta)) > 0.1)],
        "local_light_shimmer": shimmer_stats(rows),
        "rim_or_back_light": NM, "cast_shadows": NM,
    }


def motion_section(rows, fps):
    newd = np.array([bool(x["motion"]["new_drawing"]) if x["motion"]["new_drawing"] is not None else False for x in rows])
    spd = series(rows, "motion.mean_speed")
    on = newd & ~np.isnan(spd)                       # measure motion where a new drawing arrived, not on holds
    pick = lambda k: series(rows, f"motion.{k}")[on]
    hist = np.array([x["motion"]["direction_hist8"] for x, m in zip(rows, on) if m and x["motion"]["direction_hist8"]])
    parallax = series(rows, "depth.layer_speed_ratio")
    fast = series(rows, "depth.fast_layer_share")
    real = on & (spd > 0.0005)
    return {"measured_on": "frames where a new drawing arrived (holds carry no motion)", "frames_used": int(on.sum()),
            "mean_speed_frame_widths_per_frame": nz(spd[on], np.mean), "p95_speed": nz(pick("p95_speed"), np.median),
            "moving_share": nz(pick("moving_share"), np.mean),
            "direction_deg": circular_mean_deg(pick("direction_deg"), spd[on]), "coherence": nz(pick("coherence"), np.mean),
            "direction_hist8_share": [r(x, 3) for x in hist.mean(axis=0)] if hist.size else NM,
            "divergence_mean": nz(pick("divergence"), np.mean), "curl_mean": nz(pick("curl"), np.mean),
            "parallax": {"layer_speed_ratio": nz(parallax[real], np.median), "fast_layer_share": nz(fast[real], np.median),
                         "evidence_frames": int(real.sum())} if real.sum() >= 3 else NM}


def physics_section(rows, fps):
    cnt = series(rows, "physics.particle_count")
    has = cnt > 0
    frac = float(np.nanmean(has)) if len(rows) else 0.0
    part = {"frames_with_particles_share": r(frac, 3), "mean_particle_count": nz(cnt[has], np.mean), "gravity_wind": NM, "particle_type": NM}
    if has.sum() >= 5:
        vx, vy = series(rows, "physics.particle_vx")[has], series(rows, "physics.particle_vy")[has]
        fall, ds = series(rows, "physics.fall_speed")[has], series(rows, "physics.downward_share")[has]
        st, rd = series(rows, "physics.streakiness")[has], series(rows, "physics.roundness")[has]
        mvx, mvy = float(np.nanmean(vx)), float(np.nanmean(vy))
        per_s = math.hypot(mvx, mvy) * fps
        part["velocity_frame_widths_per_second"] = {"vx": r(mvx * fps), "vy": r(mvy * fps), "speed": r(per_s)}
        part["turbulence"] = nz(series(rows, "physics.turbulence")[has], np.mean, None)
        part["gravity_wind"] = {"direction_deg": r(math.degrees(math.atan2(mvy, mvx)) % 360, 1), "downward_share": nz(ds, np.mean),
                                "note": "mean velocity of small moving blobs; 90 deg = straight down (gravity), 0/180 = wind"}
        s_med, r_med, d_med = float(np.nanmedian(st)), float(np.nanmedian(rd)), float(np.nanmedian(ds))
        count_med = float(np.nanmedian(cnt[has]))
        spread = float(np.nanmedian(series(rows, "physics.particle_spread")[has]))
        big_motion = float(np.nanmedian(series(rows, "physics.large_motion_share")[has]))
        small_area = float(np.nanmedian(series(rows, "physics.particle_area_share")[has]))
        # Pixel statistics cannot reliably tell particles from other things that move as many small blobs. Checked by eye on real
        # shots: dappled sunset light through leaves and animated logo text both look like a particle field (false positives);
        # rain streaks merge into large connected regions and look like character motion (false negative). So this is only ever a
        # CANDIDATE that the vision pass (semantic.weather_particles_seen) must confirm or reject.
        many_blobs = frac > 0.3 and count_med >= 8 and spread > 0.12
        clean_field = many_blobs and small_area > big_motion
        if clean_field and s_med > 2.5 and d_med > 0.8:
            kind, conf = "candidate_rain_like_streaks", 0.35
        elif clean_field and d_med > 0.6 and r_med > 0.45:
            kind, conf = "candidate_falling_petals_snow_or_dust", 0.3
        elif clean_field:
            kind, conf = "candidate_drifting_particles", 0.2
        elif many_blobs:
            kind, conf = "candidate_particles_merged_with_large_motion(rain_or_character_motion)", 0.1
        else:
            kind, conf = "no_particle_field_detected", 0.5
        part["field_test"] = {"median_blob_count": r(count_med, 1), "spread": r(spread, 3), "particle_area_share": r(small_area, 5),
                              "large_motion_share": r(big_motion, 5), "rule": "count>=8 and spread>0.12 (candidate); clean when particle area > large-motion area",
                              "known_failures": "false positive on dappled light and animated logos; false negative when rain merges into large regions",
                              "needs_visual_confirmation": kind != "no_particle_field_detected"}
        part["particle_type"] = {"inferred": kind, "confidence": conf,
                                 "evidence": {"streakiness": r(s_med, 2), "roundness": r(r_med, 2), "downward_share": r(d_med, 2), "frames_share": r(frac, 2)}}
    # sway: dominant oscillation of the subject-motion vector
    spd = series(rows, "motion.mean_speed")
    dirn = np.radians(series(rows, "motion.direction_deg"))
    sway = NM
    if len(rows) >= int(1.5 * fps):
        vxs, vys = np.nan_to_num(spd * np.cos(dirn)), np.nan_to_num(spd * np.sin(dirn))
        sig = vys if vys.std() >= vxs.std() else vxs
        if sig.std() > 1e-5:
            spec = np.abs(np.fft.rfft(sig - sig.mean())) ** 2
            freqs = np.fft.rfftfreq(len(sig), 1 / fps)
            band = (freqs > 0.3) & (freqs < 4)
            if band.any() and spec[band].sum() / (spec[1:].sum() + 1e-12) > 0.3:
                k = np.flatnonzero(band)[int(np.argmax(spec[band]))]
                sway = {"frequency_hz": r(freqs[k], 2), "amplitude_frame_widths_per_frame": r(sig.std(), 5),
                        "power_share_in_band": r(spec[band].sum() / (spec[1:].sum() + 1e-12), 2)}
    delta = series(rows, "lighting.exposure_delta")
    mad = series(rows, "transition.mad_prev")
    med = np.nanmedian(mad[1:]) if len(mad) > 1 else 0
    hits = [int(i) for i in range(2, len(rows)) if abs(np.nan_to_num(delta[i])) > 0.1 or (mad[i] > max(6 * med, 8) and i > 1)]
    return {"particles": part, "sway": sway, "impacts_or_flashes": {"frames": hits, "note": "exposure jump > 0.1 luma or frame difference > 6x the shot median"},
            "cloth_hair_fluid": NM, "rigid_body_collisions": NM}


def composition_section(rows, fps, meta):
    g = lambda k: series(rows, f"composition.{k}")
    sx, sy = g("subject_x"), g("subject_y")
    grid = np.array([x["depth"]["sharpness_grid3x3"] for x in rows if x["depth"]["sharpness_grid3x3"]])
    ce = series(rows, "depth.sharpness_centre_over_edges")
    dof = NM
    if ce[~np.isnan(ce)].size:
        med = float(np.nanmedian(ce))
        t = np.arange(len(ce))[~np.isnan(ce)]
        slope = float(np.polyfit(t, ce[~np.isnan(ce)], 1)[0]) * fps if t.size > 4 else 0.0
        dof = {"centre_over_edges_sharpness": r(med, 3), "inferred": "shallow_depth_of_field_centre_focus" if med > 1.5 else "deep_or_even_focus",
               "rack_focus_slope_per_second": r(slope, 3)}
    x0, y0, x1, y1 = meta["content_rect_640"]
    return {"subject_centre": {"x": nz(sx, np.median), "y": nz(sy, np.median), "path": [[r(sx[i]), r(sy[i])] for i in np.linspace(0, len(rows) - 1, min(9, len(rows))).astype(int)]},
            "subject_area": nz(g("subject_area"), np.median), "subject_bbox_median": [nz(np.array([x["composition"]["subject_bbox"][k] if x["composition"]["subject_bbox"] else np.nan for x in rows]), np.median) for k in range(4)],
            "distance_to_rule_of_thirds": nz(g("dist_to_thirds"), np.median), "horizon_tilt_deg": nz(g("horizon_tilt_deg"), np.median),
            "horizon_strength": nz(g("horizon_strength"), np.median), "edge_density": nz(g("edge_density"), np.median),
            "depth_of_field": dof, "sharpness_grid3x3_mean": [r(v, 2) for v in grid.mean(axis=0)] if grid.size else NM,
            "letterbox_content_rect_640": [x0, y0, x1, y1], "aspect_content": r((x1 - x0) / (y1 - y0), 3),
            "caveat": "saliency box is crude and burned-in subtitles/logos influence edge_density; see text_on_screen"}


def colour_section(rows, fps):
    cols, wts = [], []
    for x in rows:
        for c in x["colour"]["palette"]:
            cols.append(c["rgb"]); wts.append(c["share"])
    pal = NM
    if cols:
        data = np.array(cols, np.float32)
        k = min(6, len(data))
        crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
        _, labels, centres = cv2.kmeans(data, k, None, crit, 2, cv2.KMEANS_PP_CENTERS)
        share = np.bincount(labels.ravel(), weights=np.array(wts), minlength=k)
        share = share / (share.sum() + 1e-9)
        order = np.argsort(-share)
        pal = [{"rgb": [int(v) for v in centres[i]], "share": r(share[i], 3)} for i in order]
    tint = lambda key: [nz(np.array([(x["colour"][key] or [np.nan] * 3)[c] for x in rows], float), np.median) for c in range(3)]
    return {"palette": pal, "saturation_mean": nz(series(rows, "colour.saturation_mean"), np.median), "colourfulness": nz(series(rows, "colour.colourfulness"), np.median),
            "grade": {"shadow_tint_rgb": tint("shadow_tint_rgb"), "highlight_tint_rgb": tint("highlight_tint_rgb"),
                      "meaning": "RGB deviation from neutral in the darkest / brightest 20% of pixels"}}


def colour_regions_section(grid_frames, subject_bbox_xywh, subject_source):
    """Where the colours sit, from the measured 32x18 colour grid (colour_grid32x18.npy, content area only): median RGB of the top,
    middle and bottom thirds and of the subject box, over the shot. A colour script's blocking, not a picture: four colours."""
    if grid_frames is None or len(grid_frames) == 0:
        return NM
    g = np.median(grid_frames.astype(np.float32), axis=0)            # [18,32,3] RGB
    gh, gw = g.shape[:2]
    band = lambda y0, y1: [int(v) for v in np.median(g[y0:y1].reshape(-1, 3), axis=0)]
    out = {"top_third_rgb": band(0, gh // 3), "middle_third_rgb": band(gh // 3, 2 * gh // 3), "bottom_third_rgb": band(2 * gh // 3, gh),
           "subject_rgb": NM, "subject_bbox_xywh": NM, "subject_source": NM,
           "measured_on": "colour_grid32x18.npy (per-frame cell means of the content area), median over the shot"}
    if subject_bbox_xywh is not None and all(v is not None and v == v for v in subject_bbox_xywh):
        x, y, w, h = subject_bbox_xywh
        x0, x1 = int(np.floor(x * gw)), int(np.ceil((x + w) * gw))
        y0, y1 = int(np.floor(y * gh)), int(np.ceil((y + h) * gh))
        cells = g[max(y0, 0):min(max(y1, y0 + 1), gh), max(x0, 0):min(max(x1, x0 + 1), gw)].reshape(-1, 3)
        if len(cells):
            out.update(subject_rgb=[int(v) for v in np.median(cells, axis=0)], subject_bbox_xywh=[r(v) for v in subject_bbox_xywh], subject_source=subject_source)
        if subject_source and subject_source.startswith("characters.face_track"):
            out["character"] = character_colours(g, subject_bbox_xywh)
    return out


def character_colours(g, face_xywh):
    """Measured colours of a character around its detected face box (anime face boxes span brows to chin): hair = band above
    the box, skin = lower middle of the box, body = band below the box. Median of 32x18 grid cells; NOT MEASURED if the band
    falls outside the frame."""
    gh, gw = g.shape[:2]
    x, y, w, h = face_xywh

    def med(x0, y0, x1, y1):
        c0, c1 = max(int(np.floor(x0 * gw)), 0), min(int(np.ceil(x1 * gw)), gw)
        r0, r1 = max(int(np.floor(y0 * gh)), 0), min(int(np.ceil(y1 * gh)), gh)
        if c1 <= c0 or r1 <= r0:
            return NM
        return [int(v) for v in np.median(g[r0:r1, c0:c1].reshape(-1, 3), axis=0)]
    return {"hair_rgb": med(x + 0.1 * w, y - 0.35 * h, x + 0.9 * w, y + 0.05 * h),
            "skin_rgb": med(x + 0.3 * w, y + 0.45 * h, x + 0.7 * w, y + 0.85 * h),
            "body_rgb": med(x - 0.2 * w, y + 1.25 * h, x + 1.2 * w, 1.0),
            "measured_on": "32x18 colour grid cells above / inside / below the median face box"}


def transition_section(rows, prev_rows, next_rows, fps):
    def edge_kind(window_rows, boundary_score, side):
        diss = np.nanmax(series(window_rows, "transition.dissolve_score")) if window_rows else float("nan")
        fb = series(window_rows, "transition.fade_black_score"); fw = series(window_rows, "transition.fade_white_score")
        lum = series(window_rows, "lighting.luma_mean")
        kind = "hard_cut"
        if not np.isnan(diss) and diss > 0.25:
            kind = "dissolve"
        elif np.nanmax(fb) > 0.5 and lum.size > 4 and abs(lum[-1] - lum[0]) > 0.15:
            kind = "fade_through_black"
        elif np.nanmax(fw) > 0.5 and lum.size > 4 and abs(lum[-1] - lum[0]) > 0.15:
            kind = "fade_through_white"
        return {"inferred": kind, "boundary_frame_difference": r(boundary_score, 2), "max_dissolve_score": r(diss, 3),
                "max_fade_black": r(np.nanmax(fb), 3), "max_fade_white": r(np.nanmax(fw), 3)}
    first, last = rows[:6], rows[-6:]
    return {"in": edge_kind(first, rows[0]["transition"]["mad_prev"] if rows[0]["transition"]["mad_prev"] is not None else float("nan"), "in") if prev_rows is not None else {"inferred": "start_of_video"},
            "out": edge_kind(last, rows[-1]["transition"]["mad_next"] if rows[-1]["transition"]["mad_next"] is not None else float("nan"), "out") if next_rows is not None else {"inferred": "end_of_video"}}


def audio_section(rows, fps, transcript):
    rms = series(rows, "audio.rms_db")
    if np.isnan(rms).all():
        return {"loudness": NM}
    beats = [i for i, x in enumerate(rows) if x["audio"]["beat_onset"]]
    tempo = NM
    if len(beats) >= 4:
        ibi = np.diff(beats) / fps
        tempo = {"bpm_from_median_beat_interval": r(60 / np.median(ibi), 1), "beats": len(beats), "note": "spectral-flux onsets, not a tempo tracker; treat as a hint"}
    step = max(1, int(fps / 4))
    curve = [r(np.nanmean(rms[i:i + step]), 1) for i in range(0, len(rows), step)]
    t0, t1 = rows[0]["t"], rows[-1]["t"] + 1 / fps
    words = NM
    if transcript is not None:
        words = [s for s in transcript if s["end"] > t0 and s["start"] < t1] or "no speech segments in this shot"
    return {"rms_db_mean": nz(rms, np.mean), "rms_db_peak": nz(rms, np.max), "loudness_curve_db_per_quarter_second": curve,
            "spectral_centroid_hz": nz(series(rows, "audio.spectral_centroid_hz"), np.median),
            "band_shares_low_mid_high": [nz(series(rows, f"audio.{b}_share"), np.mean) for b in ("low", "mid", "high")],
            "onset_strength_mean": nz(series(rows, "audio.onset_strength"), np.mean), "beat_frames_in_shot": beats, "tempo": tempo,
            "speech_band_ratio_median": nz(series(rows, "audio.speech_band_ratio"), np.median),
            "spoken_words_whisper": words, "music_notes_key_instruments": NM}


def characters_section(rows, fps):
    cnt = series(rows, "characters.count")
    scales = [x["characters"]["shot_scale"] for x in rows if x["characters"]["shot_scale"]]
    keys = np.linspace(0, len(rows) - 1, min(8, len(rows))).astype(int)
    track = []
    for i in keys:
        faces = rows[i]["characters"]["faces"]
        big = max(faces, key=lambda f: f[3]) if faces else None
        track.append({"frame": int(i), "faces": len(faces), "largest_face_bbox_xywh": big})
    return {"detector": "lbpcascade_animeface (misses profiles, hair-only and stylised faces: 0 detections does NOT mean no character)",
            "frames_with_face_share": r(float(np.nanmean(cnt > 0)), 3), "max_faces": int(np.nanmax(cnt)),
            "shot_scale_by_largest_face": {s: scales.count(s) for s in sorted(set(scales))} or NM, "face_track": track,
            "identity_wardrobe_pose_expression": NM}


def text_section(rows, fps):
    share = float(np.mean([x["text_on_screen"]["subtitle_present"] for x in rows]))
    return {"subtitle_present_share": r(share, 3), "subtitle_stroke_share_median": nz(series(rows, "text_on_screen.subtitle_stroke_share"), np.median),
            "text_content": NM, "corner_logo": NM,
            "caveat": "burned-in subtitles are an overlay, not part of the animation: exclude the lower band from frame scoring when present"}


# ----------------------------------------------------------------------------- blender directives
def D(setting, value, source, conf):
    return {"setting": setting, "value": value, "source_metric": source, "confidence": conf}


def blender_directives(s):
    out = []
    cam, li, ph, co, cl = s["camera"], s["lighting"], s["physics"], s["composition"], s["colour"]
    if isinstance(cam.get("path_keyframes"), list):
        out.append(D("camera.keyframes(shift_x/shift_y/scale/roll)", cam["path_keyframes"], "camera.path_keyframes (Farneback flow + RANSAC similarity)", 0.7))
        out.append(D("camera.noise_shake", {"rms_frame_widths": cam["shake_rms_frame_widths"], "enabled": cam["handheld_shake"]}, "camera.shake_rms_frame_widths", 0.5))
    if isinstance(co["depth_of_field"], dict):
        shallow = co["depth_of_field"]["inferred"].startswith("shallow")
        out.append(D("camera.data.dof.use_dof", shallow, "composition.depth_of_field.centre_over_edges_sharpness", 0.5))
    if cl["palette"] != NM:
        out.append(D("world.color", cl["palette"][0]["rgb"], "colour.palette[0] (largest share)", 0.4))
    if li["key_direction_screen_deg"]["angle"] is not None:
        tmb = li["top_minus_bottom"] or 0.0
        out.append(D("light.key.sun.direction", {"screen_angle_deg": li["key_direction_screen_deg"]["angle"], "elevation_deg": r(30 + 60 * float(np.clip(tmb / 0.3, -1, 1)), 1)},
                     "lighting.key_direction_screen_deg + top_minus_bottom", 0.35))
    out.append(D("light.key.energy_relative", li["highlight_luma_p95"], "lighting.highlight_luma_p95", 0.5))
    out.append(D("light.fill.energy_relative", li["ambient_luma_p5"], "lighting.ambient_luma_p5", 0.5))
    out.append(D("compositor.glare(bloom).mix", li["bloom"], "lighting.bloom (halo energy around bright pixels)", 0.5))
    out.append(D("compositor.vignette.strength", li["vignette_corner_over_centre"], "lighting.vignette_corner_over_centre", 0.5))
    out.append(D("compositor.colour_balance", cl["grade"], "colour.grade (shadow/highlight tint)", 0.5))
    out.append(D("world.exposure_keyframes", li["exposure_luma"]["keyframes"], "lighting.exposure_luma.keyframes", 0.6))
    if li["flash_frames"]:
        out.append(D("light.energy_flash_keyframes", li["flash_frames"], "lighting.flash_frames (exposure jump > 0.1)", 0.6))
    pt = ph["particles"]["particle_type"]
    if isinstance(pt, dict) and pt["inferred"] != "no_particle_field_detected":
        out.append(D("particle_system(only after visual confirmation)", {"type": pt["inferred"], "count_per_frame": ph["particles"]["mean_particle_count"],
                                         "velocity_fw_per_s": ph["particles"].get("velocity_frame_widths_per_second"), "gravity_wind": ph["particles"]["gravity_wind"]},
                     "physics.particles (moving-blob statistics)", pt["confidence"]))
    if isinstance(ph["sway"], dict):
        out.append(D("modifier.noise/sway(hair, cloth, foliage)", ph["sway"], "physics.sway (FFT of subject motion)", 0.3))
    out.append(D("render.frame_step(cadence_on_n)", s["timing"]["cadence_on_n"], "timing.cadence_on_n", 0.7))
    for side in ("in", "out"):
        k = s["transitions"][side]["inferred"]
        if k not in ("hard_cut", "start_of_video", "end_of_video"):
            out.append(D(f"sequencer.transition_{side}", k, f"transitions.{side}", 0.5))
    out.append(D("light.rim_light, cast_shadows, materials, character_rig", NM, "not derivable from pixel statistics; needs the semantic pass", 0.0))
    return out


# ----------------------------------------------------------------------------- driver
def contact_sheet(frames_dir, lo, hi, out_path, n=6):
    idx = np.linspace(lo, hi - 1, min(n, hi - lo)).astype(int)
    tiles = []
    for i in idx:
        im = cv2.resize(cv2.imread(str(frames_dir / f"f_{i + 1:05d}.jpg")), (420, 236))
        cv2.putText(im, f"f{i}", (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(im, f"f{i}", (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
        tiles.append(im)
    while len(tiles) % 3:
        tiles.append(np.zeros_like(tiles[0]))
    cv2.imwrite(str(out_path), np.vstack([np.hstack(tiles[i:i + 3]) for i in range(0, len(tiles), 3)]))


def expand(spec, n):
    if not spec:
        return list(range(n))
    out = []
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b or a) + 1))
    return out


def find_slug(fragment):
    hits = [p for p in OUT.iterdir() if p.is_dir() and fragment in p.name]
    if len(hits) != 1:
        sys.exit(f"'{fragment}' matches {[h.name for h in hits]}")
    return hits[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--shots", default="")
    a = ap.parse_args()
    D_ = find_slug(a.slug)
    meta = json.loads((D_ / "meta.json").read_text(encoding="utf-8"))
    fps = meta["fps"]
    rows = [json.loads(x) for x in (D_ / "frames_table.jsonl").read_text(encoding="utf-8").splitlines()]
    shots = json.loads((D_ / "shots.json").read_text(encoding="utf-8"))["shots"]
    tr_path = ROOT / "blender_agent" / "skills" / "sources" / D_.name / "transcript.json"
    transcript = json.loads(tr_path.read_text(encoding="utf-8")) if tr_path.exists() else None
    (D_ / "shots").mkdir(exist_ok=True)
    (D_ / "sheets").mkdir(exist_ok=True)
    sem_path = D_ / "semantic.json"          # vision pass (frame-script-standard step 3), kept apart so a rebuild never wipes it
    semantic = json.loads(sem_path.read_text(encoding="utf-8")) if sem_path.exists() else None
    grid_path = D_ / "colour_grid32x18.npy"
    grid32 = np.load(grid_path) if grid_path.exists() else None
    index = []
    for i in expand(a.shots, len(shots)):
        sh = shots[i]
        rs = rows[sh["start"]:sh["end"]]
        script = {"slug": D_.name, "shot": i, "frames": [sh["start"], sh["end"]], "seconds": [r(sh["start"] / fps, 3), r(sh["end"] / fps, 3)],
                  "standard": "training/SPEC.md section 4 -- measured or NOT MEASURED",
                  "timing": timing_section(rs, fps), "camera": camera_section(rs, fps), "lighting": lighting_section(rs, fps),
                  "motion": motion_section(rs, fps), "physics": physics_section(rs, fps), "composition": composition_section(rs, fps, meta),
                  "colour": colour_section(rs, fps),
                  "transitions": transition_section(rs, rows[sh["start"] - 1:sh["start"]] or None, rows[sh["end"]:sh["end"] + 1] or None, fps),
                  "audio": audio_section(rs, fps, transcript), "characters": characters_section(rs, fps), "text_on_screen": text_section(rs, fps),
                  "semantic": {"setting": NM, "characters": NM, "actions": NM, "props": NM, "weather_particles_seen": NM, "mood": NM, "filled_by": None}}
        ch, co = script["characters"], script["composition"]
        faces = [t["largest_face_bbox_xywh"] for t in ch["face_track"] if t.get("largest_face_bbox_xywh")] if isinstance(ch["face_track"], list) else []
        if faces and isinstance(ch["frames_with_face_share"], (int, float)) and ch["frames_with_face_share"] >= 0.5:
            box, src = list(np.median(np.array(faces, float), axis=0)), "characters.face_track (median largest face)"
        elif isinstance(co["subject_bbox_median"], list) and None not in co["subject_bbox_median"]:
            box, src = co["subject_bbox_median"], "composition.subject_bbox_median (saliency)"
        else:
            box, src = None, None
        script["colour"]["regions"] = colour_regions_section(grid32[sh["start"]:sh["end"]] if grid32 is not None else None, box, src)
        if semantic and str(i) in semantic["shots"]:
            script["semantic"] = {**semantic["shots"][str(i)], "filled_by": semantic["filled_by"]}
        script["blender_directives"] = blender_directives(script)
        (D_ / "shots" / f"shot_{i:02d}.json").write_text(json.dumps(script, indent=1), encoding="utf-8")
        contact_sheet(D_ / "frames", sh["start"], sh["end"], D_ / "sheets" / f"shot_{i:02d}.jpg")
        index.append({"shot": i, "frames": script["frames"], "camera": script["camera"]["move"]["inferred"] if isinstance(script["camera"]["move"], dict) else script["camera"]["move"],
                      "cadence_on_n": script["timing"]["cadence_on_n"],
                      "particles": script["physics"]["particles"]["particle_type"]["inferred"] if isinstance(script["physics"]["particles"]["particle_type"], dict) else NM,
                      "transition_in": script["transitions"]["in"]["inferred"], "faces_share": script["characters"]["frames_with_face_share"]})
    (D_ / "script.json").write_text(json.dumps({"slug": D_.name, "shots": index}, indent=1), encoding="utf-8")
    print(f"{len(index)} shot scripts -> {D_}/shots  (contact sheets in {D_}/sheets)")


if __name__ == "__main__":
    main()
