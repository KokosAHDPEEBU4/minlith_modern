import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout,
                              QVBoxLayout, QListWidget, QListWidgetItem,
                              QStackedWidget, QLabel, QCheckBox, QSlider,
                              QComboBox, QLineEdit, QPushButton, QFrame,
                              QRadioButton, QButtonGroup, QSizePolicy)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QColor

QSS = """
QMainWindow { background: #f5f7fa; }
QListWidget {
    background: #ffffff;
    border: none;
    border-right: 1px solid #e5e7eb;
    font-size: 14px;
    outline: none;
}
QListWidget::item {
    padding: 12px 20px;
    border-left: 3px solid transparent;
    color: #6b7280;
}
QListWidget::item:selected {
    background: #f5f7fa;
    color: #3b82f6;
    border-left-color: #3b82f6;
    font-weight: bold;
}
QListWidget::item:hover { background: #f5f7fa; }
QLineEdit {
    padding: 8px 12px;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    background: white;
    font-size: 13px;
}
QPushButton {
    padding: 8px 16px;
    border-radius: 6px;
    font-size: 13px;
    border: 1px solid #e5e7eb;
    background: white;
}
QPushButton:hover { background: #f5f7fa; }
QPushButton#primary {
    background: #3b82f6;
    color: white;
    border: none;
}
QPushButton#primary:hover { background: #2563eb; }
QPushButton#danger { color: #ef4444; }
QFrame.card {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 16px;
}
QLabel.title { font-size: 15px; font-weight: bold; }
QLabel.subtitle { font-size: 12px; color: #6b7280; }
QComboBox {
    padding: 6px 10px;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    background: white;
    min-width: 150px;
}
/* Тоггл */
QCheckBox { spacing: 8px; }
QCheckBox::indicator {
    width: 40px; height: 22px;
    border-radius: 11px;
    background: #d1d5db;
    position: relative;
}
QCheckBox::indicator:checked { background: #3b82f6; }
QCheckBox::indicator:after {
    content: '';
    width: 18px; height: 18px;
    background: white;
    border-radius: 50%;
    position: absolute;
    top: 2px; left: 2px;
}
QCheckBox::indicator:checked:after { left: 20px; }
QSlider::groove:horizontal {
    height: 4px;
    background: #e5e7eb;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    width: 16px; height: 16px;
    background: #3b82f6;
    border-radius: 8px;
    margin: -6px 0;
}
"""

class SettingsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Настройки")
        self.resize(900, 600)
        self.setStyleSheet(QSS)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        sidebar = QWidget()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("background: white;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 20, 0, 0)

        title = QLabel("⚙️ Настройки")
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 0 20px 15px;")
        sidebar_layout.addWidget(title)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск...")
        self.search.setStyleSheet("margin: 0 16px 12px;")
        sidebar_layout.addWidget(self.search)

        self.nav = QListWidget()
        sections = ["Общие", "Внешний вид", "Уведомления", "Звук", "Аккаунт"]
        for s in sections:
            self.nav.addItem(QListWidgetItem(s))
        self.nav.setCurrentRow(0)
        sidebar_layout.addWidget(self.nav)

        main_layout.addWidget(sidebar)

        # Content
        content = QWidget()
        content.setStyleSheet("background: #f5f7fa;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(30, 30, 30, 30)

        # Topbar
        topbar = QHBoxLayout()
        self.page_title = QLabel("Общие")
        self.page_title.setStyleSheet("font-size: 22px; font-weight: bold;")
        topbar.addWidget(self.page_title)
        topbar.addStretch()

        reset_btn = QPushButton("Сбросить")
        save_btn = QPushButton("Сохранить")
        save_btn.setObjectName("primary")
        topbar.addWidget(reset_btn)
        topbar.addWidget(save_btn)
        content_layout.addLayout(topbar)

        # Stacked pages
        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack)

        self.stack.addWidget(self.make_general())
        self.stack.addWidget(self.make_appearance())
        self.stack.addWidget(self.make_notifications())
        self.stack.addWidget(self.make_audio())
        self.stack.addWidget(self.make_account())

        # Connections
        self.nav.currentRowChanged.connect(self.switch_page)
        save_btn.clicked.connect(lambda: self.toast("✓ Настройки сохранены"))
        reset_btn.clicked.connect(lambda: print("Reset"))

        # Toast label
        self.toast_label = QLabel("", self)
        self.toast_label.setStyleSheet("""
            background: #10b981; color: white; padding: 10px 18px;
            border-radius: 8px; font-size: 13px;
        """)
        self.toast_label.hide()

    def switch_page(self, idx):
        self.stack.setCurrentIndex(idx)
        self.page_title.setText(self.nav.item(idx).text())

    def make_row(self, label, widget, subtitle=None):
        row = QHBoxLayout()
        info = QVBoxLayout()
        lbl = QLabel(label)
        lbl.setStyleSheet("font-size: 14px;")
        info.addWidget(lbl)
        if subtitle:
            sub = QLabel(subtitle)
            sub.setStyleSheet("font-size: 12px; color: #6b7280;")
            info.addWidget(sub)
        info.addStretch()
        row.addLayout(info)
        row.addWidget(widget)
        return row

    def make_card(self, title, desc, rows_layout):
        card = QFrame()
        card.setProperty("class", "card")
        card.setStyleSheet("""
            background: white; border: 1px solid #e5e7eb;
            border-radius: 10px; padding: 16px;
        """)
        layout = QVBoxLayout(card)
        t = QLabel(title)
        t.setStyleSheet("font-size: 15px; font-weight: bold;")
        layout.addWidget(t)
        if desc:
            d = QLabel(desc)
            d.setStyleSheet("font-size: 12px; color: #6b7280; margin-bottom: 10px;")
            layout.addWidget(d)
        layout.addLayout(rows_layout)
        return card

    def make_general(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        rows = QVBoxLayout()
        rows.addLayout(self.make_row("Язык интерфейса", QComboBox(), "Выберите язык приложения"))
        combo = QComboBox()
        combo.addItems(["UTC+3 (Москва)", "UTC+5 (Екатеринбург)"])
        rows.addLayout(self.make_row("Часовой пояс", combo))
        rows.addLayout(self.make_row("Запускать при старте", QCheckBox()))
        rows.addLayout(self.make_row("Сворачивать в трей", QCheckBox()))

        layout.addWidget(self.make_card("Язык и регион", "Параметры локализации", rows))
        layout.addStretch()
        return page

    def make_appearance(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        rows = QVBoxLayout()
        rows.addLayout(self.make_row("Тёмная тема", QCheckBox()))

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(12, 20)
        slider.setValue(14)
        val_lbl = QLabel("14px")
        val_lbl.setStyleSheet("font-size: 13px; color: #6b7280; min-width: 40px;")
        slider.valueChanged.connect(lambda v: val_lbl.setText(f"{v}px"))
        slider_row = QHBoxLayout()
        slider_row.addWidget(QLabel("Размер шрифта"))
        slider_row.addStretch()
        slider_row.addWidget(slider)
        slider_row.addWidget(val_lbl)
        rows.addLayout(slider_row)

        layout.addWidget(self.make_card("Тема", "Настройка внешнего вида", rows))
        layout.addStretch()
        return page

    def make_notifications(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        rows = QVBoxLayout()
        rows.addLayout(self.make_row("Включить уведомления", QCheckBox()))
        rows.addLayout(self.make_row("Звук уведомлений", QCheckBox()))
        combo = QComboBox()
        combo.addItems(["Всегда", "Только активные", "Никогда"])
        rows.addLayout(self.make_row("Показывать баннеры", combo))
        rows.addLayout(self.make_row("Не беспокоить", QCheckBox()))

        layout.addWidget(self.make_card("Уведомления", "Оповещения приложения", rows))
        layout.addStretch()
        return page

    def make_audio(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        rows = QVBoxLayout()

        def make_slider_row(label, default):
            s = QSlider(Qt.Orientation.Horizontal)
            s.setRange(0, 100)
            s.setValue(default)
            v = QLabel(f"{default}%")
            v.setStyleSheet("font-size: 13px; color: #6b7280; min-width: 40px;")
            s.valueChanged.connect(lambda val: v.setText(f"{val}%"))
            r = QHBoxLayout()
            r.addWidget(QLabel(label))
            r.addStretch()
            r.addWidget(s)
            r.addWidget(v)
            return r

        rows.addLayout(make_slider_row("Общая громкость", 70))
        rows.addLayout(make_slider_row("Громкость уведомлений", 50))
        combo = QComboBox()
        combo.addItems(["По умолчанию", "Динамики", "Наушники"])
        rows.addLayout(self.make_row("Устройство вывода", combo))

        layout.addWidget(self.make_card("Звук", "Громкость и аудио", rows))
        layout.addStretch()
        return page

    def make_account(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        rows = QVBoxLayout()
        name = QLineEdit()
        name.setText("Kokos")
        rows.addLayout(self.make_row("Имя пользователя", name))
        email = QLineEdit()
        email.setText("kokos@example.com")
        rows.addLayout(self.make_row("Email", email))
        layout.addWidget(self.make_card("Профиль", "Информация об аккаунте", rows))

        danger = QVBoxLayout()
        del_btn = QPushButton("Удалить аккаунт")
        del_btn.setObjectName("danger")
        danger.addLayout(self.make_row("Удалить аккаунт", del_btn, "Все данные будут удалены"))
        layout.addWidget(self.make_card("Опасная зона", "Необратимые действия", danger))

        layout.addStretch()
        return page

    def toast(self, msg):
        self.toast_label.setText(msg)
        self.toast_label.adjustSize()
        self.toast_label.move(self.width() - self.toast_label.width() - 24,
                              self.height() - self.toast_label.height() - 24)
        self.toast_label.show()
        QTimer.singleShot(2200, self.toast_label.hide)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = SettingsWindow()
    w.show()
    sys.exit(app.exec())