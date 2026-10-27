"""Where an image sits inside a widget: zoom, offset, clamping and coordinate mapping.

Pure geometry (QtCore value types only, no widgets), so the viewport's zoom/pan rules
can be unit-tested without a window:

* `zoom` is screen pixels per image pixel; `None` means *fit* (the whole image visible, letterboxed);
* the image is centred when smaller than the widget and clamped so it never leaves the
  widget when larger;
* zooming out stops at the fit zoom, zooming in at `MAX_ZOOM` (fit never exceeds it either, so a
  tiny image is shown at 300 % and centred rather than blown up further).
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRect, QRectF

MAX_ZOOM = 3.0   # 300 %


class ViewGeometry:
    """Placement of an `image_size` image inside a `widget_size` widget."""

    def __init__(self, image_size: tuple[int, int] = (800, 600), widget_size: tuple[int, int] = (1, 1)):
        self._image_size = image_size
        self._widget_size = widget_size
        self._zoom: float | None = None
        self._offset = QPointF(0.0, 0.0)
        self._image_rect = QRect()
        self._layout()

    # --- sizes ----------------------------------------------------------------
    @property
    def image_size(self) -> tuple[int, int]:
        """Size of the image being placed, in pixels."""
        return self._image_size

    @property
    def widget_size(self) -> tuple[int, int]:
        """Size of the widget the image is placed in."""
        return self._widget_size

    def set_image_size(self, size: tuple[int, int], keep_zoom: bool = False) -> None:
        """A new image resolution; returns to fit unless `keep_zoom`."""
        self._image_size = (max(1, int(size[0])), max(1, int(size[1])))
        if not keep_zoom:
            self._zoom = None
        self._layout()

    def set_widget_size(self, width: int, height: int) -> None:
        """The widget was resized (zoom is kept, the offset re-clamped)."""
        self._widget_size = (max(1, int(width)), max(1, int(height)))
        self._layout()

    # --- zoom -----------------------------------------------------------------
    def fit_zoom(self) -> float:
        """Screen pixels per image pixel at which the whole image fits the widget (capped at MAX_ZOOM).

        This is also the smallest zoom allowed: zooming out further would only add empty border.
        """
        (iw, ih), (w, h) = self._image_size, self._widget_size
        return min(MAX_ZOOM, max(1e-6, min(w / iw, h / ih)))

    def zoom(self) -> float:
        """Screen pixels per image pixel (the fit zoom while fitting)."""
        return self.fit_zoom() if self._zoom is None else self._zoom

    @property
    def is_fit(self) -> bool:
        """True while no explicit zoom is set."""
        return self._zoom is None

    def set_zoom(self, zoom: float | None, anchor: QPointF | None = None) -> None:
        """Set the zoom (None = fit); the image point under screen `anchor` (default: centre) stays put."""
        if zoom is None:
            self._zoom = None
            self._layout()
            return
        zoom = max(self.fit_zoom(), min(MAX_ZOOM, float(zoom)))
        w, h = self._widget_size
        anchor = anchor if anchor is not None else QPointF(w / 2, h / 2)
        image_point = self.screen_to_image(anchor)
        self._zoom = zoom
        self._offset = anchor - image_point * zoom
        self._layout()

    def reset(self) -> None:
        """Back to fit."""
        self.set_zoom(None)

    def pan(self, delta: QPointF) -> None:
        """Scroll by `delta` screen pixels (leaves fit mode; clamped so the image stays in view)."""
        self.set_offset(self._offset + delta)

    def set_offset(self, offset: QPointF) -> None:
        """Place image pixel (0, 0) at screen `offset` (leaves fit mode; clamped)."""
        if self._zoom is None:
            self._zoom = self.fit_zoom()
        self._offset = QPointF(offset)
        self._layout()

    # --- mapping --------------------------------------------------------------
    @property
    def offset(self) -> QPointF:
        """Screen position of image pixel (0, 0)."""
        return QPointF(self._offset)

    @property
    def image_rect(self) -> QRect:
        """Screen rectangle of the visible part of the image."""
        return QRect(self._image_rect)

    def screen_to_image(self, pos: QPointF) -> QPointF:
        """Image pixel coordinates under a screen point."""
        z = self.zoom()
        return QPointF((pos.x() - self._offset.x()) / z, (pos.y() - self._offset.y()) / z)

    def image_to_screen(self, region: QRectF) -> QRectF:
        """Screen rectangle covered by an image-pixel rectangle under the current view."""
        z = self.zoom()
        return QRectF(self._offset.x() + region.x() * z, self._offset.y() + region.y() * z, region.width() * z, region.height() * z)

    def visible_region(self) -> QRectF:
        """The visible part of the image, in image pixels."""
        rect = self._image_rect
        top_left = self.screen_to_image(QPointF(rect.x(), rect.y()))
        z = self.zoom()
        return QRectF(top_left.x(), top_left.y(), rect.width() / z, rect.height() / z)

    # --- internals ------------------------------------------------------------
    def _layout(self) -> None:
        """Clamp the offset (centre when smaller than the widget) and recompute the visible rect."""
        (iw, ih), (w, h) = self._image_size, self._widget_size
        z = self.zoom()
        shown_w, shown_h = iw * z, ih * z
        x = (w - shown_w) / 2 if self._zoom is None or shown_w <= w else min(0.0, max(w - shown_w, self._offset.x()))
        y = (h - shown_h) / 2 if self._zoom is None or shown_h <= h else min(0.0, max(h - shown_h, self._offset.y()))
        self._offset = QPointF(x, y)
        self._image_rect = QRectF(x, y, shown_w, shown_h).intersected(QRectF(0, 0, w, h)).toAlignedRect()
