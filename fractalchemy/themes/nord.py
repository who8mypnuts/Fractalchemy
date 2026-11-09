"""The Nord family (https://www.nordtheme.com): the reference theme and six variations, all from Nord's sixteen colours.

    Polar Night  nord0 #2E3440  nord1 #3B4252  nord2 #434C5E  nord3 #4C566A
    Snow Storm   nord4 #D8DEE9  nord5 #E5E9F0  nord6 #ECEFF4
    Frost        nord7 #8FBCBB  nord8 #88C0D0  nord9 #81A1C1  nord10 #5E81AC
    Aurora       nord11 #BF616A (red)  nord12 #D08770 (orange)  nord13 #EBCB8B (yellow)  nord14 #A3BE8C (green)
                 nord15 #B48EAD (purple)

Syntax follows Nord's own editor mapping: keywords nord9, types nord7, functions nord8, strings nord14, numbers nord15,
preprocessor nord10. Comments use `#616E88`, Nord's brightened nord3; it is still below 3:1 on nord0, so `derive`
lifts it a little further.
"""

from __future__ import annotations

from .model import Seed

NORD = {f"nord{i}": c for i, c in enumerate((
    "#2E3440", "#3B4252", "#434C5E", "#4C566A", "#D8DEE9", "#E5E9F0", "#ECEFF4", "#8FBCBB",
    "#88C0D0", "#81A1C1", "#5E81AC", "#BF616A", "#D08770", "#EBCB8B", "#A3BE8C", "#B48EAD"))}
N = NORD
HUES = dict(red=N["nord11"], orange=N["nord12"], yellow=N["nord13"], green=N["nord14"], cyan=N["nord7"], blue=N["nord9"],
            purple=N["nord15"])
FROST_SYNTAX = {"keyword": N["nord9"], "type": N["nord7"], "function": N["nord8"], "builtin": N["nord8"], "string": N["nord14"],
                "number": N["nord15"], "preprocessor": N["nord10"], "special": N["nord13"], "api": N["nord8"], "definition": N["nord8"],
                "member": N["nord7"], "constant": N["nord15"]}
FAMILY = "Nord"

SEEDS = (
    Seed("Nord", FAMILY, True, bg=N["nord0"], surface=N["nord1"], base="#2A303B", fg=N["nord4"], dim="#AEB7C6",
         accent=N["nord8"], comment="#616E88", overrides=FROST_SYNTAX, **HUES),
    Seed("Nord Deep", FAMILY, True, bg="#242933", surface=N["nord0"], base="#1E222A", fg=N["nord4"], dim="#AEB7C6",
         accent=N["nord8"], comment="#616E88", overrides=FROST_SYNTAX, **HUES),
    Seed("Nord Frost", FAMILY, True, bg=N["nord0"], surface=N["nord1"], base="#2A303B", fg=N["nord6"], dim="#B9C2D1",
         accent=N["nord10"], comment="#6C7A96",
         overrides={**FROST_SYNTAX, "keyword": N["nord7"], "type": N["nord9"], "special": N["nord8"]}, **HUES),
    Seed("Nord Aurora", FAMILY, True, bg=N["nord0"], surface=N["nord1"], base="#2A303B", fg=N["nord4"], dim="#AEB7C6",
         accent=N["nord15"], comment="#6C7A96",
         overrides={**FROST_SYNTAX, "keyword": N["nord12"], "type": N["nord13"], "preprocessor": N["nord11"],
                    "special": N["nord15"]}, **HUES),
    Seed("Nord High Contrast", FAMILY, True, bg="#1E2128", surface=N["nord0"], base="#191C22", fg=N["nord6"], dim="#C2CAD8",
         accent=N["nord8"], comment="#8A94A8", overrides=FROST_SYNTAX, **HUES),
    Seed("Nord Snow Storm", FAMILY, False, bg=N["nord5"], surface=N["nord4"], base=N["nord6"], fg=N["nord0"], dim=N["nord3"],
         accent=N["nord10"], comment="#7B88A1",
         overrides={**FROST_SYNTAX, "keyword": N["nord10"], "function": N["nord10"], "api": N["nord10"]}, **HUES),
    Seed("Nord Light Frost", FAMILY, False, bg=N["nord6"], surface=N["nord5"], base="#F8F9FB", fg=N["nord1"], dim=N["nord3"],
         accent=N["nord9"], comment="#7B88A1",
         overrides={**FROST_SYNTAX, "keyword": N["nord10"], "type": N["nord7"]}, **HUES),
)

__all__ = ["SEEDS", "NORD", "FAMILY"]
