"""Fragments: Fragmentarium-style GLSL fragment shaders as fractals.

The Qt-free core of the Fragments window: the `.frag` language (`preprocessor`, `parameters`, `state`, `files`),
the GLSL compatibility layer that lets the legacy fragment corpus run on core-profile contexts (`glsl_compat`),
the camera maths (`camera`), the bundled library (`examples`) and the templates. The moderngl side lives in
`fragments.gl`, the window in `ui.fragments`. See `plans/fragments-plan.md` and `docs/fragments.md`.
"""
