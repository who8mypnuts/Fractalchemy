"""Import Apophysis plugin sources into the Fractalchemy formula library.

Scans a tree of Apophysis plugin sources (loose `.c` / `.cpp` / `.h` files, SDK-style plugin
folders, and zip / 7z archives), assembles one self-contained source per plugin, applies the
small patches listed in `PATCHES`, compiles each with the formula compiler, checks that the
numpy and GLSL forms agree, and writes the survivors into the library:

    fractalchemy/formulas/library/apophysis7x/   sources shipped with Apophysis 7X
    fractalchemy/formulas/library/plugins/       community plugins

Usage:
    python tools/import_apo_plugins.py [--source samples/aposource] [--out fractalchemy/formulas/library]
                                       [--only name,name] [--dry-run] [--no-gl]

The report lists every plugin that could not be imported and why; those are ported by hand
(see `fractalchemy/formulas/library/ports/`). Existing files in the output folders are
overwritten only when the new source verifies, so a hand-fixed file is never clobbered by a
broken import.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import numpy as np  # noqa: E402

from fractalchemy.formulas.lang import FormulaError, compile_source  # noqa: E402
import test_variations as T  # noqa: E402  (imported before any GL context exists: it probes for OpenGL itself)

SDK_HEADERS = {"apoplugin.h", "variable_info.h", "apoplugin_classic.h", "apoplugin_msvc_novar.h", "apoplugin_msvc_var.h",
               "apoplugin_msvc.h", "dll.h"}
PLUGIN_NAME = re.compile(r'APO_PLUGIN\s*\(\s*"([^"]+)"\s*\)')
N_PLUGIN = re.compile(r'#define\s+N_PLUGIN\s+"([^"]+)"')
INCLUDE = re.compile(r'#include\s+"([^"]+)"')

# Source-level patches: plugin name -> list of (old, new) text replacements, applied after assembly.
# They repair sources that never compiled cleanly outside the author's own environment.
AM = "#define AM (1.0 / 2147483647.0)   /* (was missing from the source) */\n"
PATCHES: dict[str, list[tuple[str, str]]] = {
    "CircleLinear": [("", AM)],
    "CircleRand": [("", AM)],
    "CircleTrans1": [("", AM)],
    "JuliaRandomN": [("", AM)],
    "truc_eralex1": [("", AM)],
    "truc_eralex2": [("", AM)],
    "waves4": [("double(waves4_yfact);", "double waves4_yfact;")],
    "minkowskope": [("regex:(\\d\\.\\d*|\\d)d\\b", "\\g<1>")],   # Java-style `1.0d` literals
    "bwraps2": [("#define pre_bwraps2\n", "")],   # the shared source builds pre_bwraps2 unless told otherwise
    "bwrands": [("", "#define SGN(a) ((a) < 0 ? -1 : ((a) > 0 ? 1 : 0))   /* (was missing from the source) */\n")],
    "waves42": [("double(waves42_yfact);", "double waves42_yfact;"), ("double(waves42_freqx2);", "double waves42_freqx2;")],
    "scrambly": [("#include <stdlib.h> // for div and div_t", ""), ("div_t divresult;", "int divresult_quot, divresult_rem;"),
                 ("divresult = div(seed+j+1, LL2);", "divresult_quot = (seed+j+1) / LL2; divresult_rem = (seed+j+1) % LL2;"),
                 ("VAR(mx_rd[j]) = divresult.rem;", "VAR(mx_rd[j]) = divresult_rem;"),
                 ("divresult = div(swp, VAR(current_l));", "divresult_quot = swp / VAR(current_l); divresult_rem = swp % VAR(current_l);"),
                 ("Iy = divresult.quot; Ix = divresult.rem;", "Iy = divresult_quot; Ix = divresult_rem;"),
                 ("divresult = div(prn, idxmax-ridx);", "divresult_quot = prn / (idxmax-ridx); divresult_rem = prn % (idxmax-ridx);"),
                 ("ridx += divresult.rem;", "ridx += divresult_rem;")],
    "post_smartcrop": [("    double *xi, *yi, *zi;\n", ""),
                       ("""    if (VAR(post_scrop_static) == 2) {
        VAR(xi) = vp->pFPx;
        VAR(yi) = vp->pFPy;
        VAR(zi) = vp->pFPz;
    } else {
        VAR(xi) = vp->pFTx;
        VAR(yi) = vp->pFTy;
        VAR(zi) = vp->pFTz;
    }
