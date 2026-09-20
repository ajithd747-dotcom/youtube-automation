"""Grade one Act 6 frame toward the Shinkai-style reference, to see what the pivot buys.

    python build/paper_heart/style_test.py

The reference's look is not one effect, it is a stack: blown highlights, heavy bloom off those
highlights, saturated colour with a cool shadow bias, atmospheric haze with depth, lens
aberration at the edges, and rain. This applies that stack to an existing render so the
difference is visible before committing to rebuilding anything.
"""
from pathlib import Path

import cv2
import numpy as np

SRC = Path("renders/paper_heart/act6/f_4752.png")
OUT = Path("renders/paper_heart/style_compare.png")


def bloom(img, thresh=170, sigma_a=9, sigma_b=35, amt_a=0.55, amt_b=0.40):
    """Two-radius bloom off the bright areas.

    One radius gives uniform haze; two gives a tight core glow plus a wide atmospheric wash,
    which is what the reference actually has around its highlights.
    """
    f = img.astype(np.float32)
    lum = f.max(axis=2)
    keep = np.clip((lum - thresh) / max(1.0, 255.0 - thresh), 0, 1)[..., None]
    bright = f * keep
    g = cv2.GaussianBlur(bright, (0, 0), sigma_a) * amt_a
    g += cv2.GaussianBlur(bright, (0, 0), sigma_b) * amt_b
    return 255.0 - (255.0 - f) * (255.0 - np.clip(g, 0, 255)) / 255.0


def aberration(img, px=2):
    """Split the channels slightly outward from centre - cheap lens character."""
    h, w = img.shape[:2]
    out = img.copy().astype(np.float32)
    for c, k in ((2, px), (0, -px)):                      # R out, B in
        M = np.float32([[1 + k / w, 0, -k / 2], [0, 1 + k / h, -k / 2]])
        out[:, :, c] = cv2.warpAffine(img[:, :, c].astype(np.float32), M, (w, h),
                                      borderMode=cv2.BORDER_REPLICATE)
    return out


def haze(img, strength=0.22, tint=(210, 190, 165)):
    """Aerial perspective: lift the far/bright half toward a warm atmospheric tint.

    Uses luminance as a stand-in for depth, which holds up here because the sky IS the distance.
    """
    f = img.astype(np.float32)
    lum = cv2.GaussianBlur(f.max(axis=2), (0, 0), 25)[..., None] / 255.0
    layer = np.ones_like(f) * np.array(tint, np.float32)
    return f * (1 - lum * strength) + layer * (lum * strength)


def rain(img, n=340, length=34, angle=-16, opacity=0.30, seed=3):
    """Thin motion-blurred streaks. The reference is a rain film; this is its texture."""
    h, w = img.shape[:2]
    rng = np.random.default_rng(seed)
    layer = np.zeros((h, w), np.float32)
    dx = int(round(length * np.sin(np.radians(angle))))
    for _ in range(n):
        x, y = rng.integers(0, w), rng.integers(0, h)
        cv2.line(layer, (x, y), (x + dx, y + length), float(rng.uniform(0.5, 1.0)), 1)
    layer = cv2.GaussianBlur(layer, (0, 0), 0.7)[..., None]
    return img.astype(np.float32) * (1 - layer * opacity) + 255.0 * layer * opacity


def grade(img, sat=1.30, contrast=1.10, shadow_tint=(18, 6, -10)):
    """High saturation, cool shadows, warm highs - the reference sits at sat ~90-147."""
    f = img.astype(np.float32)
    hsv = cv2.cvtColor(np.clip(f, 0, 255).astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * sat, 0, 255)
    f = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32)
    f = (f - 128.0) * contrast + 128.0
    dark = 1.0 - (f.max(axis=2, keepdims=True) / 255.0)    # weight toward shadows
    f += np.array(shadow_tint, np.float32) * dark
    return f


def main():
    src = cv2.imread(str(SRC))
    if src is None:
        print("no source frame yet:", SRC)
        return
    steps = [("original", src.astype(np.float32))]
    x = grade(src)
    steps.append(("+ grade", x.copy()))
    x = haze(np.clip(x, 0, 255).astype(np.uint8))
    steps.append(("+ haze", x.copy()))
    x = bloom(np.clip(x, 0, 255).astype(np.uint8))
    steps.append(("+ bloom", x.copy()))
    x = rain(np.clip(x, 0, 255).astype(np.uint8))
    x = aberration(np.clip(x, 0, 255).astype(np.uint8))
    steps.append(("+ rain + lens", x.copy()))

    tiles = []
    for name, im in steps:
        t = cv2.resize(np.clip(im, 0, 255).astype(np.uint8), (620, 349))
        cv2.rectangle(t, (0, 0), (620, 26), (0, 0, 0), -1)
        cv2.putText(t, name, (8, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1,
                    cv2.LINE_AA)
        tiles.append(t)
    while len(tiles) % 3:
        tiles.append(np.zeros_like(tiles[0]))
    rows = [np.hstack(tiles[i:i + 3]) for i in range(0, len(tiles), 3)]
    cv2.imwrite(str(OUT), np.vstack(rows))

    fin = np.clip(steps[-1][1], 0, 255).astype(np.uint8)
    hsv = cv2.cvtColor(fin, cv2.COLOR_BGR2HSV)
    print("graded : sat %.1f  val %.1f  contrast %.1f"
          % (hsv[:, :, 1].mean(), hsv[:, :, 2].mean(), fin.std()))
    print("target : sat 54-147, contrast 38-93  (measured off the reference)")
    print("->", OUT)


if __name__ == "__main__":
    main()
