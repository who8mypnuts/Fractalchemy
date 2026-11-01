"""Render or check Fragmentarium fragments from the command line — what FragM's `.fqs` scripts did.

    python tools/render_frag.py Mandelbulb.frag --out out/bulb.png --size 1920x1080 --tiles 2 --subframes 200
    python tools/render_frag.py Mandelbulb.frag --all-presets --out out/            # one image per preset
    python tools/render_frag.py anim.fafrag --frames 0-249 --fps 25 --length 10 --out out/anim.png [--video mp4]
    python tools/render_frag.py --check fractalchemy/fragments/library/Examples/**/*.frag   # compile only; exit code = failures
    python tools/render_frag.py big.frag --out out/big.png --tiles 4 --tile-range 0-7 --tile-dir out/tiles   # half the tiles …
    python tools/render_frag.py big.frag --out out/big.png --tiles 4 --tile-range 8-15 --tile-dir out/tiles  # … the other half
    python tools/render_frag.py big.frag --out out/big.png --tiles 4 --assemble --tile-dir out/tiles         # join them
    python tools/render_frag.py bulb.frag --out out/bulb.png --stereo anaglyph      # or sbs; --panorama for 360°

Headless: a standalone OpenGL context is created (EGL / llvmpipe work without a display).
"""

from __future__ import annotations

import argparse
import glob
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fractalchemy.fragments import batch  # noqa: E402
from fractalchemy.fragments.animation import AnimationSettings  # noqa: E402
from fractalchemy.fragments.gl.engine import FragEngine  # noqa: E402
from fractalchemy.fragments.render_settings import FragFinalSettings  # noqa: E402


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    add_arguments(parser)
    return parser.parse_args(argv)


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """The options (shared with the Fragments window's help page)."""
    parser.add_argument("fragments", nargs="+", help=".frag / .fafrag files (globs allowed)")
    parser.add_argument("--check", action="store_true", help="preprocess and compile only; report failures")
    parser.add_argument("--out", default="", help="output file (or folder with --all-presets / --keyframes)")
    parser.add_argument("--preset", default="Default", help="the preset to apply (default: Default)")
    parser.add_argument("--all-presets", action="store_true", help="render every preset into --out (a folder)")
    parser.add_argument("--keyframes", action="store_true", help="render every KeyFrame preset into --out (a folder)")
    parser.add_argument("--size", default="1920x1080", help="tile size WIDTHxHEIGHT (default 1920x1080)")
    parser.add_argument("--tiles", type=int, default=1, help="tiles per side (default 1)")
    parser.add_argument("--padding", type=float, default=0.0, help="tile padding 0..1 (default 0)")
    parser.add_argument("--subframes", type=int, default=100, help="subframes per tile (default 100)")
    parser.add_argument("--frames", default="", help="animation frame range A-B (renders a numbered sequence)")
    parser.add_argument("--fps", type=int, default=None, help="frames per second (default: the fragment's metadata or 25)")
    parser.add_argument("--length", type=int, default=None, help="animation length in seconds (default: metadata or 10)")
    parser.add_argument("--format", default="", help="image format key (png, png16 → PNG at 16 bits, exr, jpeg, tiff, …); default from --out")
    parser.add_argument("--depth-alpha", action="store_true", help="EXR: write the depth buffer as the Z channel")
    parser.add_argument("--video", default="", help="encode the frames with ffmpeg (mp4, mp4-hevc, webm, mov, gif)")
    parser.add_argument("--include-path", action="append", default=[], help="extra include folder (repeatable)")
    parser.add_argument("--tile-range", default="", help="render only tiles A-B (row-major indices) into --tile-dir")
    parser.add_argument("--tile-dir", default="", help="folder the rendered tiles are kept in as .npz (default: <out>.tiles)")
    parser.add_argument("--resume", action="store_true", help="skip tiles already present in --tile-dir")
    parser.add_argument("--assemble", action="store_true", help="render nothing; join the tiles found in --tile-dir into the image")
    parser.add_argument("--region", default="", help="render a crop of the frame: X,Y,W,H as fractions (e.g. 0.25,0.25,0.5,0.5)")
    parser.add_argument("--stereo", default="none", choices=["none", "anaglyph", "sbs"], help="stereo pair: anaglyph (red/cyan) or side by side")
    parser.add_argument("--eye-separation", type=float, default=0.03, help="stereo eye distance as a fraction of the eye-target distance")
    parser.add_argument("--panorama", action="store_true", help="360° equirectangular (the fragment's EquiRectangular mode; use a 2:1 size)")
    parser.add_argument("--quiet", action="store_true")


