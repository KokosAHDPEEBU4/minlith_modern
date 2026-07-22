"""Main application window for MINLITH Modern."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from src.gui.input_panel import InputPanel
from src.gui.results_table import ResultsTable
from src.core.calculator import Calculator
from src.core.models import Sample, OxideComposition


class MainWindow(QMainWindow):
    """Main window with input panel and results table."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MINLITH Modern — Normative Mineralogy")
        self.setMinimumSize(1200, 700)

        self.calculator = Calculator()

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: input
        self.input_panel = InputPanel()
        splitter.addWidget(self.input_panel)

        # Right: results
        self.results_table = ResultsTable()
        splitter.addWidget(self.results_table)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)

        # Buttons
        btn_row = QHBoxLayout()
        self.btn_calculate = QPushButton("  Calculate  ")
        self.btn_calculate.setStyleSheet(
            "QPushButton { font-weight: bold; padding: 8px 24px; }"
        )
        self.btn_calculate.clicked.connect(self._on_calculate)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_calculate)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Status bar
        self.statusBar().showMessage("Ready")

    def _on_calculate(self) -> None:
        """Run calculation on current input."""
        data = self.input_panel.get_composition()
        if data is None:
            QMessageBox.warning(self, "Input Error", "Please fill in at least SiO2.")
            return

        sample = Sample(name="Sample", composition=data)
        try:
            result = self.calculator.calculate_single(sample)
            self.results_table.set_result(result)
            self.statusBar().showMessage(
                f"Calculated: {result.rock_type.name}, "
                f"sum={sum(v for v in result.defect.values()):.1f}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Calculation Error", str(e))
