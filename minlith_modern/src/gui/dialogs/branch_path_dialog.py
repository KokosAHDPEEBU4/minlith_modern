"""Диалог «Маршрут веток» — показывает траекторию решений для образца."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from src.core.branch_report import (
    branch_path_headers,
    describe_branch_path,
    format_branch_path_text,
)


class BranchPathDialog(QDialog):
    """Модальное окно с таблицей принятых движком решений (веток)."""

    def __init__(self, path: dict | None, sample: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Маршрут веток — {sample}" if sample else "Маршрут веток")
        self.setMinimumSize(640, 420)
        self._path = path
        self._sample = sample

        layout = QVBoxLayout(self)

        rows = describe_branch_path(path)
        if not rows:
            layout.addWidget(QLabel(
                "Для этого образца маршрут не передан.\n"
                "Движок отдаёт маршрут веток только в режиме «Excel (корректные округл.)»."
            ))
        else:
            layout.addWidget(QLabel(
                "Последовательность принятых решений (сверху вниз):"
            ))
            table = QTableWidget(len(rows), len(branch_path_headers()))
            table.setHorizontalHeaderLabels(list(branch_path_headers()))
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.verticalHeader().setVisible(False)
            for i, r in enumerate(rows):
                table.setItem(i, 0, QTableWidgetItem(str(r["stage_title"])))
                table.setItem(i, 1, QTableWidgetItem(str(r["name"])))
                table.setItem(i, 2, QTableWidgetItem(str(r["condition"])))
                table.setItem(i, 3, QTableWidgetItem(str(r["source"])))
            h = table.horizontalHeader()
            for c in range(len(branch_path_headers())):
                h.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
            layout.addWidget(table)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_copy = QPushButton("Копировать текст")
        self._btn_copy.setEnabled(bool(rows))
        self._btn_copy.clicked.connect(self._on_copy)
        btn_row.addWidget(self._btn_copy)
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def _on_copy(self) -> None:
        QApplication.clipboard().setText(
            format_branch_path_text(self._path, self._sample)
        )
