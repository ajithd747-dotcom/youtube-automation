import sys, json, time
sys.path.insert(0, r"D:\youtube automation\blender_agent")
import blender_runner
names = sys.argv[1].split(",")
for n in names:
    t = time.time()
    r = blender_runner.run_job({"shot": {"style": "anime", "preset": n}, "width": 480, "height": 270, "fps": 12, "duration": 1.0, "quality": "draft",
                                "mode": "still", "out": rf"D:\youtube automation\blender_agent\work\recreate\p_{n}.png"}, timeout=300)
    print(n, r.get("ok"), (r.get("error") or "")[:160], round(time.time() - t), "s", (r.get("traceback") or "")[-300:] if not r.get("ok") else "")
