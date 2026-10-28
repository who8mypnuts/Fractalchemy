"""Scripting: a Python API over the flame model, the engine that runs scripts, and the documentation the
Script Editor's completion and help panels are built from.

    api.py         the objects and functions a script sees (`flame`, `transforms`, `camera`, `gradient`, `xaos`, …)
    runner.py      runs a script on a copy of the flame with a stoppable trace, reporting errors with line numbers
    docs.py        the reference database: every global and type member, with signatures and option lists
    completion.py  type-aware completion and context help for the editor (Qt-free)
    generate.py    Flame → Script: a script that rebuilds a flame
    templates.py   built-in templates (`builtin_templates/*.py`) and the user's own (`user_script_dir()/templates`)

Everything here is Qt-free so it can be tested headlessly; the windows live in `fractalchemy/ui`.
"""

from .api import ScriptContext, ScriptError, ScriptStopped
from .runner import ScriptResult, run_script

__all__ = ["ScriptContext", "ScriptError", "ScriptStopped", "ScriptResult", "run_script"]
