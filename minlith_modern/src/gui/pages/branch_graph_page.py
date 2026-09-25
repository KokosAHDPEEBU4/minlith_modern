"""Страница «Граф разветвлений»: дерево решений, маршрут и ручной выбор ветки.

Дерево строится из каталога решений (``branch_catalog``); пройденный образцом
маршрут подсвечивается; пользователь может принудительно выбрать ветку и
пересчитать образец (override, этапы 2–4 ТЗ ``docs/planning/TZ_BRANCH_GRAPH.md``).
"""

from __future__ import annotations

from dataclasses import replace

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.branch_report import (
    branch_path_json,
    diff_branch_paths,
    forced_branch_ids,
    path_branch_ids,
)
from src.core.excel_parity.branch_catalog import catalog_to_dict


class BranchGraphPage(QWidget):
    """Визуализация графа решений и ручной выбор веток."""

    def __init__(self, calculator=None, parent=None) -> None:
        super().__init__(parent)
        self._calculator = calculator
        self._results: list = []
        self._current_result = None
        self._overrides: dict[str, str] = {}
        self._decisions: list[dict] = catalog_to_dict()["decisions"]

        layout = QVBoxLayout(self)
        header = QLabel("Граф разветвлений")
        header.setStyleSheet("font-size: 18px; font-weight: bold; padding: 8px;")
        layout.addWidget(header)

        top = QHBoxLayout()
        top.addWidget(QLabel("Образец:"))
        self._sample_combo = QComboBox()
        self._sample_combo.setMinimumWidth(200)
        self._sample_combo.currentIndexChanged.connect(self._on_sample_changed)
        top.addWidget(self._sample_combo)
        top.addStretch()

        self._btn_force = QPushButton("Принудительно выбрать ветку")
        self._btn_force.setEnabled(False)
        self._btn_force.clicked.connect(self._on_force)
        top.addWidget(self._btn_force)

        self._btn_reset = QPushButton("Снять выбор ветки")
        self._btn_reset.clicked.connect(self._on_reset)
        top.addWidget(self._btn_reset)

        self._btn_recalc = QPushButton("Пересчитать с выбранными ветками")
        self._btn_recalc.clicked.connect(self._on_recalculate)
        top.addWidget(self._btn_recalc)

        self._btn_export = QPushButton("Экспорт маршрута (JSON)")
        self._btn_export.clicked.connect(self._on_export_json)
        top.addWidget(self._btn_export)

        self._btn_compare = QPushButton("Сравнить с авто")
        self._btn_compare.clicked.connect(self._on_compare)
        top.addWidget(self._btn_compare)
        layout.addLayout(top)

        body = QHBoxLayout()

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Решение / ветка", "Условие", "Источник"])
        self._tree.setColumnWidth(0, 240)
        self._tree.itemSelectionChanged.connect(self._on_tree_selection)
        body.addWidget(self._tree, stretch=3)

        side = QVBoxLayout()
        side.addWidget(QLabel("Принудительный выбор (override):"))
        self._overrides_label = QLabel("нет")
        self._overrides_label.setWordWrap(True)
        self._overrides_label.setStyleSheet("color: #888;")
        side.addWidget(self._overrides_label)
        side.addWidget(QLabel("Результат:"))
        self._result_label = QLabel("")
        self._result_label.setWordWrap(True)
        side.addWidget(self._result_label)
        side.addStretch()
        body.addLayout(side, stretch=2)
        layout.addLayout(body, stretch=1)

        self._build_tree()
        self._update_overrides_label()

    # ── построение дерева ──

    def _build_tree(self) -> None:
        self._tree.clear()
        for decision in self._decisions:
            parent = QTreeWidgetItem([f"{decision['title']}  ({decision['id']})", "", ""])
            font = parent.font(0)
            font.setBold(True)
            parent.setFont(0, font)
            parent.setData(0, Qt.ItemDataRole.UserRole,
                           (decision["id"], None, decision["overridable"]))
            for branch in decision["branches"]:
                child = QTreeWidgetItem([
                    branch["title"], branch.get("condition", ""),
                    branch.get("source", ""),
                ])
                child.setData(0, Qt.ItemDataRole.UserRole, (
                    decision["id"], branch["id"], decision["overridable"],
                    branch["title"]))
                parent.addChild(child)
            self._tree.addTopLevelItem(parent)
        self._tree.expandAll()

    # ── данные ──

    def set_calculator(self, calculator) -> None:
        self._calculator = calculator

    def set_results(self, results: list) -> None:
        self._results = list(results)
        self._overrides.clear()
        blocked = self._sample_combo.blockSignals(True)
        self._sample_combo.clear()
        for result in self._results:
            self._sample_combo.addItem(getattr(result, "sample_name", "?"))
        self._sample_combo.blockSignals(blocked)
        self._current_result = self._results[0] if self._results else None
        self._refresh()

    def _on_sample_changed(self, index: int) -> None:
        if 0 <= index < len(self._results):
            self._current_result = self._results[index]
            self._overrides.clear()
        self._refresh()

    # ── подсветка маршрута ──

    def _refresh(self) -> None:
        path = getattr(self._current_result, "branch_path", None) \
            if self._current_result else None
        taken = path_branch_ids(path)
        forced = forced_branch_ids(path)

        for i in range(self._tree.topLevelItemCount()):
            parent = self._tree.topLevelItem(i)
            parent_taken = False
            for j in range(parent.childCount()):
                child = parent.child(j)
                data = child.data(0, Qt.ItemDataRole.UserRole)
                if not data or data[1] is None:
                    continue
                branch_id = data[1]
                title = data[3] if len(data) > 3 else data[1]
                is_taken = branch_id in taken
                is_forced = branch_id in forced
                parent_taken = parent_taken or is_taken
                prefix = "★ " if is_forced else ("✓ " if is_taken else "   ")
                child.setText(0, prefix + title)
                font = child.font(0)
                font.setBold(is_taken)
                font.setItalic(is_forced)
                child.setFont(0, font)
            parent_font = parent.font(0)
            parent_font.setBold(True)
            parent.setFont(0, parent_font)
            if parent_taken:
                parent.setText(0, parent.text(0).rstrip(" ✓"))
                parent.setText(0, parent.text(0) + "  ✓")

        self._update_result_label()
        self._update_overrides_label()

    def _input_sample(self):
        from src.core.models import Sample
        result = self._current_result
        if result is None:
            return None
        return Sample(name=getattr(result, "sample_name", "sample"),
                      composition=result.input_composition)

    def _update_result_label(self) -> None:
        result = self._current_result
        if result is None:
            self._result_label.setText("")
            return
        minerals = result.minerals_weight
        self._result_label.setText(
            f"Тип: {result.rock_type.name}\n"
            f"F={result.coefficients.F:.3f}  A={result.coefficients.A:.3f}\n"
            f"Ab={minerals.ab:.2f}  An={minerals.an:.2f}  Or={minerals.or_:.2f}  "
            f"Q={minerals.q:.2f}"
        )

    def _update_overrides_label(self) -> None:
        if not self._overrides:
            self._overrides_label.setText("нет")
            return
        self._overrides_label.setText(
            "\n".join(f"{d} → {b}" for d, b in self._overrides.items()))

    # ── действия ──

    def _on_tree_selection(self) -> None:
        items = self._tree.selectedItems()
        enabled = False
        if items:
            data = items[0].data(0, Qt.ItemDataRole.UserRole)
            if data and data[1] is not None and data[2]:
                enabled = True
        self._btn_force.setEnabled(enabled)

    def _on_force(self) -> None:
        items = self._tree.selectedItems()
        if not items:
            return
        data = items[0].data(0, Qt.ItemDataRole.UserRole)
        if not data or data[1] is None:
            QMessageBox.information(self, "Граф", "Выберите ветку (не решение).")
            return
        decision_id, branch_id, overridable = data[0], data[1], data[2]
        if not overridable:
            QMessageBox.information(
                self, "Граф", "Это решение не поддерживает ручной выбор.")
            return
        self._overrides[decision_id] = branch_id
        self._update_overrides_label()

    def _on_reset(self) -> None:
        self._overrides.clear()
        self._update_overrides_label()

    def _on_recalculate(self) -> None:
        sample = self._input_sample()
        if sample is None:
            return
        from src.core.calculator import Calculator
        from src.core.models import CalculationConfig

        base = getattr(self._calculator, "config", None)
        if base is not None:
            config = replace(base, calculation_engine="excel_parity",
                             branch_overrides=dict(self._overrides))
        else:
            config = CalculationConfig(calculation_engine="excel_parity",
                                       branch_overrides=dict(self._overrides))
        try:
            result = Calculator(config=config).calculate_single(sample)
        except Exception as exc:  # noqa: BLE001 - показать пользователю
            QMessageBox.critical(self, "Ошибка пересчёта", str(exc))
            return
        self._current_result = result
        self._refresh()

    def _on_export_json(self) -> None:
        if self._current_result is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт маршрута веток", "branch_path.json", "JSON (*.json)")
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(branch_path_json(self._current_result.branch_path))
        except OSError as exc:
            QMessageBox.critical(self, "Ошибка экспорта", str(exc))
            return
        QMessageBox.information(self, "Готово", f"Маршрут сохранён:\n{path}")

    def _on_compare(self) -> None:
        index = self._sample_combo.currentIndex()
        if index < 0 or index >= len(self._results) or self._current_result is None:
            return
        auto = self._results[index]
        diff = diff_branch_paths(auto.branch_path, self._current_result.branch_path)
        if not diff:
            QMessageBox.information(
                self, "Сравнение маршрутов",
                "Маршруты совпадают (override не меняет маршрут для этого образца).")
            return
        lines = ["Различия маршрутов (авто → принудительный):", ""]
        for item in diff:
            who = "авто" if item["present_in"] == "a" else "принудительный"
            lines.append(f"  {item['stage']}: {item['name']}  (только {who})")
        QMessageBox.information(self, "Сравнение маршрутов", "\n".join(lines))