""", ""),
                       ("    const double *xi = VAR(xi), *yi = VAR(yi), *zi = VAR(zi);",
                        "    double xi = VAR(post_scrop_static) == 2 ? FPx : FTx, yi = VAR(post_scrop_static) == 2 ? FPy : FTy, zi = VAR(post_scrop_static) == 2 ? FPz : FTz;"),
                       ("*xi", "xi"), ("*yi", "yi"), ("*zi", "zi")],
}

# Where a plugin's sources live decides the library folder.
GROUPS = (
    ("apophysis-7x/src/Plugin", "apophysis7x"),
    ("apophysis-plugins/plugins", "apophysis7x"),
)

HEADER = """/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        {origin}
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

"""


def extract_archives(source: Path, work: Path) -> None:
    """Unpack every zip / 7z under `source` (recursively) into `work`."""
    try:
        import py7zr
    except ImportError:  # pragma: no cover - optional
        py7zr = None
    todo = [p for p in source.rglob("*") if p.suffix.lower() in (".zip", ".7z")]
    seen = set()
    while todo:
        archive = todo.pop()
        if archive in seen:
            continue
        seen.add(archive)
        dest = work / (hashlib.md5(str(archive).encode()).hexdigest()[:8] + "_" + archive.stem)
        dest.mkdir(parents=True, exist_ok=True)
        try:
            if archive.suffix.lower() == ".zip":
                zipfile.ZipFile(archive).extractall(dest)
            elif py7zr is not None:
                py7zr.SevenZipFile(archive).extractall(dest)
            else:
                print(f"skipping {archive} (pip install py7zr to unpack 7z archives)")
                continue
        except Exception as exc:  # noqa: BLE001
            print(f"cannot unpack {archive}: {exc}")
            continue
        todo.extend(p for p in dest.rglob("*") if p.suffix.lower() in (".zip", ".7z"))


def find_sources(roots: list[Path]) -> dict[str, list[Path]]:
    """Plugin name → candidate entry files, best first."""
    found: dict[str, list[Path]] = collections.defaultdict(list)
    for root in roots:
        for path in sorted(root.rglob("*")):
            if path.suffix.lower() not in (".c", ".cpp", ".h", ".cc") or not path.is_file():
                continue
            if path.name in SDK_HEADERS or "/.mingw/" in path.as_posix():
                continue
            text = path.read_text(errors="replace")
            names = PLUGIN_NAME.findall(text) or N_PLUGIN.findall(text)
            if not names:
                continue
            entry = path
            sdk_entry = path.parent / "apoplugin.c"   # apophysis-plugins SDK layout: apoplugin.c includes the parts
            if sdk_entry.exists() and path.name != "apoplugin.c":
                entry = sdk_entry
            for name in names:
                if name.startswith("<%") or name == "example":
                    continue
                if entry not in found[name]:
                    found[name].append(entry)
    for name, entries in found.items():
        entries.sort(key=lambda p: _preference(p, name))
    return dict(found)


def _preference(path: Path, name: str) -> tuple:
    text = path.as_posix()
    rank = 3
    for needle, _ in GROUPS:
        if needle in text:
            rank = 0
    if "apo7x15d_plugin-pack" in text:
        rank = 1
    if "x64" in text or "64" in path.parent.name:
        rank = min(rank, 2)
    return (rank, len(text))


def assemble(entry: Path) -> str:
    """The entry file with its local (non-SDK) includes inlined."""
    def load(path: Path, depth: int) -> str:
        text = path.read_text(errors="replace")

        def repl(m: re.Match) -> str:
            inc = m.group(1)
            if inc in SDK_HEADERS or depth > 4:
                return f"// (SDK header {inc} implied)" if inc in SDK_HEADERS else ""
            target = path.parent / inc
            return load(target, depth + 1) if target.exists() else f"// (missing include {inc})"
        return INCLUDE.sub(repl, text)
    return load(entry, 0)


def group_for(entry: Path) -> str:
    text = entry.as_posix()
    for needle, group in GROUPS:
        if needle in text:
            return group
    return "plugins"


def verify(variation, ctx) -> tuple[bool, str]:
    """numpy vs GLSL agreement on the test points (see tests/test_variations.py)."""
    params = T.prepared_params(variation, T._params(variation))
    expected = T._run_numpy(variation, params)
    if ctx is None:
        return bool(np.isfinite(expected).mean() > 0.75), "no GL check"
    try:
        program = T._glsl_program(ctx, variation, params)
    except Exception as exc:  # noqa: BLE001
        return False, "GLSL compile: " + str(exc).splitlines()[-1][:160]
    actual = T._run_glsl(ctx, program)
    program.release()
    if variation.random:
        ok = np.isfinite(actual).mean() > 0.75 and np.isfinite(expected).mean() > 0.75
        return ok, "" if ok else "non-finite output"
    both = np.isfinite(expected) & np.isfinite(actual)
    if both.mean() <= 0.75:
        return False, f"non-finite output ({both.mean():.0%} finite)"
    scale = np.maximum(1.0, np.abs(expected[both]))
    close = np.isclose(actual, expected, atol=3e-4 * scale.max(), rtol=3e-4) | ~both
    bad_rows = int((~close.all(axis=1)).sum())
    if bad_rows <= 1:   # one point may sit on a float32 boundary of a discontinuity
        return True, ""
    return False, f"numpy/GLSL mismatch on {bad_rows} of {len(expected)} points"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default=str(ROOT / "samples" / "aposource"))
    ap.add_argument("--out", default=str(ROOT / "fractalchemy" / "formulas" / "library"))
    ap.add_argument("--only", default="", help="comma-separated plugin names")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-gl", action="store_true", help="skip the GLSL check")
    args = ap.parse_args()
    source, out = Path(args.source), Path(args.out)
    only = {n for n in args.only.split(",") if n}

    ctx = None
    if not args.no_gl:
        import moderngl
        ctx = moderngl.create_standalone_context(require=330)

    work = Path(tempfile.mkdtemp(prefix="apo-import-"))
    extract_archives(source, work)
    sources = find_sources([source, work])
    print(f"{len(sources)} plugin names found")
    from fractalchemy.fractal import variations as V
    native = {n for n, v in V.REGISTRY.items() if v.style == V.LEGACY}   # defined in Python: keep those
    imported, failed, skipped = [], [], []
    for name in sorted(sources, key=str.lower):
        if only and name not in only:
            continue
        if name in native and name not in only:
            skipped.append(name)
            continue
        last_error = "no source"
        for entry in sources[name]:
            text = assemble(entry)
            for old, new in PATCHES.get(name, []):
                if old == "":
                    text = new + text
                elif old.startswith("regex:"):
                    text = re.sub(old[6:], new, text)
                else:
                    text = text.replace(old, new)
            origin = entry.relative_to(source).as_posix() if entry.is_relative_to(source) else entry.name
            try:
                compiled = compile_source(text, origin=origin)
            except FormulaError as exc:
                last_error = str(exc).split(": ", 1)[-1]
                continue
            except Exception as exc:  # noqa: BLE001 - compiler bug: report it like any other failure
                last_error = f"internal error: {type(exc).__name__}: {exc}"
                continue
            if compiled.variation.name != name:
                last_error = f"declares {compiled.variation.name!r}"
                continue
            ok, why = verify(compiled.variation, ctx)
            if not ok:
                last_error = why
                continue
            target = out / group_for(entry) / f"{name}.c"
            if not args.dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(HEADER.format(origin=origin) + text, encoding="utf-8")
            imported.append((name, target.relative_to(out).as_posix(), compiled.spec.warnings))
            break
        else:
            failed.append((name, last_error))
    shutil.rmtree(work, ignore_errors=True)
    print(f"\nimported {len(imported)}:")
    for name, target, warnings in imported:
        print(f"  {name:28s} -> {target}" + (f"   ({'; '.join(warnings)})" if warnings else ""))
    print(f"\nnot imported {len(failed)}:")
    for name, why in failed:
        print(f"  {name:28s} {why}")
    if skipped:
        print(f"\nskipped (native Python definition exists): {', '.join(skipped)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
