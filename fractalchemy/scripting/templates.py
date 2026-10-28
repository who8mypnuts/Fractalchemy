"""Script templates: the built-in ones (files in `scripting/builtin_templates/`) and the user's own, saved as `.py` files in
`user_script_dir() / "templates"`. A template's name, category and description come from `# @name`,
`# @category` and `# @description` comment lines at the top of the file (see `parse_metadata`)."""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

BUILTIN_DIR = Path(__file__).resolve().parent / "builtin_templates"
USER_CATEGORY = "My templates"
META_LINE = re.compile(r"^\s*#\s*@(\w+)\s*:?\s*(.*?)\s*$")
CATEGORY_ORDER = ("Transforms", "Colours", "Xaos", "Camera", "Flame")


@dataclass
class Template:
    """One script template.

    Attributes:
        name: Shown in the list (from `# @name`, else the file name).
        category: Group in the list (`# @category`; user templates are always 'My templates').
        description: One line (`# @description`).
        code: The script.
        path: Its file (None for a template that has not been saved).
        builtin: Shipped with Fractalchemy (read-only).
    """
    name: str
    category: str
    description: str
    code: str
    path: Path | None = None
    builtin: bool = False
    meta: dict[str, str] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return str(self.path) if self.path else self.name


def parse_metadata(code: str) -> dict[str, str]:
    """`# @key value` lines at the top of a script (stops at the first line that is not a comment or blank)."""
    meta: dict[str, str] = {}
    for line in code.split("\n"):
        if not line.strip():
            continue
        if not line.lstrip().startswith("#"):
            break
        m = META_LINE.match(line)
        if m:
            meta[m.group(1).lower()] = m.group(2)
    return meta


def strip_metadata(code: str) -> str:
    """The script without its `# @key` header lines (for inserting a template into another script)."""
    lines = code.split("\n")
    kept, header = [], True
    for line in lines:
        if header and (META_LINE.match(line) or not line.strip()):
            continue
        header = False
        kept.append(line)
    return "\n".join(kept)


def with_metadata(code: str, **values: str) -> str:
    """`code` with `# @key value` header lines set (existing ones replaced, new ones added at the top)."""
    lines = code.split("\n")
    present: dict[str, int] = {}
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        if not line.lstrip().startswith("#"):
            break
        m = META_LINE.match(line)
        if m:
            present[m.group(1).lower()] = i
    for key, value in values.items():
        if not value:
            continue
        text = f"# @{key} {value}"
        if key in present:
            lines[present[key]] = text
        else:
            insert_at = max(present.values()) + 1 if present else 0
            lines.insert(insert_at, text)
            present[key] = insert_at
            for k, v in list(present.items()):
                if k != key and v >= insert_at:
                    present[k] = v + 1
    return "\n".join(lines)


def template_from_file(path: Path, builtin: bool = False) -> Template:
    code = path.read_text(encoding="utf-8")
    meta = parse_metadata(code)
    name = meta.get("name") or path.stem.replace("_", " ").capitalize()
    category = USER_CATEGORY if not builtin else (meta.get("category") or "Other")
    return Template(name, category, meta.get("description", ""), code, path, builtin, meta)


def user_script_dir() -> Path:
    """The per-user folder for scripts (templates live in its `templates` subfolder); created on demand by the UI."""
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "Fractalchemy" / "scripts"


def builtin_templates() -> list[Template]:
    """The shipped templates, in category order then by name."""
    templates = [template_from_file(p, builtin=True) for p in sorted(BUILTIN_DIR.glob("*.py")) if p.name != "__init__.py"]
    return sort_templates(templates)


def user_templates(folder: Path | None = None) -> list[Template]:
    """The user's templates (`.py` files in `folder`, default `user_script_dir()/templates`); unreadable files are skipped."""
    folder = folder or user_script_dir() / "templates"
    if not folder.is_dir():
        return []
    templates = []
    for path in sorted(folder.glob("*.py")):
        try:
            templates.append(template_from_file(path))
        except (OSError, UnicodeDecodeError):
            continue
    return sorted(templates, key=lambda t: t.name.lower())


def all_templates(user_folder: Path | None = None) -> list[Template]:
    return user_templates(user_folder) + builtin_templates()


def sort_templates(templates: list[Template]) -> list[Template]:
    def key(t: Template):
        order = CATEGORY_ORDER.index(t.category) if t.category in CATEGORY_ORDER else len(CATEGORY_ORDER)
        return (order, t.category.lower(), t.name.lower())
    return sorted(templates, key=key)


def safe_file_name(name: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip()).strip("_").lower() or "template"
    return stem + ".py"


def save_user_template(name: str, code: str, description: str = "", folder: Path | None = None, replace: Path | None = None) -> Template:
    """Write a user template (name / description stamped into the header); `replace` overwrites that file."""
    folder = folder or user_script_dir() / "templates"
    folder.mkdir(parents=True, exist_ok=True)
    code = with_metadata(code, name=name, description=description)
    path = replace if replace is not None else folder / safe_file_name(name)
    if replace is None:
        n = 2
        while path.exists():
            path = folder / f"{safe_file_name(name)[:-3]}_{n}.py"
            n += 1
    path.write_text(code, encoding="utf-8")
    return template_from_file(path)


def delete_user_template(template: Template) -> None:
    if template.builtin or template.path is None:
        raise ValueError("built-in templates cannot be deleted")
    template.path.unlink(missing_ok=True)


def rename_user_template(template: Template, name: str) -> Template:
    """Change the `# @name` of a user template (the file keeps its name)."""
    if template.builtin or template.path is None:
        raise ValueError("built-in templates cannot be renamed")
    template.path.write_text(with_metadata(template.code, name=name), encoding="utf-8")
    return template_from_file(template.path)


__all__ = ["Template", "parse_metadata", "strip_metadata", "with_metadata", "builtin_templates", "user_templates", "all_templates",
           "save_user_template", "delete_user_template", "rename_user_template", "user_script_dir", "USER_CATEGORY", "BUILTIN_DIR"]
