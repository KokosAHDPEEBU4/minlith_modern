"""Страница файлов — импорт, drag-drop, список последних файлов."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.gui.widgets.drag_drop_widget import DragDropWidget
from src.io.excel import load_samples

logger = logging.getLogger(__name__)


class FilesPage(QWidget):
    """Страница импорта и управления файлами."""

    samples_loaded = pyqtSignal(list)

    def __init__(self, config=None, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self._loaded_samples: list = []

        layout = QVBoxLayout(self)

        header = QLabel("Файлы")
        header.setStyleSheet("font-size: 18px; font-weight: bold; padding: 8px;")
        layout.addWidget(header)

        splitter = QSplitter(Qt.Orientation.Vertical)

        top = QWidget()
        top_layout = QVBoxLayout(top)

        self._drag_drop = DragDropWidget()
        self._drag_drop.files_dropped.connect(self._on_files_dropped)
        top_layout.addWidget(self._drag_drop)

        btn_row = QHBoxLayout()
        self._btn_import = QPushButton("Импорт .xlsx")
        self._btn_import.clicked.connect(self._on_import_click)
        btn_row.addWidget(self._btn_import)

        self._btn_import_csv = QPushButton("Импорт .csv")
        self._btn_import_csv.clicked.connect(self._on_import_csv)
        btn_row.addWidget(self._btn_import_csv)

        btn_row.addStretch()

        self._btn_template = QPushButton("Шаблон (эталон)")
        self._btn_template.setToolTip("Скачать шаблон с эталоном T-O2")
        self._btn_template.clicked.connect(self._on_export_template)
        btn_row.addWidget(self._btn_template)

        self._btn_blank = QPushButton("Шаблон (пустой)")
        self._btn_blank.setToolTip("Скачать пустой шаблон для заполнения")
        self._btn_blank.clicked.connect(self._on_export_blank)
        btn_row.addWidget(self._btn_blank)

        top_layout.addLayout(btn_row)

        splitter.addWidget(top)

        bottom = QWidget()
        bottom_layout = QVBoxLayout(bottom)

        list_header = QHBoxLayout()
        list_header.addWidget(QLabel("Загруженные образцы:"))
        list_header.addStretch()
        self._btn_clear = QPushButton("Очистить всё")
        self._btn_clear.clicked.connect(self._clear_list)
        list_header.addWidget(self._btn_clear)
        bottom_layout.addLayout(list_header)

        self._file_list = QListWidget()
        self._file_list.setAlternatingRowColors(True)
        self._file_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        bottom_layout.addWidget(self._file_list)

        splitter.addWidget(bottom)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

    def _on_files_dropped(self, paths: list[str]) -> None:
        for path in paths:
            p = Path(path)
            if p.is_dir():
                self._load_folder(p)
            else:
                self._load_file(path)

    def _load_folder(self, folder: Path) -> None:
        """Рекурсивная загрузка всех .xlsx/.csv файлов из папки."""
        extensions = {".xlsx", ".csv"}
        files = sorted(f for f in folder.rglob("*") if f.suffix.lower() in extensions)
        if not files:
            QMessageBox.information(self, "Импорт", f"Файлы .xlsx/.csv не найдены в {folder.name}")
            return
        for f in files:
            self._load_file(str(f))

    def _on_import_click(self) -> None:
        from PyQt6.QtWidgets import QFileDialog
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Импорт файлов", "",
            "Excel (*.xlsx);;CSV (*.csv);;Все файлы (*)",
        )
        for path in paths:
            self._load_file(path)

    def _on_import_csv(self) -> None:
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "Импорт CSV", "",
            "CSV (*.csv);;Все файлы (*)",
        )
        if path:
            self._load_csv(path)

    def _on_export_template(self) -> None:
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт шаблона", "minlith_template.xlsx",
            "Excel (*.xlsx)",
        )
        if not path:
            return
        try:
            from src.io.template import create_reference_template
            create_reference_template(path)
            QMessageBox.information(self, "Шаблон", f"Шаблон сохранён:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _on_export_blank(self) -> None:
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт пустого шаблона", "minlith_blank.xlsx",
            "Excel (*.xlsx)",
        )
        if not path:
            return
        try:
            from src.io.template import create_template
            create_template(path, sample_names=["Образец 1", "Образец 2", "Образец 3"])
            QMessageBox.information(self, "Шаблон", f"Пустой шаблон сохранён:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _load_file(self, path: str) -> None:
        try:
            samples = load_samples(path)
            if not samples:
                QMessageBox.information(self, "Импорт", f"Образцы не найдены в {Path(path).name}")
                return
            self._loaded_samples.extend(samples)
            for s in samples:
                self._file_list.addItem(f"{s.name}  ({Path(path).name})")
            if self._config:
                self._config.add_recent_file(path)
            self.samples_loaded.emit(samples)
            logger.info("Загружено %d образцов из %s", len(samples), Path(path).name)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка импорта", str(e))
            logger.error("Ошибка загрузки %s: %s", path, e)

    def _load_csv(self, path: str) -> None:
        try:
            import csv
            samples = []
            with open(path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f, delimiter=";")
                for row in reader:
                    from src.core.models import OxideComposition, Sample
                    name = row.get("Name", row.get("name", Path(path).stem))
                    oxide_data = {}
                    for k, v in row.items():
                        if k.lower() in OxideComposition.__dataclass_fields__:
                            try:
                                oxide_data[k.lower()] = float(v.replace(",", ".")) if v else 0.0
                            except (ValueError, AttributeError):
                                oxide_data[k.lower()] = 0.0
                    comp = OxideComposition(**oxide_data)
                    samples.append(Sample(name=name, composition=comp))

            self._loaded_samples.extend(samples)
            for s in samples:
                self._file_list.addItem(f"{s.name}  ({Path(path).name})")
            self.samples_loaded.emit(samples)
            logger.info("Загружено %d образцов из CSV", len(samples))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка импорта CSV", str(e))

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        row = self._file_list.row(item)
        if 0 <= row < len(self._loaded_samples):
            sample = self._loaded_samples[row]
            self.samples_loaded.emit([sample])

    def _clear_list(self) -> None:
        self._loaded_samples.clear()
        self._file_list.clear()

    def get_all_samples(self) -> list:
        return list(self._loaded_samples)
