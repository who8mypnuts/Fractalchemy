"""Spike (evidence for plans/fragments-plan.md): compile every bundled example through the naive moderniser.

Run from samples/fragmentarium/Fragmentarium_Examples_Folder:  python3 plans/spikes/frag_compile_all_examples.py
Result at the time of planning: 138 of 188 runnable examples compiled with a 100-line moderniser; see the plan, appendix C.
"""
import sys, subprocess, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import moderngl
import frag_modernise_spike as spike
EX = Path("/workspace/Fractalchemy/samples/fragmentarium/Fragmentarium_Examples_Folder")
ctx = moderngl.create_standalone_context(require=330)
ok = fail = 0
fails = {}
for p in sorted(EX.rglob("*.frag")):
    if "Include" in p.parts: continue
    try:
        fs = spike.preprocess(p)
        spike.compile_program(ctx, fs)
        if fs["buffershader"]: spike.compile_program(ctx, fs["buffershader"])
        ok += 1
    except Exception as e:
        fail += 1
        msg = str(e).strip().splitlines()
        key = next((l for l in msg if "error" in l.lower()), msg[0] if msg else "?")[:160]
        fails.setdefault(key, []).append(str(p.relative_to(EX)))
print("ok", ok, "fail", fail)
for k, v in sorted(fails.items(), key=lambda kv: -len(kv[1])):
    print(len(v), k, "|", v[:3])
