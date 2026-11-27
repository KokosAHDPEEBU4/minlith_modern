"""Shared layout tokens for GUI pages.

Keeping page margins/spacing and header styling in one place prevents the
"every page is a little different" drift (9 vs 0 vs 8 px margins, 13 vs 18 vs
22 px headers).
"""

from __future__ import annotations

from PyQt6.QtWidgets import QBoxLayout, QLabel, QSizePolicy, QWidget

PAGE_MARGINS: tuple[int, int, int, int] = (20, 20, 20, 20)
PAGE_SPACING = 12
HEADER_OBJECT_NAME = "pageHeader"


def normalize_page_layout(
    page: QWidget,
    title: str,
    *,
    add_header: bool = False,
) -> QLabel | None:
    """Apply the shared page margins/spacing and normalise the page header.

    If ``add_header`` is true and no label with ``title`` exists, a header is
    inserted at the top of the page layout (used by Reports/Logs, which had no
    page title at all).
    """
    layout = page.layout()
    if layout is not None:
        layout.setContentsMargins(*PAGE_MARGINS)
        layout.setSpacing(PAGE_SPACING)

    header: QLabel | None = None
    for label in page.findChildren(QLabel):
        if label.text() == title:
            header = label
            break

    if header is None and add_header and isinstance(layout, QBoxLayout):
        header = QLabel(title)
        layout.insertWidget(0, header)

    if header is not None:
        header.setObjectName(HEADER_OBJECT_NAME)
        # Drop ad-hoc inline header styles; the theme QSS owns typography.
        header.setStyleSheet("")
        # QStyleSheetStyle reports an 8 px negative contents rect for a label
        # that just received an objectName, which clips the top of 20 px
        # glyphs.  Explicit 8 px margins cancel that offset (and give the
        # header a small, consistent optical indent).
        header.setContentsMargins(8, 8, 8, 8)
        # objectName changes do not always invalidate the cached size hint,
        # which left 20 px headers clipped to an 11 px label height.
        header.setMinimumHeight(28)
        header.setSizePolicy(QSizePolicy.Policy.Expanding,
                             QSizePolicy.Policy.Fixed)
        style = header.style()
        if style is not None:
            style.unpolish(header)
            style.polish(header)
        header.updateGeometry()
    return header
