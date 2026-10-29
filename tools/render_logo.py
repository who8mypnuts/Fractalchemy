"""Render the Fractalchemy mark — the main version and every alternative — at high resolution into `logo/`.

Usage:
    python tools/render_logo.py [--out logo] [--size 1024]

Writes one folder per variant (`logo/main/`, `logo/mono/`, …) holding the mark at `--size` pixels — transparent, on
white and on dark — the wordmark (a quarter of that height) in the same three forms, and `design_sheet.png` (the
mark at 16–256 px beside the light and dark wordmarks, the sheet used while designing); plus `contact_sheet.png`
with every variant side by side. The default size is 2048 px.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=ROOT / "logo")
    parser.add_argument("--size", type=int, default=2048)
    args = parser.parse_args()
    from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
    from PySide6.QtWidgets import QApplication

    from fractalchemy.widgets.logo import VARIANTS, logo_pixmap, wordmark_pixmap

    QApplication.instance() or QApplication([])
    args.out.mkdir(parents=True, exist_ok=True)
    white, dark = QColor("#ffffff"), QColor("#1b1e27")
    for variant, description in VARIANTS.items():
        folder = args.out / variant
        folder.mkdir(parents=True, exist_ok=True)
        logo_pixmap(args.size, variant=variant).save(str(folder / f"mark_{args.size}.png"))
        logo_pixmap(args.size, white, variant).save(str(folder / f"mark_{args.size}_on_white.png"))
        logo_pixmap(args.size, dark, variant, ink=QColor("#e8ecf5") if variant == "mono" else None).save(str(folder / f"mark_{args.size}_on_dark.png"))
        wordmark_pixmap(args.size // 4, variant=variant).save(str(folder / f"wordmark_{args.size // 4}.png"))
        wordmark_pixmap(args.size // 4, white, variant=variant).save(str(folder / f"wordmark_{args.size // 4}_on_white.png"))
        wordmark_pixmap(args.size // 4, dark, dark=True, variant=variant).save(str(folder / f"wordmark_{args.size // 4}_on_dark.png"))
        _design_sheet(variant, description).save(str(folder / "design_sheet.png"))
    # the contact sheet: each variant large, with its small sizes beside it and its description beneath
    cell_w, cell_h = 560, 330
    sheet = QPixmap(cell_w * 3, cell_h * 2)
    sheet.fill(QColor("#f4f5f8"))
    painter = QPainter(sheet)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    font = QFont("Sans Serif")
    font.setPixelSize(15)
    painter.setFont(font)
    for i, (variant, description) in enumerate(VARIANTS.items()):
        x0, y0 = (i % 3) * cell_w + 20, (i // 3) * cell_h + 20
        painter.drawPixmap(x0, y0, logo_pixmap(240, variant=variant))
        x = x0 + 260
        for small in (16, 24, 32, 48, 64):
            painter.drawPixmap(x, y0 + 240 - small, logo_pixmap(small, variant=variant))
            x += small + 14
        painter.drawPixmap(x0 + 260, y0 + 20, wordmark_pixmap(64, variant=variant))
        painter.setPen(QColor("#1f2a44"))
        painter.drawText(x0, y0 + 265, cell_w - 40, 50, 0x1000 | 0x0001, f"{variant}: {description}")   # TextWordWrap | AlignLeft
    painter.end()
    sheet.save(str(args.out / "contact_sheet.png"))
    print(f"{len(VARIANTS)} variants rendered into {args.out} (one folder each, plus contact_sheet.png)")
    return 0


def _design_sheet(variant: str, description: str):
    """The sheet used while designing: the mark at 16–256 px in a row, the wordmark in light and dark beneath."""
    from PySide6.QtGui import QColor, QFont, QPainter, QPixmap

    from fractalchemy.widgets.logo import logo_pixmap, wordmark_pixmap

    sheet = QPixmap(1200, 520)
    sheet.fill(QColor("#f4f5f8"))
    painter = QPainter(sheet)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    x = 30
    for size in (16, 24, 32, 48, 64, 128, 256):
        painter.drawPixmap(x, 30 + (256 - size), logo_pixmap(size, variant=variant))
        x += size + 30
    painter.drawPixmap(30, 320, wordmark_pixmap(112, variant=variant))
    painter.drawPixmap(660, 330, wordmark_pixmap(96, QColor("#1b1e27"), dark=True, variant=variant))
    font = QFont("Sans Serif")
    font.setPixelSize(16)
    painter.setFont(font)
    painter.setPen(QColor("#1f2a44"))
    painter.drawText(30, 480, f"{variant}: {description}")
    painter.end()
    return sheet


if __name__ == "__main__":
    sys.exit(main())
