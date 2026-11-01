"""Record the parameter inventory of every bundled example fragment — the fixture `tests/test_fragments_corpus.py` checks.

    python tools/fragments_snapshot.py            # rewrites tests/fragments_inventory.json

Run it after a deliberate preprocessor change (or after updating the bundled library) and review the diff: every
changed group / range / default / lock means a fragment will show different sliders than FragM shows.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fractalchemy.fragments.examples import EXAMPLES_DIR, all_examples  # noqa: E402
from fractalchemy.fragments.files import FileManager  # noqa: E402
from fractalchemy.fragments.preprocessor import Preprocessor  # noqa: E402

SNAPSHOT = Path(__file__).resolve().parents[1] / "tests" / "fragments_inventory.json"


def describe(param) -> dict:
    entry = {"type": param.glsl_type, "kind": param.kind, "group": param.group, "default": param.default, "lock": param.lock.value}
    for field in ("from_", "to", "texts", "channels", "normalize"):
        if hasattr(param, field):
            entry[field.rstrip("_")] = getattr(param, field)
    if param.slider.value:
        entry["slider"] = param.slider.value
    return entry


def inventory() -> dict:
    out = {}
    for path in all_examples():
        source = Preprocessor(FileManager(original=path)).parse(path.read_text(encoding="utf-8", errors="replace"), path)
        out[str(path.relative_to(EXAMPLES_DIR))] = {
            "camera": source.camera_kind, "buffer": source.buffer, "buffershader": source.buffer_shader is not None,
            "presets": list(source.presets), "params": {p.name: describe(p) for p in source.all_params},
            "flags": [source.clear_on_change, source.subframes_between_redraws, source.subframe_max],
        }
    return out


def write_snapshot(data: dict, path: Path = SNAPSHOT) -> None:
    """One fragment per line, so a diff shows which fragment changed without a two-megabyte indent."""
    lines = [f" {json.dumps(name)}: {json.dumps(entry, sort_keys=True, default=list)}" for name, entry in sorted(data.items())]
    path.write_text("{\n" + ",\n".join(lines) + "\n}\n", encoding="utf-8")


if __name__ == "__main__":
    write_snapshot(inventory())
    print(f"wrote {SNAPSHOT}")
