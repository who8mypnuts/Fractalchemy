"""Render the Fractalchemy mark — the main version and every alternative — at high resolution into `logo/`.

Usage:
    python tools/render_logo.py [--out logo] [--size 1024]

Writes, per variant: `<variant>_<size>.png` (transparent), `<variant>_on_white.png`, `<variant>_on_dark.png`, the
wordmark in light and dark, and a contact sheet of everything plus the small sizes (16–64 px) so the mark can be
judged at task-bar scale too.
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
    parser.add_argument("--size", type=int, default=1024)
    args = parser.parse_args()
    from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
    from PySide6.QtWidgets import QApplication

    from fractalchemy.widgets.logo import VARIANTS, logo_pixmap, wordmark_pixmap

    QApplication.instance() or QApplication([])
    args.out.mkdir(parents=True, exist_ok=True)
    white, dark = QColor("#ffffff"), QColor("#1b1e27")
    for variant, description in VARIANTS.items():
        logo_pixmap(args.size, variant=variant).save(str(args.out / f"{variant}_{args.size}.png"))
        logo_pixmap(args.size, white, variant).save(str(args.out / f"{variant}_on_white.png"))
        logo_pixmap(args.size, dark, variant, ink=QColor("#e8ecf5") if variant == "mono" else None).save(str(args.out / f"{variant}_on_dark.png"))
        wordmark_pixmap(256, white, variant=variant).save(str(args.out / f"{variant}_wordmark.png"))
        wordmark_pixmap(256, dark, dark=True, variant=variant).save(str(args.out / f"{variant}_wordmark_dark.png"))
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
    print(f"{len(VARIANTS)} variants rendered into {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