def expand(patterns: list[str]) -> list[Path]:
    paths: list[Path] = []
    for pattern in patterns:
        matches = sorted(glob.glob(pattern, recursive=True))
        paths += [Path(m) for m in matches] if matches else [Path(pattern)]
    return paths


def settings_from(args: argparse.Namespace, out: Path) -> FragFinalSettings:
    width, height = (int(v) for v in args.size.lower().split("x"))
    fmt, depth = args.format, 8
    if fmt == "png16":
        fmt, depth = "png", 16
    if not fmt:
        fmt = {".exr": "exr", ".jpg": "jpeg", ".jpeg": "jpeg", ".tif": "tiff", ".tiff": "tiff", ".webp": "webp", ".bmp": "bmp"}.get(out.suffix.lower(), "png")
    if fmt == "exr":
        depth = 32
    settings = FragFinalSettings(tile_width=width, tile_height=height, tiles=args.tiles, padding=args.padding, subframes=args.subframes,
                                 output_path=str(out), output_format=fmt, depth=depth, depth_to_alpha=args.depth_alpha,
                                 video=bool(args.video), video_format=args.video or "mp4")
    if args.frames:
        first, last = (int(v) for v in args.frames.split("-"))
        settings = settings.with_(animation=True, start_frame=first, end_frame=last)
    settings = settings.with_(stereo=args.stereo, eye_separation=args.eye_separation, panorama=args.panorama)
    if args.region:
        settings = settings.with_(region=tuple(float(v) for v in args.region.split(",")))
    if args.tile_range or args.assemble or args.resume:
        tile_dir = args.tile_dir or f"{out}.tiles"
        if args.assemble:
            settings = settings.with_(tile_range=(-1, -1), tile_dir=tile_dir)           # nothing drawn: every tile comes from the folder
        else:
            first, last = (int(v) for v in args.tile_range.split("-")) if args.tile_range else (0, settings.tile_count - 1)
            settings = settings.with_(tile_range=(first, last), tile_dir=tile_dir, resume=args.resume)
    return settings


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    paths = expand(args.fragments)
    include_paths = [Path(p) for p in args.include_path]
    engine = FragEngine()
    failures = 0
    try:
        if args.check:
            for path in paths:
                try:
                    diagnostics = batch.check(path, engine, include_paths)
                except batch.BatchError as exc:
                    diagnostics, message = [], str(exc)
                    failures += 1
                    print(f"FAIL {path}: {message}")
                    continue
                errors = [d for d in diagnostics if d.severity == "error"]
                failures += bool(errors)
                if not args.quiet or errors:
                    print(f"{'FAIL' if errors else 'ok  '} {path}" + (f": {errors[0].text()}" if errors else ""))
            return 1 if failures else 0
        if not args.out:
            print("--out is required unless --check is given", file=sys.stderr)
            return 2
        out = Path(args.out)
        for path in paths:
            started = time.perf_counter()
            try:
                if args.all_presets or args.keyframes:
                    settings = settings_from(args, out / f"{path.stem}.png" if not out.suffix else out)
                    written = batch.render_presets(path, settings, engine, out if not out.suffix else out.parent, include_paths, args.keyframes)
                else:
                    target = out / f"{path.stem}.png" if out.is_dir() or (not out.suffix and len(paths) > 1) else out
                    settings = settings_from(args, target)
                    clock = None
                    if args.fps or args.length:
                        clock = AnimationSettings(args.fps or 25, args.length or 10)
                    result = batch.render(path, settings, engine, args.preset, include_paths, animation=clock)
                    written = result.paths
                    if settings.animation and settings.video and written:
                        import subprocess
                        frames = settings.frames((clock or AnimationSettings()).frames)
                        subprocess.run(settings.ffmpeg_command((clock or AnimationSettings()).fps, (clock or AnimationSettings()).frames, frames[0]), check=False)
            except batch.BatchError as exc:
                failures += 1
                print(f"FAIL {path}: {exc}", file=sys.stderr)
                continue
            if not args.quiet:
                print(f"{path.name}: {len(written)} file(s) in {time.perf_counter() - started:.1f} s" + (f" → {written[0]}" if written else ""))
                for note in getattr(result, "notes", []) if not (args.all_presets or args.keyframes) else []:
                    print(f"  {note}")
        return 1 if failures else 0
    finally:
        engine.close()


if __name__ == "__main__":
    sys.exit(main())
