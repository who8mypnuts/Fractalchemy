"""Rendering engines and the service that runs them off the GUI thread.

Two engines share the scene model in `fractalchemy.fractal`:

* the **preview** engine (`gpu_engine` via moderngl, falling back to `cpu_engine`)
  trades precision for immediate feedback — progressive passes, reduced resolution
  while interacting;
* the **final** engine (to come) will favour precision and output quality.

`RenderSettings` describes *how* to render (size, passes, quality); the flame says *what*.
"""

from .settings import RenderSettings, RenderStats

__all__ = ["RenderSettings", "RenderStats"]
