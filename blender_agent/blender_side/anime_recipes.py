"""Anime action shot presets (data-driven). A shot = {"style":"anime","preset":<name>,"params":{...}} -> build(shot, w, h, fps, duration).

Timing inside a preset is in seconds LOCAL to the shot; presets scale their events with `duration` where it matters.
Each preset mirrors one beat of the analysed reference (see skills anime-action-speed-lines-and-accent etc.)."""
import math

import bpy

import anime_lib as A
import scene_lib as L
from scene_lib import STATE, frame, key

D = math.radians
PRESETS = {}


def preset(name):
    def deco(fn):
        PRESETS[name] = fn
        return fn
    return deco


def hero_path(j, pts, s=1.0):
    """Key the hero root along [(t, (x,y,z), (rx,ry,rz deg))] and return a t->pos function for hair follow-through."""
    for t, p, r in pts:
        key(j["root"], frame(t), loc=p, rot=tuple(D(x) for x in r), interp="BEZIER")

    def at(t):
        if t <= pts[0][0]:
            return pts[0][1]
        for (t0, p0, _), (t1, p1, _) in zip(pts, pts[1:]):
            if t0 <= t <= t1:
                u = (t - t0) / max(1e-6, t1 - t0)
                return tuple(p0[i] + (p1[i] - p0[i]) * u for i in range(3))
        return pts[-1][1]
    return at


def poses(j, seq):
    """seq: [(t, pose, blend?)] keyed at those times."""
    for item in seq:
        t, name = item[0], item[1]
        A.apply_pose(j, name, frame(t), item[2] if len(item) > 2 else None)


def world(ground=True, city=True, clouds=True, z=0.0):
    if ground:
        A.desert(z)
    if city:
        A.city_ledge(z, y=55)
    if clouds:
        A.clouds()


def rel(at, seq, roll=None, lens=35, shake=0.0):
    """Camera keys relative to the hero's path: seq = [(t, offset_xyz, look_offset_xyz)] -> world keys; guarantees framing."""
    keys = []
    for t, off, look in seq:
        h = at(t)
        keys.append((t, tuple(h[i] + off[i] for i in range(3)), tuple(h[i] + look[i] for i in range(3))))
    return A.cam_rig(keys, lens=lens, roll=roll, shake=shake)


@preset("black")
def p_black(p, T):
    w = bpy.context.scene.world.node_tree
    w.nodes.clear()
    out, bg = w.nodes.new("ShaderNodeOutputWorld"), w.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (0, 0, 0, 1)
    w.links.new(bg.outputs[0], out.inputs["Surface"])
    A.cam_rig([(0, (0, -10, 1), (0, 0, 1))])


@preset("plunge")
def p_plunge(p, T):
    world(clouds=False, z=0)
    A.cam_rig([(0, (0, -60, 120), (0, 30, 0)), (T, (0, -20, 60), (0, 30, 0))], lens=28, roll=[(0, -10), (T, -18)])
    v = bpy.context.scene.view_settings
    hold = float(p.get("black_until", 0.0))      # the reference is pure black for its first ~0.9 s, then the dark ground fades up
    v.exposure = -10.0
    v.keyframe_insert("exposure", frame=1)
    if hold:
        v.keyframe_insert("exposure", frame=frame(hold))
    v.exposure = -2.6
    v.keyframe_insert("exposure", frame=frame(hold + 0.1))
    v.exposure = -0.7
    v.keyframe_insert("exposure", frame=STATE["frames"])


@preset("aerial_dive")
def p_dive(p, T):
    world(z=0)
    j = A.build_hero((0, 0, 0), 1.0)
    at = hero_path(j, [(0, (0, 30, 130), (75, 0, 0)), (T, (0, 6, 92), (75, 0, 0))])
    poses(j, [(0, "dive"), (T, "dive", ("reach", 0.35))])
    A.hair_follow(j, at, STATE["fps"], gain=0.9)
    rel(at, [(0, (0, -5.2, 2.2), (0, 0, 0)), (T, (0, -4.6, 1.7), (0, 0, 0))], roll=[(0, 14), (T, 20)], lens=30, shake=0.04)
    A.shard((-9, 5, 100), (5.5, 6.5, 1), (D(90), 0, D(-25)), t0=T * 0.45, dur=T * 0.5)


