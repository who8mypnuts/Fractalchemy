"""What an animation render is asked to do, and the ffmpeg command that turns the frames into a video.

`AnimationRenderSettings` wraps a `FinalRenderSettings` (size, quality, filter, denoiser, engine,
image format and options — everything the Render Image window offers) with what a batch needs
instead of one file name: an output folder, a base name (frames are `base_0001.png`, …), the frame
range and step, and the optional video. Qt-free; the Render Animation window persists it through
`to_dict` / `from_dict`, and the `.faanim` file keeps the last one used.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from ..render.final_settings import FinalRenderSettings
from ..render.output import output_format, size_problem



@dataclass(frozen=True)
class VideoFormat:
    """One container / codec choice for ffmpeg.

    Attributes:
        key: Identifier stored in settings.
        label: Name shown in the UI.
        suffix: The video file's extension.
        codec: ffmpeg arguments choosing the codec and pixel format.
        has_crf: Whether the codec takes a constant-rate-factor quality.
    """
    key: str
    label: str
    suffix: str
    codec: tuple[str, ...] = ()
    has_crf: bool = False


VIDEO_FORMATS = (
    VideoFormat("mp4", "MP4 — H.264 (plays everywhere)", ".mp4", ("-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart"), True),
    VideoFormat("mp4-hevc", "MP4 — H.265 / HEVC (smaller)", ".mp4",
                ("-c:v", "libx265", "-pix_fmt", "yuv420p", "-tag:v", "hvc1", "-movflags", "+faststart"), True),
    VideoFormat("webm", "WebM — VP9", ".webm", ("-c:v", "libvpx-vp9", "-pix_fmt", "yuv420p", "-b:v", "0"), True),
    VideoFormat("mov", "QuickTime — ProRes 422 (editing)", ".mov", ("-c:v", "prores_ks", "-profile:v", "3", "-pix_fmt", "yuv422p10le")),
    VideoFormat("gif", "GIF (animated)", ".gif"),
)
VIDEO_FORMAT_BY_KEY = {v.key: v for v in VIDEO_FORMATS}


def video_format(key: str) -> VideoFormat:
    """The video format for a settings key (unknown keys mean MP4 / H.264)."""
    return VIDEO_FORMAT_BY_KEY.get(key, VIDEO_FORMATS[0])
FFMPEG_READABLE = ("png", "jpeg", "tiff", "webp", "bmp")   # frame formats ffmpeg's image2 demuxer reads
DEFAULT_CRF = 18
FRAME_DIGITS = 4
DEFAULT_FRAME_QUALITY = 500.0    # samples per pixel of a frame: a quarter of a single image's default (there are many frames)


@dataclass(frozen=True)
class AnimationRenderSettings:
    """A complete description of one animation render (see the module docstring).

    Attributes:
        image: Size, quality, engine, image format and options (its `output_path` is ignored).
        folder: Where the frames (and the video) go.
        base_name: Frame file stem; the frame number and the format's suffix are appended.
        start_frame, end_frame: Inclusive frame range (`end_frame` −1 = the animation's last frame).
        step: Render every `step`-th frame.
        skip_existing: Leave frames whose file already exists alone (resume a stopped render).
        video: Run ffmpeg on the frames afterwards.
        video_format: One of `VIDEO_FORMATS`' keys.
        video_quality: CRF for H.264 / H.265 / VP9 (lower is better; 18 is visually lossless for H.264).
        video_name: Video file stem (empty = `base_name`).
        keep_frames: Keep the frame images after the video was made.
    """
    image: FinalRenderSettings = field(default_factory=lambda: FinalRenderSettings(quality=DEFAULT_FRAME_QUALITY))
    folder: str = ""
    base_name: str = "frame"
    start_frame: int = 0
    end_frame: int = -1
    step: int = 1
    skip_existing: bool = False
    video: bool = False
    video_format: str = "mp4"
    video_quality: int = DEFAULT_CRF
    video_name: str = ""
    keep_frames: bool = True

    # --- derived ------------------------------------------------------------------------------------------------
    def frames(self, total_frames: int) -> list[int]:
        """The frame numbers to render."""
        last = total_frames - 1 if self.end_frame < 0 else min(self.end_frame, total_frames - 1)
        first = max(0, min(self.start_frame, last))
        return list(range(first, last + 1, max(1, self.step)))

    @property
    def extension(self) -> str:
        """The frames' file suffix (with the dot)."""
        return output_format(self.image.output_format).extension

    def digits(self, total_frames: int) -> int:
        """How many digits the frame number is padded to (at least `FRAME_DIGITS`)."""
        return max(FRAME_DIGITS, len(str(max(0, total_frames - 1))))

    def frame_path(self, frame: int, total_frames: int) -> Path:
        """Where frame `frame` is written."""
        return Path(self.folder) / f"{safe_stem(self.base_name)}_{frame:0{self.digits(total_frames)}d}{self.extension}"

    def frame_pattern(self, total_frames: int) -> str:
        """The printf-style pattern ffmpeg reads the frames with."""
        return str(Path(self.folder) / f"{safe_stem(self.base_name)}_%0{self.digits(total_frames)}d{self.extension}")

    def video_path(self) -> Path:
        """Where the video is written."""
        return Path(self.folder) / (safe_stem(self.video_name or self.base_name) + video_format(self.video_format).suffix)

    def with_image(self, image: FinalRenderSettings) -> "AnimationRenderSettings":
        """The same batch with other image settings (their `output_path` is dropped)."""
        return replace(self, image=replace(image, output_path=""))

    def problems(self, total_frames: int) -> list[str]:
        """Reasons this render cannot start (empty when it can)."""
        issues = [p for p in self.image.problems() if not p.startswith("Choose an output file")]
        fmt = output_format(self.image.output_format)
        size_issue = size_problem(fmt, self.image.width, self.image.height)
        if size_issue:
            issues.append(size_issue)
        if not self.folder.strip():
            issues.append("Choose an output folder")
        if not safe_stem(self.base_name):
            issues.append("Give the frames a base name")
        if not self.frames(total_frames):
            issues.append("The frame range is empty")
        if self.video:
            issues += video_problems(self)
        return issues

    # --- persistence --------------------------------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        """Plain data for persistence (inverse of `from_dict`)."""
        data = {k: v for k, v in self.__dict__.items() if k != "image"}
        data["image"] = self.image.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnimationRenderSettings":
        """Inverse of `to_dict`; unknown keys are ignored, bad values fall back to the defaults."""
        defaults = cls()
        values: dict[str, Any] = {}
        for name, default in defaults.__dict__.items():
            if name == "image" or name not in data:
                continue
            try:
                values[name] = bool(data[name]) if isinstance(default, bool) else type(default)(data[name])
            except (TypeError, ValueError):
                pass
        image = data.get("image")
        if isinstance(image, dict):
            values["image"] = FinalRenderSettings.from_dict(image)
        settings = cls(**values)
        if settings.video_format not in VIDEO_FORMAT_BY_KEY:
            settings = replace(settings, video_format="mp4")
        return replace(settings, step=max(1, settings.step), video_quality=max(0, min(63, settings.video_quality)))


def safe_stem(name: str) -> str:
    """A file stem without path separators or characters file systems refuse."""
    return re.sub(r'[\\/:*?"<>|]+', "_", name).strip().strip(".")


# --- ffmpeg --------------------------------------------------------------------------------------------------------
def ffmpeg_path() -> str | None:
    """The ffmpeg executable on this system, or None."""
    return shutil.which("ffmpeg")


def video_problems(settings: AnimationRenderSettings) -> list[str]:
    """Why the video cannot be made (empty when it can)."""
    issues = []
    if ffmpeg_path() is None:
        issues.append("ffmpeg was not found on this system (install it, or turn the video off)")
    if settings.image.output_format not in FFMPEG_READABLE:
        readable = ", ".join(output_format(k).label for k in FFMPEG_READABLE)
        issues.append(f"ffmpeg cannot read {output_format(settings.image.output_format).label} frames; use {readable}")
    if settings.step != 1:
        issues.append("The video needs every frame (step 1)")
    return issues


def ffmpeg_command(settings: AnimationRenderSettings, fps: int, total_frames: int, first_frame: int,
                   executable: str | None = None) -> list[str]:
    """The ffmpeg command line encoding the rendered frames into `settings.video_path()`."""
    fmt = video_format(settings.video_format)
    cmd = [executable or ffmpeg_path() or "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-stats",
           "-framerate", str(max(1, fps)), "-start_number", str(first_frame), "-i", settings.frame_pattern(total_frames)]
    if fmt.key == "gif":
        # a palette pass makes a far better GIF than the default 256-colour dither
        cmd += ["-vf", "split[s0][s1];[s0]palettegen=stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5",
                "-loop", "0"]
    else:
        cmd += ["-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2"]    # yuv420p needs even dimensions
        cmd += list(fmt.codec)
        if fmt.has_crf:
            cmd += ["-crf", str(settings.video_quality)]
    cmd.append(str(settings.video_path()))
    return cmd


__all__ = ["AnimationRenderSettings", "VideoFormat", "VIDEO_FORMATS", "VIDEO_FORMAT_BY_KEY", "video_format", "FFMPEG_READABLE",
           "DEFAULT_CRF", "DEFAULT_FRAME_QUALITY", "safe_stem", "ffmpeg_path", "ffmpeg_command", "video_problems"]
