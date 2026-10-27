"""Report sections about the fractal: summary, camera, colouring, palette, transforms, variations, xaos.

`FlameFacts` digests the flame once (every transform including the final one, every non-zero
variation term, xaos use) and the section builders read from it, so the summary counts and the
detailed tables can never disagree.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from ...fractal.scene import Flame, XForm
from ...fractal.variations import REGISTRY, canonical_name
from ...model.color import hue, luminance, rgb_to_hex, rgb_to_hsl
from ..final_settings import FinalRenderSettings
from .model import Section, Table

HUE_NAMES = ("red", "orange", "yellow", "chartreuse", "green", "spring green", "cyan", "azure", "blue", "violet",
             "magenta", "rose")
GREY_SATURATION = 0.15


@dataclass(frozen=True)
class FlameFacts:
    """The flame digested for the report.

    Attributes:
        flame: The flame.
        labelled: (label, xform) for every transform: "1", "2", … then "final".
        terms: (label, canonical variation name, weight) for every non-zero variation term.
    """
    flame: Flame
    labelled: tuple[tuple[str, XForm], ...]
    terms: tuple[tuple[str, str, float], ...]

    @classmethod
    def of(cls, flame: Flame) -> "FlameFacts":
        """Digest `flame`."""
        labelled = [(str(i), x) for i, x in enumerate(flame.xforms, start=1)]
        if flame.final is not None:
            labelled.append(("final", flame.final))
        terms = [(label, canonical_name(n), w) for label, x in labelled for n, w in x.variations.items() if w != 0]
        return cls(flame, tuple(labelled), tuple(terms))

    @property
    def names(self) -> set[str]:
        """Distinct variation names in use."""
        return {name for _label, name, _w in self.terms}

    def usage(self) -> dict[str, list[tuple[str, float]]]:
        """Variation name → [(transform label, weight)], most-used first."""
        used: dict[str, list[tuple[str, float]]] = {}
        for label, name, weight in self.terms:
            used.setdefault(name, []).append((label, weight))
        return dict(sorted(used.items(), key=lambda kv: (-len(kv[1]), kv[0])))

    @property
    def xaos_in_use(self) -> bool:
        """True if any transform has a xaos row that is not all ones."""
        return any(x.chaos is not None and any(c != 1 for c in x.chaos) for x in self.flame.xforms)


def fractal_section(facts: FlameFacts, source: str) -> Section:
    """Counts that summarise the fractal."""
    flame = facts.flame
    xforms = flame.xforms
    all_xforms = [x for _label, x in facts.labelled]
    parametric = sorted(n for n in facts.names if n in REGISTRY and REGISTRY[n].params)
    total_weight = sum(x.weight for x in xforms)
    sec = Section("fractal", "Fractal")
    sec.add("name", "Name", flame.name)
    sec.add("source", "Source", source, source or "not from a file")
    if flame.source_version:
        sec.add("source_version", "Written by", flame.source_version)
    sec.add("flame_width", "Flame's own width", flame.camera.width, f"{flame.camera.width} px")
    sec.add("flame_height", "Flame's own height", flame.camera.height, f"{flame.camera.height} px")
    sec.add("transforms", "Transforms", len(xforms))
    sec.add("active_transforms", "Transforms with positive weight", sum(1 for x in xforms if x.weight > 0))
    sec.add("final_transform", "Final transform", flame.final is not None)
    sec.add("total_weight", "Total weight", round(total_weight, 6), f"{total_weight:g}")
    sec.add("variation_terms", "Variation terms (all transforms)", len(facts.terms))
    sec.add("distinct_variations", "Distinct variations", len(facts.names))
    sec.add("parametric_variations", "Parametric variations", len(parametric), ", ".join(parametric) or "none")
    sec.add("variations_mean_per_transform", "Variations per transform (mean)", round(len(facts.terms) / max(1, len(all_xforms)), 3),
            f"{len(facts.terms) / max(1, len(all_xforms)):.2f}")
    sec.add("pre_blur_transforms", "Transforms with pre_blur", sum(1 for x in all_xforms if x.variations.get("pre_blur")))
    sec.add("post_affine_transforms", "Transforms with a post affine", sum(1 for x in all_xforms if x.has_post()))
    sec.add("xaos", "Xaos in use", facts.xaos_in_use)
    sec.add("invisible_transforms", "Invisible transforms (opacity 0)", sum(1 for x in xforms if x.opacity <= 0))
    sec.add("unsupported_variations", "Unsupported variations (ignored)", list(flame.unsupported), ", ".join(flame.unsupported) or "none")
    sec.add("palette_entries", "Palette entries", len(flame.palette))
    return sec


def camera_section(flame: Flame, s: FinalRenderSettings) -> Section:
    """The camera, and the fractal-space extent it shows at the output size."""
    cam = flame.camera
    ppu = cam.at_size(s.width, s.height).pixels_per_unit(s.width, s.height)
    span_w, span_h = s.width / ppu, s.height / ppu
    cx, cy = cam.center
    sec = Section("camera", "Camera")
    sec.add("center_x", "Centre x", cx, f"{cx:.6g}")
    sec.add("center_y", "Centre y", cy, f"{cy:.6g}")
    sec.add("scale", "Scale (pixels per unit at the flame's width)", cam.scale, f"{cam.scale:.6g}")
    sec.add("zoom", "Zoom (powers of two)", cam.zoom, f"{cam.zoom:g} (× {2 ** cam.zoom:.4g})")
    sec.add("rotate", "Rotation", cam.rotate, f"{cam.rotate:g}°")
    sec.add("pixels_per_unit", "Pixels per unit at the output size", round(ppu, 6), f"{ppu:.6g}")
    sec.add("units_per_pixel", "Fractal units per output pixel", 1.0 / ppu, f"{1.0 / ppu:.4g}")
    sec.add("span_width", "Visible width", round(span_w, 6), f"{span_w:.6g} units")
    sec.add("span_height", "Visible height", round(span_h, 6), f"{span_h:.6g} units")
    for key, label, value in (("left", "Left edge (unrotated)", cx - span_w / 2), ("right", "Right edge (unrotated)", cx + span_w / 2),
                              ("top", "Top edge (unrotated)", cy - span_h / 2), ("bottom", "Bottom edge (unrotated)", cy + span_h / 2)):
        sec.add(key, label, round(value, 6), f"{value:.6g}")
    return sec


def coloring_section(flame: Flame) -> Section:
    """Tone-mapping settings."""
    c = flame.coloring
    sec = Section("coloring", "Colouring")
    for key, label, value in (("brightness", "Brightness", c.brightness), ("gamma", "Gamma", c.gamma),
                              ("gamma_threshold", "Gamma threshold", c.gamma_threshold), ("vibrancy", "Vibrancy", c.vibrancy),
                              ("contrast", "Contrast", c.contrast)):
        sec.add(key, label, value, f"{value:g}")
    sec.add("background", "Background", rgb_to_hex(tuple(c.background)), _colour_text(tuple(c.background)))
    return sec


def palette_section(flame: Flame) -> Section:
    """Statistics of the 256-entry palette: luminance, saturation, dominant hues, smoothness."""
    sec = Section("palette", "Palette")
    colours = [tuple(int(v) for v in c) for c in flame.palette]
    sec.add("entries", "Entries", len(colours))
    if not colours:
        return sec
    lum = [luminance(c) for c in colours]
    saturations = [rgb_to_hsl(c)[1] for c in colours]
    mean = tuple(int(round(sum(c[i] for c in colours) / len(colours))) for i in range(3))
    deltas = [max(abs(a[i] - b[i]) for i in range(3)) for a, b in zip(colours, colours[1:])] or [0]
    dominant = _dominant_hues(colours)
    dark, bright = int(np.argmin(lum)), int(np.argmax(lum))
    sec.add("unique_colors", "Unique colours", len(set(colours)))
    sec.add("mean_color", "Mean colour", rgb_to_hex(mean), _colour_text(mean))
    sec.add("mean_luminance", "Mean luminance", round(sum(lum) / len(lum), 3), f"{sum(lum) / len(lum):.1f} / 255")
    sec.add("darkest", "Darkest entry", rgb_to_hex(colours[dark]), f"{rgb_to_hex(colours[dark])} at index {dark} (luminance {lum[dark]:.1f})")
    sec.add("brightest", "Brightest entry", rgb_to_hex(colours[bright]), f"{rgb_to_hex(colours[bright])} at index {bright} (luminance {lum[bright]:.1f})")
    sec.add("mean_saturation", "Mean saturation", round(sum(saturations) / len(saturations), 4), f"{100 * sum(saturations) / len(saturations):.1f} %")
    sec.add("grey_entries", "Near-grey entries", sum(1 for sat in saturations if sat <= GREY_SATURATION))
    sec.add("dominant_hues", "Dominant hues", [name for name, _ in dominant],
            ", ".join(f"{name} ({count})" for name, count in dominant) or "none (grey palette)")
    sec.add("max_step", "Largest step between neighbours", max(deltas), f"{max(deltas)} / 255 per channel")
    sec.add("mean_step", "Mean step between neighbours", round(sum(deltas) / len(deltas), 3), f"{sum(deltas) / len(deltas):.2f} / 255")
    sec.add("first", "First entry", rgb_to_hex(colours[0]))
    sec.add("last", "Last entry", rgb_to_hex(colours[-1]))
    return sec


def _dominant_hues(colours: list[tuple[int, int, int]]) -> list[tuple[str, int]]:
    """The three most common hue families among the saturated, mid-lightness entries."""
    families: dict[str, int] = {}
    for c in colours:
        _h, sat, light = rgb_to_hsl(c)
        if sat > GREY_SATURATION and 0.05 < light < 0.95:
            name = HUE_NAMES[int(hue(c) * len(HUE_NAMES) + 0.5) % len(HUE_NAMES)]
            families[name] = families.get(name, 0) + 1
    return sorted(families.items(), key=lambda kv: -kv[1])[:3]


def _colour_text(rgb: tuple[int, int, int]) -> str:
    return f"{rgb_to_hex(rgb)} (rgb {rgb[0]}, {rgb[1]}, {rgb[2]})"


def transforms_section(facts: FlameFacts) -> Section:
    """One row per transform (the final transform last, without weight / probability)."""
    total = sum(x.weight for x in facts.flame.xforms) or 1.0
    table = Table("", "Transforms", [
        ("index", "#"), ("name", "name"), ("weight", "weight"), ("probability", "probability"), ("color", "colour"),
        ("color_speed", "colour speed"), ("opacity", "opacity"), ("variations", "variations"), ("params", "parameters"),
        ("coefs", "pre affine [a b c d e f]"), ("post", "post affine"), ("determinant", "det"), ("scale_factor", "scale"),
        ("xaos", "xaos row")], id_key="index")
    for label, x in facts.labelled:
        row = _xform_row(label, x, x.weight / total)
        if label == "final":
            row["weight"] = row["probability"] = ("", "—")
        table.add_row(row)
    sec = Section("transforms", "Transforms")
    sec.tables.append(table)
    return sec


def _xform_row(label: str, x: XForm, probability: float) -> dict:
    a, b, c, d, _e, _f = x.coefs
    det = a * d - b * c
    variations = [(canonical_name(n), w) for n, w in x.variations.items() if w != 0]
    params = sorted(x.params.items())
    return {
        "index": label, "name": x.name or "", "weight": (x.weight, f"{x.weight:g}"),
        "probability": (round(probability, 6), f"{100 * probability:.2f} %"), "color": (x.color, f"{x.color:g}"),
        "color_speed": (x.color_speed, f"{x.color_speed:g}"), "opacity": (x.opacity, f"{x.opacity:g}"),
        "variations": (" ".join(f"{n}={w:g}" for n, w in variations), ", ".join(f"{n} {w:g}" for n, w in variations) or "none"),
        "params": (" ".join(f"{k}={v:g}" for k, v in params), ", ".join(f"{k} {v:g}" for k, v in params) or "—"),
        "coefs": (_affine_machine(x.coefs), _affine_text(x.coefs)),
        "post": (_affine_machine(x.post) if x.has_post() else "", _affine_text(x.post) if x.has_post() else "identity"),
        "determinant": (round(det, 6), f"{det:.4g}"), "scale_factor": (round(math.sqrt(abs(det)), 6), f"{math.sqrt(abs(det)):.4g}"),
        "xaos": (" ".join(f"{v:g}" for v in x.chaos) if x.chaos else "", ", ".join(f"{v:g}" for v in x.chaos) if x.chaos else "—"),
    }


def _affine_machine(coefs) -> str:
    return " ".join(f"{v:.10g}" for v in coefs)


def _affine_text(coefs) -> str:
    return "[" + ", ".join(f"{c:.6g}" for c in coefs) + "]"


def variations_section(facts: FlameFacts) -> Section:
    """Per-variation usage: which transforms, weight statistics, parameters, kind."""
    table = Table("", "Variations", [
        ("name", "variation"), ("transforms", "used by"), ("transform_list", "transforms"), ("total_weight", "total weight"),
        ("mean_weight", "mean weight"), ("min_weight", "min"), ("max_weight", "max"), ("parameters", "parameters"),
        ("kind", "kind"), ("supported", "supported")], id_key="name")
    usage = facts.usage()
    for name, uses in usage.items():
        weights = [w for _, w in uses]
        var = REGISTRY.get(name)
        params = sorted(var.params) if var else []
        table.add_row({
            "name": name, "transforms": len(uses),
            "transform_list": (" ".join(label for label, _ in uses), ", ".join(label for label, _ in uses)),
            "total_weight": _g(sum(weights)), "mean_weight": _g(sum(weights) / len(weights)),
            "min_weight": _g(min(weights)), "max_weight": _g(max(weights)),
            "parameters": (" ".join(params), ", ".join(params) or "—"), "kind": _variation_kind(name, var),
            "supported": var is not None or name == "pre_blur",
        })
    sec = Section("variations", "Variations")
    sec.add("terms", "Variation terms", len(facts.terms))
    most_used = next(iter(usage), "")
    sec.add("most_used", "Most used", most_used, most_used or "none")
    sec.tables.append(table)
    return sec


def _variation_kind(name: str, var) -> str:
    if name == "pre_blur":
        return "pre_blur"
    if var is None:
        return "unknown"
    return "random" if var.random else ("affine-dependent" if var.uses_affine else "plain")


def _g(value: float) -> tuple[float, str]:
    return round(value, 6), f"{value:g}"


def xaos_section(facts: FlameFacts) -> Section | None:
    """The xaos matrix, or None when xaos is not used."""
    if not facts.xaos_in_use:
        return None
    xforms = [x for x in facts.flame.xforms if x.weight > 0]
    n = len(xforms)
    table = Table("", "Xaos matrix (row = from, column = to)",
                  [("from", "from")] + [(f"to_{j}", f"→ {j}") for j in range(1, n + 1)], id_key="from")
    dead = 0
    for i, x in enumerate(xforms, start=1):
        chaos = (list(x.chaos) + [1.0] * n)[:n] if x.chaos is not None else [1.0] * n
        dead += sum(1 for c in chaos if c == 0)
        table.add_row({"from": i, **{f"to_{j}": _g(v) for j, v in enumerate(chaos, start=1)}})
    sec = Section("xaos", "Xaos (transform-to-transform weights)")
    sec.tables.append(table)
    sec.add("dead_links", "Forbidden links (weight 0)", dead)
    return sec


__all__ = ["FlameFacts", "fractal_section", "camera_section", "coloring_section", "palette_section", "transforms_section",
           "variations_section", "xaos_section"]