@preset("side_lunge")
def p_lunge(p, T):
    world(z=0)
    j = A.build_hero((0, 0, 0), 1.0)
    at = hero_path(j, [(0, (-3, 24, 26), (0, 0, 90)), (T, (3, 24, 26), (0, 0, 90))])
    poses(j, [(0, "lunge"), (T, "lunge", ("jump", 0.3))])
    A.hair_follow(j, at, STATE["fps"], gain=1.3)
    rel(at, [(0, (0, -4.0, 0.9), (0.3, 0, 0.95)), (T, (0.5, -4.0, 0.9), (0.4, 0, 1.0))], lens=40, shake=0.02)
    A.laser((-14, 22, 29.6), (16, 22, 27.0), t0=T * 0.5, dur=0.16, width=0.07)
    A.laser((-14, 22, 28.4), (16, 22, 26.0), t0=T * 0.5, dur=0.16, width=0.07)


@preset("up_shot")
def p_up(p, T):
    world(ground=False, city=False)
    A.clouds(9, 300, 20)
    j = A.build_hero((0, 0, 0), 1.0)
    at = hero_path(j, [(0, (0, 30, 40), (0, 0, 20)), (T, (1, 30, 44), (0, 0, 20))])
    poses(j, [(0, "jump"), (T, "jump", ("reach", 0.4))])
    A.hair_follow(j, at, STATE["fps"], gain=1.0)
    rel(at, [(0, (0, -3.0, -1.7), (0, 0, 0.9)), (T, (0, -3.0, -1.5), (0, 0, 1.0))], roll=[(0, -8), (T, -14)], lens=28)
    A.laser((-20, 26, 26), (18, 26, 62), t0=T * 0.6, dur=0.2, width=0.12)


@preset("crouch_explosion")
def p_crouch(p, T):
    world(z=0)
    j = A.build_hero((0, 0, 0), 1.0)
    at = hero_path(j, [(0, (4, 24, 0.05), (0, 0, 210)), (T, (4.2, 24, 0.05), (0, 0, 210))])
    poses(j, [(0, "crouch"), (T, "crouch", ("lunge", 0.2))])
    A.hair_follow(j, at, STATE["fps"], gain=0.6)
    A.debris((-6, 44, 2.0), t0=0.05, life=T * 1.2, size=1.3)
    rel(at, [(0, (-2.2, -4.6, 1.2), (-3.5, 20, 2.6)), (T, (-1.8, -4.6, 1.3), (-3.5, 20, 3.4))], lens=26, shake=0.06)
    A.petals((3.4, 23, 1.6), 0.05, n=8, life=1.0, spread=2)
    A.shard((-1.0, 22, 6.0), (2.4, 3.0, 1), (D(90), 0, D(-70)), t0=0.15, dur=0.5)


@preset("top_down")
def p_top(p, T):
    world(ground=False, city=False)
    A.clouds(6, 200, -30)
    j = A.build_hero((0, 0, 0), 1.0)
    at = hero_path(j, [(0, (0, 0, 60), (-10, 0, 20)), (T, (1, 2, 58), (-6, 0, 30))])
    poses(j, [(0, "glide"), (T, "glide", ("jump", 0.25))])
    A.hair_follow(j, at, STATE["fps"], gain=0.8)
    rel(at, [(0, (0, 0.3, 6.0), (0, 0, 0)), (T, (0, 0.6, 5.4), (0.3, 0, 0))], roll=[(0, 25), (T, 40)], lens=34)


@preset("smear")
def p_smear(p, T):
    world(ground=False, city=False)
    A.clouds(8, 200, 40)
    j = A.build_hero((0, 0, 0), 1.0)
    at = hero_path(j, [(0, (0, 30, 40), (60, 20, 30)), (T, (0, 30, 40), (60, 20, 30))])
    poses(j, [(0, "reach")])
    A.hair_follow(j, lambda t: (t * 60, 0, 0), STATE["fps"], gain=2.2)
    A.cam_rig([(0, (-9, 24, 41), (0, 30, 40.5)), (T, (9, 24, 41), (0, 30, 40.5))], lens=34, roll=[(0, -6), (T, 8)], shake=0.05)
    bpy.context.scene.render.use_motion_blur = True
    bpy.context.scene.render.motion_blur_shutter = 1.6


