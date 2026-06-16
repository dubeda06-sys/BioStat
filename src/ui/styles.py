"""Estilos globales para BioStat - Tema limpio y moderno."""

MAIN_STYLE = """
QMainWindow {
    background-color: #f7f8fc;
    padding: 0px;
    margin: 0px;
}

QMenuBar {
    background-color: #ffffff;
    border-bottom: 1px solid #e8eaf0;
    padding: 2px 8px;
    font-size: 13px;
    color: #344055;
}

QMenuBar::item {
    padding: 6px 12px;
    border-radius: 5px;
    margin: 1px 2px;
}

QMenuBar::item:selected {
    background-color: #eef2ff;
    color: #4f6ef7;
}

QMenu {
    background-color: #ffffff;
    border: 1px solid #e8eaf0;
    border-radius: 8px;
    padding: 4px;
}

QMenu::item {
    padding: 7px 28px;
    border-radius: 4px;
    color: #344055;
}

QMenu::item:selected {
    background-color: #eef2ff;
    color: #4f6ef7;
}

QToolBar {
    background-color: #ffffff;
    border-bottom: 1px solid #e8eaf0;
    spacing: 4px;
    padding: 4px 8px;
}

QToolBar QToolButton {
    background-color: transparent;
    border: none;
    border-radius: 5px;
    padding: 6px 12px;
    color: #344055;
    font-size: 12px;
}

QToolBar QToolButton:hover {
    background-color: #eef2ff;
    color: #4f6ef7;
}

QStatusBar {
    background-color: #ffffff;
    border-top: 1px solid #e8eaf0;
    color: #8892a4;
    font-size: 12px;
}

QTabWidget::pane {
    border: none;
    background-color: #f7f8fc;
    padding: 0px;
    margin: 0px;
}

QTabWidget {
    padding: 0px;
    margin: 0px;
}

QTabBar {
    background-color: #ffffff;
    border-bottom: 2px solid #e8eaf0;
}

QTabBar::tab {
    background-color: transparent;
    border: none;
    padding: 11px 20px;
    margin-right: 1px;
    color: #8892a4;
    font-size: 13px;
    font-weight: 500;
    border-bottom: 2px solid transparent;
}

QTabBar::tab:selected {
    color: #4f6ef7;
    border-bottom: 2px solid #4f6ef7;
}

QTabBar::tab:hover {
    color: #344055;
    background-color: #f9fafd;
}

QPushButton {
    background-color: #4f6ef7;
    color: white;
    border: none;
    border-radius: 7px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #6380ff;
}

QPushButton:pressed {
    background-color: #3d57d9;
}

QPushButton:disabled {
    background-color: #d1d5e0;
    color: #a0a8b8;
}

QPushButton#secondary {
    background-color: #eef1f8;
    color: #344055;
}

QPushButton#secondary:hover {
    background-color: #dde3f2;
}

QPushButton#danger {
    background-color: #f04e5e;
}

QPushButton#danger:hover {
    background-color: #d93a4a;
}

QLineEdit {
    border: 1.5px solid #d8dbe3;
    border-radius: 7px;
    padding: 7px 10px;
    font-size: 13px;
    color: #344055;
    background-color: #ffffff;
    selection-background-color: #eef2ff;
}

QLineEdit:focus {
    border: 1.5px solid #4f6ef7;
}

QComboBox {
    border: 1.5px solid #d8dbe3;
    border-radius: 7px;
    padding: 7px 10px;
    font-size: 13px;
    color: #344055;
    background-color: #ffffff;
    min-width: 100px;
}

QComboBox:focus {
    border: 1.5px solid #4f6ef7;
}

QComboBox::drop-down {
    border: none;
    width: 28px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #8892a4;
    margin-right: 8px;
}

QComboBox QAbstractItemView {
    border: 1px solid #d8dbe3;
    border-radius: 7px;
    background-color: #ffffff;
    selection-background-color: #eef2ff;
    selection-color: #4f6ef7;
    padding: 3px;
}

QGroupBox {
    border: 1px solid #e8eaf0;
    border-radius: 9px;
    margin-top: 10px;
    padding: 14px 10px 10px 10px;
    background-color: #ffffff;
    font-weight: 500;
    color: #344055;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    color: #5a6478;
    font-size: 12px;
    font-weight: 600;
}

QTableWidget {
    border: 1px solid #e8eaf0;
    border-radius: 8px;
    background-color: #ffffff;
    gridline-color: #f0f2f7;
    font-size: 13px;
    color: #344055;
    selection-background-color: #eef2ff;
    selection-color: #4f6ef7;
}

QTableWidget::item {
    padding: 5px 8px;
    border-bottom: 1px solid #f5f6fa;
}

QTableWidget::item:selected {
    background-color: #eef2ff;
}

QHeaderView::section {
    background-color: #f5f7fb;
    border: none;
    border-bottom: 2px solid #e8eaf0;
    padding: 8px 10px;
    font-weight: 600;
    color: #5a6478;
    font-size: 12px;
}

QScrollBar:vertical {
    background-color: #f7f8fc;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background-color: #c8cdd8;
    border-radius: 4px;
    min-height: 28px;
}

QScrollBar::handle:vertical:hover {
    background-color: #a8b0c0;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #f7f8fc;
    height: 8px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal {
    background-color: #c8cdd8;
    border-radius: 4px;
    min-width: 28px;
}

QTextEdit {
    border: 1px solid #e8eaf0;
    border-radius: 8px;
    background-color: #ffffff;
    font-size: 13px;
    color: #344055;
    padding: 8px;
    font-family: 'Consolas', 'Courier New', monospace;
}

QLabel {
    color: #344055;
    font-size: 13px;
}

QLabel#title {
    font-size: 17px;
    font-weight: 700;
    color: #2c3650;
}

QLabel#subtitle {
    font-size: 12px;
    color: #8892a4;
}

QSpinBox, QDoubleSpinBox {
    border: 1.5px solid #d8dbe3;
    border-radius: 7px;
    padding: 7px 10px;
    font-size: 13px;
    color: #344055;
    background-color: #ffffff;
}

QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1.5px solid #4f6ef7;
}

QSplitter::handle {
    background-color: #e8eaf0;
    height: 2px;
    width: 2px;
}
"""
