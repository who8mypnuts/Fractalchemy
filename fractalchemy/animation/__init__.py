"""Animations: keyframed flames interpolated over time, the `.faanim` file, and the frame renderer.

    animation/model.py        Keyframe / Animation (fps, frames, interpolation, keyframes)
    animation/interpolate.py  aligning keyframe flames and interpolating any frame between them
    animation/format.py       the `.faanim` JSON file
    animation/render.py       AnimationRenderSettings, frame file names, the ffmpeg command
    animation/render_job.py   the Qt thread rendering every frame (and encoding the video)
"""

from .format import animation_from_text, animation_to_text, load_animation, save_animation
from .model import EASINGS, INTERPOLATIONS, Animation, Keyframe

__all__ = ["Animation", "Keyframe", "INTERPOLATIONS", "EASINGS", "load_animation", "save_animation", "animation_to_text",
           "animation_from_text"]