@preset("speed_close")
def p_speed(p, T):
    world(z=0)
    j = A.build_hero((0, 0, 0), 1.0)
    at = hero_path(j, [(0, (0, 20, 30), (70, 0, 0)), (T, (0, 8, 27), (70, 0, 0))])
    poses(j, [(0, "reach"), (T, "reach", ("dive", 0.4))])
    A.hair_follow(j, at, STATE["fps"], gain=1.6)
    rel(at, [(0, (1.6, -3.0, 1.6), (0, 0, 1.2)), (T, (0.9, -2.4, 1.5), (0, 0, 1.3))], roll=[(0, 12), (T, 18)], lens=36, shake=0.05)
    A.shard((-1.2, 12, 31), (3.0, 3.6, 1), (D(80), 0, D(-35)), t0=T * 0.1, dur=T * 0.8)


@preset("grin_close")
def p_grin(p, T):
    world(ground=False, city=False)
    A.clouds(6, 150, 10)
    j = A.build_hero((0, 0, 0), 1.0)
    at = hero_path(j, [(0, (0, 10, 8), (0, 0, 0)), (T, (0.2, 9.4, 8), (0, 0, -4))])
    poses(j, [(0, "reach")])
    A.hair_follow(j, lambda t: (0, -8 * t, 0), STATE["fps"], gain=1.4)
    rel(at, [(0, (0.05, -1.25, 1.72), (0, 0, 1.72)), (T, (0.05, -1.15, 1.72), (0, 0, 1.72))], roll=[(0, 10), (T, 14)], lens=50)
    A.shard((-0.9, 11, 10.4), (0.7, 0.9, 1), (D(90), 0, D(-30)), t0=0.1, dur=T)


@preset("back_leap")
def p_back(p, T):
    world(ground=False, city=False)
    A.clouds(10, 300, 10)
    j = A.build_hero((0, 0, 0), 1.0)
    at = hero_path(j, [(0, (0, 14, 5), (0, 0, 180)), (T, (3, 20, 11), (0, 0, 172))])
    poses(j, [(0, "crouch"), (T * 0.4, "jump"), (T, "reach", ("jump", 0.3))])
    A.hair_follow(j, at, STATE["fps"], gain=1.2)
    A.petals((0, 14, 5), 0.05, n=30, life=1.6, spread=3.5)
    rel(at, [(0, (0.4, -3.4, 1.3), (0, 0, 1.2)), (T, (0.6, -3.1, 1.2), (0, 0, 1.2))], lens=32)


@preset("ledge_small")
def p_ledge(p, T):
    world(z=0)
    j = A.build_hero((0, 0, 0), 1.0)
    at = hero_path(j, [(0, (10, 50, 0.05), (0, 0, 200)), (T, (10.4, 50, 0.05), (0, 0, 200))])
    poses(j, [(0, "crouch")])
    A.hair_follow(j, at, STATE["fps"], gain=0.5)
    rel(at, [(0, (-6, -8, 2.6), (-2, 0, 1.3)), (T, (-5.6, -8, 2.7), (-4, 0, 2.3))], lens=30)


@preset("hair_close")
def p_hair(p, T):
    world(ground=False, city=False)
    A.clouds(6, 150, 5)
    j = A.build_hero((0, 0, 0), 1.0)
    at = hero_path(j, [(0, (0, 10, 6), (0, 0, 180)), (T, (0, 10, 6), (0, 0, 184))])
    poses(j, [(0, "dive")])
    A.hair_follow(j, lambda t: (0, -20 * t, 0), STATE["fps"], gain=1.0)
    rel(at, [(0, (0.15, -2.0, 1.75), (0, 0, 1.6)), (T, (0.25, -1.9, 1.7), (0, 0, 1.6))], roll=[(0, 6)], lens=45)


def build(shot, width, height, fps, duration, quality="standard"):
    q = {"draft": 4, "standard": 8, "final": 16}.get(quality, 8)
    A.setup(width, height, fps, duration, samples=q)
    name = shot.get("preset") if shot.get("preset") in PRESETS else "aerial_dive"
    PRESETS[name](dict(shot.get("params") or {}), max(0.2, STATE["frames"] / fps - 1 / fps))
    return name
