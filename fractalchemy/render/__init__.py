"""Rendering engines and the service that runs them off the GUI thread.

Two engines share the scene model in `fractalchemy.fractal`:

* the **preview** engine (`gpu_engine` via moderngl, falling back to `cpu_engine`)
  trades precision for immediate feedback — progressive passes, reduced resolution
  while interacting;
* the **final** renderer (`final_engine`, driven by `final_service.FinalRenderJob`) favours
  precision and output quality: tiles within a memory budget, oversampling with a choice of
  reconstruction filters, density estimation and denoisers, 8 / 16-bit output in many formats.

`RenderSettings` describes *how* to preview and `FinalRenderSettings` how to render for output;
the flame says *what*.
"""

from .settings import RenderSettings, RenderStats

__all__ = ["RenderSettings", "RenderStats"]
