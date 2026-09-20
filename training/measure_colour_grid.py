"""Measured colour layout of every frame: mean RGB per cell of a 32x18 grid over the picture area (letterbox removed).

    .venv/bin/python training/measure_colour_grid.py [slug-fragment]

Writes training/reference/<slug>/colour_grid32x18.npy, uint8 [n_frames, 18, 32, 3] (RGB). This is the first rung of the
recreation ladder (SPEC section 2): a layout script that is exactly what the pixels are, at a chosen resolution.
Coarser grids are area-averaged from it, so one measurement serves every rung.
"""
import multiprocessing as mp
import os
import sys
from pathlib import Path

import cv2
import numpy as np

REF = Path(__file__).resolve().parent / "reference"
GRID_W, GRID_H = 32, 18


def grid_for_chunk(args):
    paths, rect = args
    x0, y0, x1, y1 = rect
    out = []
    for p in paths:
        im = cv2.imread(str(p))[y0:y1, x0:x1]
        small = cv2.resize(im, (GRID_W, GRID_H), interpolation=cv2.INTER_AREA)
        out.append(cv2.cvtColor(small, cv2.COLOR_BGR2RGB))
    return np.stack(out)


def write_colour_grid(slug_dir):
    import json
    meta = json.loads((slug_dir / "meta.json").read_text(encoding="utf-8"))
    rect = tuple(meta["content_rect_640"])
    paths = sorted((slug_dir / "frames").glob("f_*.jpg"))
    chunks = [(paths[i:i + 64], rect) for i in range(0, len(paths), 64)]
    with mp.Pool(os.cpu_count() or 4) as pool:
        grid = np.concatenate(pool.map(grid_for_chunk, chunks, chunksize=1))
    np.save(slug_dir / "colour_grid32x18.npy", grid)
    return grid


if __name__ == "__main__":
    frag = sys.argv[1] if len(sys.argv) > 1 else ""
    for d in sorted(p for p in REF.iterdir() if p.is_dir() and frag in p.name):
        g = write_colour_grid(d)
        print(f"{d.name}: {g.shape} -> colour_grid32x18.npy")
