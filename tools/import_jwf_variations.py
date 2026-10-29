"""Import JWildfire variations into the Fractalchemy formula library.

Scans JWildfire's variation sources (`src/org/jwildfire/create/tina/variation/*Func.java`), translates each into
the formula dialect (`tools/jwf_translate.py`), compiles it with the formula compiler, checks that the numpy and
GLSL forms agree on the test points, and writes the survivors into:

    fractalchemy/formulas/library/jwildfire/<name>.c

Usage:
    python tools/import_jwf_variations.py --source ../JWildfire [--out fractalchemy/formulas/library/jwildfire]
                                          [--only name,name] [--dry-run] [--no-gl] [--report docs/jwildfire_import.md]

Names that a loaded formula already has (case-insensitively) are skipped — JWildfire carries the Apophysis
plugins we already have, and an import must never shadow one with different maths. The report lists every
variation that could not be imported and why, grouped by reason, so the hand-porting queue is explicit.
"""

from __future__ import annotations

import argparse
import collections
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import numpy as np  # noqa: E402

from fractalchemy.formulas import verify, workbench as W  # noqa: E402
from fractalchemy.formulas.lang import FormulaError, compile_source  # noqa: E402
from fractalchemy.fractal import variations as V  # noqa: E402
from jwf_translate import Translation, Unsupported, translate  # noqa: E402

VARIATION_DIR = Path("src/org/jwildfire/create/tina/variation")
HEADER = """/*
    Fractalchemy formula library — translated from the JWildfire variation
        {file}{author}
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

"""


def verify_variation(variation, ctx) -> tuple[bool, str]:
    """numpy finiteness, and numpy-vs-GLSL agreement when a context is given."""
    expected = verify.evaluate_numpy(variation, params=verify.test_params(variation))
    if np.isfinite(expected).mean() <= 0.75:
        return False, f"non-finite numpy output ({np.isfinite(expected).mean():.0%} finite)"
    if ctx is None:
        return True, "no GL check"
    try:
        report = verify.compare(variation, ctx)
    except Exception as exc:  # noqa: BLE001 - the driver rejected the GLSL
        return False, "GLSL compile: " + str(exc).splitlines()[-1][:160]
    return report.ok, "" if report.ok else report.message


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, default=ROOT.parent / "JWildfire", help="the JWildfire checkout")
    parser.add_argument("--out", type=Path, default=ROOT / "fractalchemy" / "formulas" / "library" / "jwildfire")
    parser.add_argument("--only", default="", help="comma-separated variation names to import")
    parser.add_argument("--dry-run", action="store_true", help="translate and verify, write nothing")
    parser.add_argument("--no-gl", action="store_true", help="skip the GLSL check")
    parser.add_argument("--report", type=Path, default=None, help="write a markdown report here")
    parser.add_argument("--overwrite", action="store_true", help="replace files already in the output folder")
    args = parser.parse_args()
    sources = sorted((args.source / VARIATION_DIR).glob("*Func.java"))
    if not sources:
        print(f"no variation sources under {args.source}", file=sys.stderr)
        return 2
    only = {n.strip() for n in args.only.split(",") if n.strip()}
    args.out.mkdir(parents=True, exist_ok=True)          # `#include "../ports/…"` lines resolve against it
    out_dir = args.out.resolve()
    existing = {name.lower() for name in V.catalogue()
                if not (W.origin_path(V.REGISTRY[name]) or Path("/")).resolve().is_relative_to(out_dir)}   # (earlier imports do not count)
    ctx = None
    if not args.no_gl:
        try:
            ctx = verify.create_context()
        except Exception as exc:  # noqa: BLE001
            print(f"no OpenGL context ({exc}); GLSL checks skipped", file=sys.stderr)
    imported: list[tuple[str, Translation]] = []
    failures: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)   # reason category -> [(name/file, detail)]
    skipped_existing = []
    for path in sources:
        java = path.read_text(encoding="utf-8", errors="replace")
        try:
            translation = translate(java, path.name)
        except Unsupported as exc:
            failures[_category(str(exc))].append((path.name, str(exc)))
            continue
        except Exception as exc:  # noqa: BLE001 - a translator bug: report, carry on
            failures["translator error"].append((path.name, f"{type(exc).__name__}: {exc}"))
            continue
        name = translation.name
        if only and name not in only:
            continue
        if name.lower() in existing:
            skipped_existing.append(name)
            continue
        try:
            compiled = compile_source(translation.source, origin=path.name, include_dir=args.out)
        except FormulaError as exc:
            failures["does not compile"].append((name, str(exc).split(": ", 1)[-1][:200]))
            continue
        except Exception as exc:  # noqa: BLE001
            failures["compiler error"].append((name, f"{type(exc).__name__}: {exc}"[:200]))
            continue
        try:
            ok, why = verify_variation(compiled.variation, ctx)
        except Exception as exc:  # noqa: BLE001
            ok, why = False, f"verification crashed: {type(exc).__name__}: {exc}"[:200]
        if not ok:
            failures["engines disagree" if "GLSL" not in why else "GLSL rejected"].append((name, why))
            continue
        imported.append((path.name, translation))
        if not args.dry_run:
            args.out.mkdir(parents=True, exist_ok=True)
            target = args.out / f"{name}.c"
            if target.exists() and not args.overwrite:
                continue
            author = f"\n        by {translation.author}" if translation.author else ""
            target.write_text(HEADER.format(file=path.name, author=author) + translation.source, encoding="utf-8")
    if ctx is not None:
        ctx.release()
    total = len(sources)
    print(f"{len(imported)} of {total} variations imported; {len(skipped_existing)} already in the library; "
          f"{sum(len(v) for v in failures.values())} not importable")
    for category, items in sorted(failures.items(), key=lambda kv: -len(kv[1])):
        print(f"  {category}: {len(items)}")
    if args.report:
        args.report.write_text(_report(imported, skipped_existing, failures, total), encoding="utf-8")
        print(f"report: {args.report}")
    return 0


