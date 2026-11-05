"""What a hi-res / animation render of a fragment is asked to do — FragM's `OutputDialog` as a dataclass.

Tiles (`tiles × tiles` of `tile_width × tile_height`, a `padding` that enlarges each tile's view so edges overlap and
are cropped — the image is `tiles · tile / (1 + padding)` a side), `subframes` to accumulate per tile, an optional
animation (a frame range at the clock's fps), and the output: a file (or a numbered sequence), the image format and
depth, the settings embedded, *depth to alpha* for EXR, the fragment saved with its settings and includes beside
the image (FragM's `<name> Files` folder), unique file names. Persisted in QSettings and in the `.fafrag` metadata.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path

from .. import config

FRAME_DIGITS = 5
MAX_PLAIN_SIDE = config.FRAG_MAX_IMAGE_SIDE


@dataclass(frozen=True)
class FragFinalSettings:
    """One hi-res / animation render.

    Attributes:
        tile_width, tile_height: Each tile's buffer size.
        tiles: Tiles per side (`tiles²` in all).
        padding: Fraction of extra view per tile (0 = none); cropped away when assembling.
        subframes: Subframes accumulated per tile.
        animation: Render a frame range instead of one still.
        start_frame, end_frame: The inclusive frame range (animation).
        preview: Show the result in a dialog instead of writing it (stills only).
        output_path: The image file (a numbered sequence for animations).
        output_format: The image format key (`render.output.FORMATS`).
        depth: Bits per channel (8 / 16; 16 / 32 for EXR).
        embed_parameters: Write the settings text into the image.
        save_parameters: Write a `.fragparams` beside the image.
        save_fragment: Write the fragment with its settings into a `<name> Files` folder (FragM's autosave).
        include_files: Copy the included files into that folder too.
        unique_name: Add a time stamp to the file name.
        depth_to_alpha: EXR: the depth buffer as the `Z` channel (FragM's DepthToAlpha).
        save_incomplete: Keep what was rendered when stopped.
        video: Encode the frames into a video with ffmpeg afterwards (animations; FragM's video dialog).
        video_format: One of `animation.render.VIDEO_FORMATS`' keys.
        video_quality: CRF for the codecs that take one.
        keep_frames: Keep the frame images after the video was made.
        report: Write the render details beside the image (`fragments/report.py`).
        report_format: `md`, `txt` or `html`.
        region: A crop of the frame rendered at full resolution — `(x, y, w, h)` as fractions (y down); None = the frame.
        stereo: `none`, `anaglyph` (red / cyan) or `sbs` (side by side): two renders with the eye shifted, composited.
        eye_separation: The stereo eye distance as a fraction of the eye–target distance.
        panorama: 360° equirectangular (sets the fragment's `EquiRectangular`; a 2:1 frame).
        tile_range: Render only tiles `(first, last)` (inclusive, row-major indices); None = all. The command line's
            distributed rendering: each machine renders a range into `tile_dir`, `--assemble` joins them.
        tile_dir: Where rendered tiles are written / read as `.npy` (empty: tiles are not kept).
        resume: Skip tiles that already exist in `tile_dir`.
    """
    tile_width: int = 1920
    tile_height: int = 1080
    tiles: int = 1
    padding: float = 0.0
    subframes: int = 100
    animation: bool = False
    start_frame: int = 0
    end_frame: int = 0
    preview: bool = False
    output_path: str = ""
    output_format: str = "png"
    depth: int = 8
    embed_parameters: bool = True
    save_parameters: bool = False
    save_fragment: bool = False
    include_files: bool = False
    unique_name: bool = False
    depth_to_alpha: bool = False
    save_incomplete: bool = True
    video: bool = False
    video_format: str = "mp4"
    video_quality: int = 18
    keep_frames: bool = True
    report: bool = False
    report_format: str = "md"
    region: tuple | None = None
    stereo: str = "none"
    eye_separation: float = 0.03
    panorama: bool = False
    tile_range: tuple | None = None
    tile_dir: str = ""
    resume: bool = False

    # --- stereo / region / tiles -------------------------------------------------------------------------------------
    @property
    def eyes(self) -> int:
        """How many renders a frame takes (2 for stereo)."""
        return 2 if self.stereo in ("anaglyph", "sbs") else 1

    def tile_indices(self) -> list[int]:
        """The tiles this job draws (all, or the `tile_range`)."""
        if self.tile_range is None:
            return list(range(self.tile_count))
        first, last = int(self.tile_range[0]), int(self.tile_range[1])
        return [i for i in range(self.tile_count) if first <= i <= last]

    def output_size(self) -> tuple[int, int]:
        """The written image's size: the frame, doubled in width for side-by-side stereo."""
        width, height = self.image_size
        return (width * 2 if self.stereo == "sbs" else width), height

    # --- geometry ---------------------------------------------------------------------------------------------------
    @property
    def inner_tile(self) -> tuple[int, int]:
        """The part of a tile that lands in the image once the padding is cropped."""
        return max(1, int(round(self.tile_width / (1.0 + self.padding)))), max(1, int(round(self.tile_height / (1.0 + self.padding))))

    @property
    def image_size(self) -> tuple[int, int]:
        """The assembled image's size (FragM's `(tiles · w) / (1 + padding)`)."""
        w, h = self.inner_tile
        return w * self.tiles, h * self.tiles

    @property
    def tile_count(self) -> int:
        return self.tiles * self.tiles

    def frames(self, total_frames: int) -> list[int]:
        """The frames to render: one (the still) or the inclusive range clipped to the animation."""
        if not self.animation:
            return [self.start_frame]
        last = min(self.end_frame, total_frames)
        first = max(0, min(self.start_frame, last))
        return list(range(first, last + 1))

    def total_steps(self, total_frames: int) -> int:
        """Subframe draws over the whole job (the progress bar's unit)."""
        return len(self.frames(total_frames)) * len(self.tile_indices()) * max(1, self.subframes) * self.eyes

    # --- problems -----------------------------------------------------------------------------------------------------
    def problems(self) -> list[str]:
        """Why the render cannot start (empty = fine)."""
        issues = []
        width, height = self.image_size
        if self.output_format != "exr" and max(width, height) > MAX_PLAIN_SIDE:
            issues.append(f"{width} × {height} is too large — must be less than {MAX_PLAIN_SIDE + 1} a side (OpenEXR output is exempt)")
        if max(self.tile_width, self.tile_height) > config.FRAG_MAX_TILE_SIDE:
            tiles = self.suggested_tiles()
            inner_w, inner_h = self.tile_width * self.tiles // tiles, self.tile_height * self.tiles // tiles
            issues.append(f"a tile may be at most {config.FRAG_MAX_TILE_SIDE} pixels a side (the GPU renders one tile at a time): "
                          f"{self.tile_width} × {self.tile_height} needs {tiles} tiles per side — tiles of {inner_w} × {inner_h} give the same "
                          f"{width} × {height} image")
        if not self.preview and not self.output_path.strip():
            issues.append("choose an output file")
        if self.animation and self.end_frame < self.start_frame:
            issues.append("the end frame lies before the start frame")
        if self.subframes < 1:
            issues.append("at least one subframe")
        if self.stereo not in ("none", "anaglyph", "sbs"):
            issues.append(f"unknown stereo mode {self.stereo!r}")
        if self.region is not None and (len(self.region) != 4 or min(self.region[2:]) <= 0 or min(self.region[:2]) < 0
                                        or self.region[0] + self.region[2] > 1.0001 or self.region[1] + self.region[3] > 1.0001):
            issues.append("the region must lie inside the frame")
        if self.tile_range is not None and not self.tile_indices() and not self.tile_dir:
            issues.append(f"the tile range {self.tile_range} selects no tile of {self.tile_count}")
        return issues

    def suggested_tiles(self) -> int:
        """The tiles per side that bring the tile under the limit while keeping the image size (what *Fix* applies)."""
        side = max(self.tile_width, self.tile_height) * self.tiles
        return max(1, -(-side // config.FRAG_MAX_TILE_SIDE))

    def retiled(self, tiles: int) -> "FragFinalSettings":
        """The same image split into `tiles` per side."""
        width, height = self.image_size
        tiles = max(1, int(tiles))
        return self.with_(tiles=tiles, tile_width=max(16, int(round(width / tiles * (1.0 + self.padding)))),
                          tile_height=max(16, int(round(height / tiles * (1.0 + self.padding)))))

    # --- names -----------------------------------------------------------------------------------------------------------
    def frame_path(self, frame: int, total_frames: int) -> Path:
        """Where frame `frame` goes: `name.00012.png` for animations (FragM's padding grows past 99999 frames)."""
        path = Path(self.output_path)
        if not self.animation:
            return path
        digits = max(FRAME_DIGITS, len(str(total_frames)))
        return path.with_name(f"{path.stem}.{frame:0{digits}d}{path.suffix}")

    def unique(self, path: Path) -> Path:
        """A time-stamped variant of `path` (FragM's *unique ID*)."""
        return path.with_name(f"{path.stem}-{datetime.now().strftime('%Y%m%d-%H%M%S')}{path.suffix}")

    def frame_pattern(self, total_frames: int) -> str:
        """The printf pattern ffmpeg reads the frames with (`name.%05d.png`)."""
        path = Path(self.output_path)
        digits = max(FRAME_DIGITS, len(str(total_frames)))
        return str(path.with_name(f"{path.stem}.%0{digits}d{path.suffix}"))

    def video_path(self) -> Path:
        from ..animation.render import video_format
        return Path(self.output_path).with_suffix(video_format(self.video_format).suffix)

    def ffmpeg_command(self, fps: int, total_frames: int, first_frame: int, executable: str | None = None) -> list[str]:
        """The ffmpeg command encoding the rendered frames into `video_path()` (the host's codec table)."""
        from ..animation.render import ffmpeg_path, video_format
        fmt = video_format(self.video_format)
        cmd = [executable or ffmpeg_path() or "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-stats", "-framerate", str(max(1, fps)),
               "-start_number", str(first_frame), "-i", self.frame_pattern(total_frames)]
        if fmt.key == "gif":
            cmd += ["-vf", "split[s0][s1];[s0]palettegen=stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5", "-loop", "0"]
        else:
            cmd += ["-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2"] + list(fmt.codec)
            if fmt.has_crf:
                cmd += ["-crf", str(self.video_quality)]
        cmd.append(str(self.video_path()))
        return cmd

    def video_problems(self) -> list[str]:
        """Why a video cannot be made from these settings."""
        from ..animation.render import FFMPEG_READABLE, ffmpeg_path
        issues = []
        if ffmpeg_path() is None:
            issues.append("ffmpeg was not found on the PATH")
        if self.output_format not in FFMPEG_READABLE:
            issues.append(f"ffmpeg cannot read {self.output_format} frames (use PNG, JPEG, TIFF, WebP or BMP)")
        if self.unique_name:
            issues.append("unique file names break the frame sequence")
        return issues

    def files_folder(self) -> Path:
        """FragM's `<name> Files` folder beside the image, for the saved fragment and its includes."""
        path = Path(self.output_path)
        return path.parent / f"{path.stem} Files"

    def describe_plan(self, total_frames: int) -> str:
        width, height = self.image_size
        frames = len(self.frames(total_frames))
        tiles = f"{self.tiles} × {self.tiles} tiles of {self.tile_width} × {self.tile_height}" if self.tiles > 1 else f"one tile of {self.tile_width} × {self.tile_height}"
        pad = f", padding {self.padding:g}" if self.padding else ""
        extras = ""
        if self.region is not None:
            extras += f" · region {self.region[2] * 100:.0f}% × {self.region[3] * 100:.0f}% of the frame"
        if self.stereo != "none":
            extras += f" · stereo {self.stereo} (two eyes, separation {self.eye_separation:g})"
        if self.panorama:
            extras += " · 360° equirectangular"
        if self.tile_range is not None:
            extras += f" · tiles {self.tile_range[0]}–{self.tile_range[1]} only" if self.tile_indices() else " · assembling saved tiles"
        return (f"{width} × {height} pixels · {tiles}{pad} · {self.subframes} subframes" + (f" · {frames} frames" if self.animation else "")
                + extras + f" · {self.total_steps(total_frames):,} draws")

    # --- persistence ---------------------------------------------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, data: dict | None) -> "FragFinalSettings":
        data = data or {}
        fields = {k: data[k] for k in cls.__dataclass_fields__ if k in data}
        for key in ("region", "tile_range"):
            if fields.get(key) is not None:
                fields[key] = tuple(fields[key]) if isinstance(fields[key], (list, tuple)) and fields[key] else None
        return replace(cls(), **fields)

    def with_(self, **fields) -> "FragFinalSettings":
        return replace(self, **fields)


def safe_stem(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]+', "_", name).strip() or "fragment"


__all__ = ["FragFinalSettings", "safe_stem", "FRAME_DIGITS"]
