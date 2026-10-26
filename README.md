# HueClid
A fractal gradient editor and browser with aspirations. Perhaps one day it will be a full fractal editor.
For now, HueClid aims to be a gradient library and browser with the ability to edit, save, and convert gradient formats to a variety of fractal programs.

## Running

```bash
pip install -r requirements.txt
python main.py
```

Tests (headless, uses Qt's offscreen platform):

```bash
python -m pytest
```

## What it does today

* **Open** (`File ▸ Open…`, `Ctrl+O`) any of:
  * `.flame` – the `<palette>` of the first `<flame>` in the file
  * `.ugr` / `.gradient` – the first gradient in the file (Ultra Fractal format)
  * images – dominant colours are extracted and ordered into a gradient:
    PNG / APNG (first frame), JPEG, AVIF, HEIC/HEIF, JPEG XL, WebP, GIF, BMP, TIFF,
    and SVG (rasterised via Qt). Transparent pixels are ignored.
* The gradient is painted in the editor with one **node** beneath each colour stop.
  Drag a node anywhere along the bar, including past other nodes; the others stay put.
* **Save** (`Ctrl+S`) writes back to the source file when it is a flame/ugr
  (for a flame, only the first palette block is rewritten; everything else is preserved).
  **Save As…** lets you pick `.flame` or `.ugr`. Image-derived gradients save as `.ugr`.

## Layout

```
main.py                 entry point only
ui/main_window.ui       Qt Designer layout (GradientEditor is a promoted custom widget)
hueclid/
  config.py             tunables: node counts, simplify tolerance, sizes
  model/                Qt-free data: colours, stops, Gradient, stop simplification
  formats/              one module per file type + registry (extension → format)
  imaging/              decoders/plugins, SVG rasteriser, palette extraction, colour ordering
  widgets/              GradientStrip, NodeBar, GradientEditor, position mapping
  ui/                   .ui loader, GradientDocument (state + signals), file actions, MainWindow
tests/                  pytest suite
```

### Notes for tuning
* Flame and UF palettes contain 256 entries. On import, stops that a straight blend
  between their neighbours would reproduce within `IMPORT_SIMPLIFY_TOLERANCE`
  (per channel, 0–255) are dropped so the node bar stays usable. Set it to `0` to keep every stop.
* `IMAGE_COLOR_COUNT` controls how many nodes an image produces; `IMAGE_ORDERING`
  picks how they are sequenced (`path` = smooth nearest-neighbour walk from the darkest
  colour, or `luminance` / `hue`).
* All loaders already return *every* gradient in a file; only the UI picks the first.
* HEIC and JPEG XL need `pillow-heif` / `pillow-jxl-plugin`; if either is missing those
  extensions simply disappear from the Open dialog, and opening such a file by path
  reports which package to install.
