"""The animation model: keyframes on a timeline of frames. Pure Python, no Qt.

An `Animation` is a list of `Keyframe`s — each a complete `Flame` pinned to a frame number — plus
the frame rate, the total length in frames and how the frames between keyframes are made:

* `interpolation`: `linear` (straight blend of every number between neighbouring keyframes),
  `smooth` (a Catmull-Rom spline through the keyframes, so motion flows through them instead of
  turning corners), `hold` (each keyframe stays until the next: a slideshow).
* `easing`: `none`, `ease-in`, `ease-out`, `ease-in-out` — how the time within a segment is warped.
* `loop`: whether the animation wraps (playback loops, and *smooth* treats the ends as neighbours).

`flame_at(frame)` is the interpolated flame (see `interpolate.py`); `to_dict` / `from_dict` are the
`.faanim` content.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..fractal.scene import Flame

INTERPOLATIONS = (("linear", "Linear"), ("smooth", "Smooth (spline through the keyframes)"), ("hold", "Hold (no blending)"))
EASINGS = (("none", "None"), ("ease-in", "Ease in"), ("ease-out", "Ease out"), ("ease-in-out", "Ease in and out"))
DEFAULT_FPS = 30
DEFAULT_FRAMES = 150
MAX_FPS = 240
MAX_FRAMES = 1_000_000


@dataclass
class Keyframe:
    """A flame pinned to a frame.

    Attributes:
        frame: Frame number (0-based) where the animation shows exactly this flame.
        flame: The flame (the keyframe owns its copy).
        name: Optional label (defaults to the flame's name when captured).
    """
    frame: int
    flame: Flame
    name: str = ""

    @property
    def label(self) -> str:
        """The name to show: the keyframe's own, else its flame's."""
        return self.name or self.flame.name

    def copy(self) -> "Keyframe":
        """An independent copy (the flame duplicated)."""
        return Keyframe(self.frame, self.flame.copy(), self.name)

    def to_dict(self) -> dict:
        """Plain data for the `.faanim` file."""
        return {"frame": self.frame, "name": self.name, "flame": self.flame.to_dict()}

    @classmethod
    def from_dict(cls, data: dict) -> "Keyframe":
        """Inverse of `to_dict`; a missing or malformed flame becomes the default flame."""
        flame = data.get("flame")
        return cls(max(0, int(data.get("frame", 0))), Flame.from_dict(flame if isinstance(flame, dict) else {}), str(data.get("name", "")))


@dataclass
class Animation:
    """Keyframes on a timeline (see the module docstring).

    Attributes:
        name: The animation's name (the default base name of rendered frames).
        fps: Frames per second.
        total_frames: Length of the animation in frames (frames beyond the last keyframe hold it).
        interpolation: One of `INTERPOLATIONS`' keys.
        easing: One of `EASINGS`' keys.
        loop: Whether playback wraps around.
        keyframes: Sorted by frame; at most one per frame.
        render: The last render settings used (plain data, kept with the file so a render can be repeated).
    """
    name: str = "animation"
    fps: int = DEFAULT_FPS
    total_frames: int = DEFAULT_FRAMES
    interpolation: str = "linear"
    easing: str = "none"
    loop: bool = False
    keyframes: list[Keyframe] = field(default_factory=list)
    render: dict = field(default_factory=dict)

    # --- facts ------------------------------------------------------------------------------------------------
    @property
    def duration(self) -> float:
        """Length in seconds."""
        return self.total_frames / max(1, self.fps)

    @property
    def last_frame(self) -> int:
        """The number of the last frame."""
        return max(0, self.total_frames - 1)

    def frame_to_seconds(self, frame: int) -> float:
        """The time of `frame` in seconds."""
        return frame / max(1, self.fps)

    def keyframe_at(self, frame: int) -> Keyframe | None:
        """The keyframe pinned exactly at `frame`, if any."""
        return next((k for k in self.keyframes if k.frame == frame), None)

    def index_at(self, frame: int) -> int | None:
        """The position in `keyframes` of the keyframe at `frame`, if any."""
        return next((i for i, k in enumerate(self.keyframes) if k.frame == frame), None)

    def segment(self, frame: int) -> tuple[Keyframe | None, Keyframe | None]:
        """(previous-or-equal keyframe, next keyframe) around `frame` (either may be None)."""
        before = next((k for k in reversed(self.keyframes) if k.frame <= frame), None)
        after = next((k for k in self.keyframes if k.frame > frame), None)
        return before, after

    def next_keyframe(self, frame: int) -> Keyframe | None:
        """The first keyframe after `frame`, if any."""
        return next((k for k in self.keyframes if k.frame > frame), None)

    def previous_keyframe(self, frame: int) -> Keyframe | None:
        """The last keyframe before `frame`, if any."""
        return next((k for k in reversed(self.keyframes) if k.frame < frame), None)

    def is_valid(self) -> bool:
        """True if there is something to show (at least one keyframe)."""
        return bool(self.keyframes)

    # --- editing ----------------------------------------------------------------------------------------------
    def set_keyframe(self, frame: int, flame: Flame, name: str = "") -> Keyframe:
        """Pin `flame` at `frame` (replacing a keyframe already there); returns the keyframe. Extends the length."""
        frame = max(0, int(frame))
        existing = self.keyframe_at(frame)
        if existing is not None:
            existing.flame = flame.copy()
            if name:
                existing.name = name
            keyframe = existing
        else:
            keyframe = Keyframe(frame, flame.copy(), name)
            self.keyframes.append(keyframe)
            self.keyframes.sort(key=lambda k: k.frame)
        if frame >= self.total_frames:
            self.total_frames = frame + 1
        return keyframe

    def remove_keyframe(self, keyframe: Keyframe) -> None:
        """Drop a keyframe (no-op if it is not in the animation)."""
        if keyframe in self.keyframes:
            self.keyframes.remove(keyframe)

    def move_keyframe(self, keyframe: Keyframe, frame: int) -> int:
        """Move a keyframe to another frame, staying between its neighbours; returns the frame it got."""
        index = self.keyframes.index(keyframe)
        lo = self.keyframes[index - 1].frame + 1 if index > 0 else 0
        hi = self.keyframes[index + 1].frame - 1 if index + 1 < len(self.keyframes) else MAX_FRAMES
        keyframe.frame = max(lo, min(hi, int(frame)))
        if keyframe.frame >= self.total_frames:
            self.total_frames = keyframe.frame + 1
        return keyframe.frame

    def set_total_frames(self, frames: int) -> None:
        """Change the length; keyframes beyond the end are kept (the length is never shorter than the last one + 1)."""
        last = self.keyframes[-1].frame + 1 if self.keyframes else 1
        self.total_frames = max(last, min(MAX_FRAMES, int(frames)))

    def flame_at(self, frame: int) -> Flame | None:
        """The interpolated flame at `frame` (None without keyframes)."""
        from .interpolate import flame_at
        return flame_at(self, frame)

    def copy(self) -> "Animation":
        """An independent copy (keyframes and their flames duplicated)."""
        return Animation(self.name, self.fps, self.total_frames, self.interpolation, self.easing, self.loop,
                         [k.copy() for k in self.keyframes], dict(self.render))

    # --- serialisation ----------------------------------------------------------------------------------------
    def to_dict(self) -> dict:
        """Plain data for the `.faanim` file (inverse of `from_dict`)."""
        return {"name": self.name, "fps": self.fps, "total_frames": self.total_frames, "interpolation": self.interpolation,
                "easing": self.easing, "loop": self.loop, "keyframes": [k.to_dict() for k in self.keyframes],
                "render": dict(self.render)}

    @classmethod
    def from_dict(cls, data: dict) -> "Animation":
        """Inverse of `to_dict`; unknown modes fall back to the defaults, keyframes are sorted and de-duplicated by frame."""
        keyframes: list[Keyframe] = []
        for entry in data.get("keyframes", []):
            if isinstance(entry, dict):
                keyframe = Keyframe.from_dict(entry)
                keyframes = [k for k in keyframes if k.frame != keyframe.frame] + [keyframe]
        keyframes.sort(key=lambda k: k.frame)
        interpolation = data.get("interpolation", "linear")
        easing = data.get("easing", "none")
        anim = cls(
            name=str(data.get("name", "animation")),
            fps=max(1, min(MAX_FPS, int(data.get("fps", DEFAULT_FPS)))),
            total_frames=max(1, min(MAX_FRAMES, int(data.get("total_frames", DEFAULT_FRAMES)))),
            interpolation=interpolation if interpolation in dict(INTERPOLATIONS) else "linear",
            easing=easing if easing in dict(EASINGS) else "none",
            loop=bool(data.get("loop", False)),
            keyframes=keyframes,
            render=dict(data.get("render", {}) or {}),
        )
        anim.set_total_frames(anim.total_frames)
        return anim


__all__ = ["Animation", "Keyframe", "INTERPOLATIONS", "EASINGS", "DEFAULT_FPS", "DEFAULT_FRAMES", "MAX_FPS", "MAX_FRAMES"]