def _category(reason: str) -> str:
    for key, category in (("GLSL vector", "GLSL helper classes (vec2 / vec3 / mat)"), ("complex-number", "Complex helper class"),
                          ("state between points", "state between points"), ("resources", "resources / images"), ("strings", "strings"),
                          ("Random", "a Random object"), ("external shapes", "external shapes"), ("run time", "code compiled at run time"),
                          ("specialised base class", "specialised base class"), ("prepost", "prepost variation"), ("helper", "helper methods"),
                          ("images", "resources / images")):
        if key in reason:
            return category
    return "unsupported construct"


def _report(imported, skipped_existing, failures, total) -> str:
    lines = ["# JWildfire import report", "",
             f"{total} variation sources scanned; **{len(imported)} imported**, {len(skipped_existing)} already in the library "
             f"(same name), {sum(len(v) for v in failures.values())} not importable.", "", "## Imported", ""]
    by_type: dict[str, list[str]] = collections.defaultdict(list)
    for _file, t in imported:
        kinds = [k for k in t.types if k in ("2D", "3D", "DC", "BLUR", "PRE", "POST", "CROP", "BASE_SHAPE", "SIMULATION", "ESCAPE_TIME_FRACTAL")]
        by_type[", ".join(kinds) or "other"].append(t.name + (f" ({t.author})" if t.author else ""))
    for kinds, names in sorted(by_type.items()):
        lines.append(f"* **{kinds}** ({len(names)}): " + ", ".join(sorted(names)))
    lines += ["", "## Not imported, by reason", ""]
    for category, items in sorted(failures.items(), key=lambda kv: -len(kv[1])):
        lines.append(f"### {category} ({len(items)})")
        lines.append("")
        for name, detail in sorted(items):
            lines.append(f"* `{name}` — {detail}")
        lines.append("")
    lines += ["## Already in the library", "", ", ".join(sorted(skipped_existing)), ""]
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
