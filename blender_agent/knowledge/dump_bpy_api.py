"""Runs INSIDE Blender:  blender -b --factory-startup --python dump_bpy_api.py -- out.jsonl

Dumps the installed Blender's own Python API (operators + RNA types + their properties, enum values,
functions) as searchable text chunks. Because it comes from the running binary it is always exactly
the right version -- no stale docs.
"""
import json
import sys

import bpy

out_path = sys.argv[sys.argv.index("--") + 1]
MAX_PROPS_PER_CHUNK = 22


def enum_ids(prop, limit=30):
    try:
        ids = [e.identifier for e in prop.enum_items]
    except Exception:
        return ""
    more = "..." if len(ids) > limit else ""
    return " {" + ", ".join(ids[:limit]) + more + "}" if ids else ""


def prop_line(p):
    extra = enum_ids(p) if p.type == "ENUM" else ""
    sub = f"/{p.subtype}" if p.subtype not in ("NONE", "") else ""
    ro = " (read-only)" if p.is_readonly else ""
    ln = f" len={p.array_length}" if getattr(p, "array_length", 0) else ""
    ptr = f" -> {p.fixed_type.identifier}" if p.type in ("POINTER", "COLLECTION") and p.fixed_type else ""
    return f"  {p.identifier}: {p.type}{sub}{ln}{ptr}{ro}{extra}. {p.description}".rstrip()


chunks = []
version = bpy.app.version_string

# ---- operators
for modname in sorted(dir(bpy.ops)):
    if modname.startswith("_"):
        continue
    mod = getattr(bpy.ops, modname)
    for opname in sorted(dir(mod)):
        if opname.startswith("_"):
            continue
        try:
            rna = getattr(mod, opname).get_rna_type()
        except Exception:
            continue
        lines = [f"bpy.ops.{modname}.{opname}()  # {rna.name}", rna.description or ""]
        for p in rna.properties:
            if p.identifier != "rna_type":
                lines.append(prop_line(p))
        chunks.append({"source": f"blender-api:{version}", "title": f"bpy.ops.{modname}.{opname}", "text": "\n".join(lines)})

# ---- types
for name in sorted(dir(bpy.types)):
    cls = getattr(bpy.types, name, None)
    rna = getattr(cls, "bl_rna", None)
    if rna is None:
        continue
    base = rna.base.identifier if rna.base else ""
    header = f"bpy.types.{name}" + (f" (extends {base})" if base else "") + f"  # {rna.name}\n{rna.description or ''}"
    props = [p for p in rna.properties if p.identifier != "rna_type"]
    funcs = []
    for fn in rna.functions:
        args = ", ".join(a.identifier for a in fn.parameters if not a.is_output)
        funcs.append(f"  .{fn.identifier}({args}). {fn.description}".rstrip())
    parts = [props[i:i + MAX_PROPS_PER_CHUNK] for i in range(0, max(len(props), 1), MAX_PROPS_PER_CHUNK)] or [[]]
    for idx, group in enumerate(parts):
        lines = [header + (f"  [properties part {idx + 1}/{len(parts)}]" if len(parts) > 1 else "")]
        lines += [prop_line(p) for p in group]
        if idx == 0 and funcs:
            lines += ["  functions:"] + funcs[:25]
        chunks.append({"source": f"blender-api:{version}", "title": f"bpy.types.{name}", "text": "\n".join(lines)})

with open(out_path, "w", encoding="utf-8") as fh:
    for c in chunks:
        fh.write(json.dumps(c) + "\n")
print(f"[dump_bpy_api] wrote {len(chunks)} chunks from Blender {version}")
