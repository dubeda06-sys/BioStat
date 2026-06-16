"""Estilos globales para BioStat - Tema Clean Clinical."""

MAIN_STYLE = """
QMainWindow {
    background-color: #f3f5f9;
    padding: 0px;
    margin: 0px;
}

QMenuBar {
    background-color: #ffffff;
    border-bottom: 1px solid #dce1e8;
    padding: 2px 8px;
    font-size: 13px;
    color: #2c3e50;
    font-family: 'Segoe UI', 'Roboto', sans-serif;
}

QMenuBar::item {
    padding: 6px 14px;
    border-radius: 5px;
    margin: 1px 2px;
}

QMenuBar::item:selected {
    background-color: #e8eef6;
    color: #2b579a;
}

QMenu {
    background-color: #ffffff;
    border: 1px solid #dce1e8;
    border-radius: 8px;
    padding: 4px;
}

QMenu::item {
    padding: 7px 28px;
    border-radius: 4px;
    color: #2c3e50;
}

QMenu::item:selected {
    background-color: #e8eef6;
    color: #2b579a;
}

QToolBar {
    background-color: #ffffff;
    border-bottom: 1px solid #dce1e8;
    spacing: 4px;
    padding: 4px 8px;
}

QToolBar QToolButton {
    background-color: transparent;
    border: none;
    border-radius: 5px;
    padding: 6px 12px;
    color: #2c3e50;
    font-size: 12px;
    font-family: 'Segoe UI', 'Roboto', sans-serif;
}

QToolBar QToolButton:hover {
    background-color: #e8eef6;
    color: #2b579a;
}

QStatusBar {
    background-color: #ffffff;
    border-top: 1px solid #dce1e8;
    color: #7b8a9e;
    font-size: 12px;
}

QTabWidget::pane {
    border: none;
    background-color: #f3f5f9;
    padding: 0px;
    margin: 0px;
}

QTabWidget {
    padding: 0px;
    margin: 0px;
}

QTabBar {
    background-color: #ffffff;
    border-bottom: 2px solid #dce1e8;
}

QTabBar::tab {
    background-color: transparent;
    border: none;
    padding: 11px 20px;
    margin-right: 1px;
    color: #7b8a9e;
    font-size: 13px;
    font-weight: 500;
    border-bottom: 2px solid transparent;
    font-family: 'Segoe UI', 'Roboto', sans-serif;
}

QTabBar::tab:selected {
    color: #2b579a;
    border-bottom: 2px solid #2b579a;
}

QTabBar::tab:hover {
    color: #2c3e50;
    background-color: #f5f7fb;
}

QPushButton {
    background-color: #2b579a;
    color: white;
    border: none;
    border-radius: 7px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 500;
    font-family: 'Segoe UI', 'Roboto', sans-serif;
}

QPushButton:hover {
    background-color: #3567b0;
}

QPushButton:pressed {
    background-color: #1e3f73;
}

QPushButton:disabled {
    background-color: #c8ced8;
    color: #9aa5b4;
}

QPushButton#secondary {
    background-color: #e8eef6;
    color: #2c3e50;
}

QPushButton#secondary:hover {
    background-color: #d5dde9;
}

QPushButton#danger {
    background-color: #d94052;
}

QPushButton#danger:hover {
    background-color: #c23040;
}

QLineEdit {
    border: 1.5px solid #c8ced8;
    border-radius: 7px;
    padding: 7px 10px;
    font-size: 13px;
    color: #2c3e50;
    background-color: #ffffff;
    selection-background-color: #e8eef6;
    font-family: 'Segoe UI', 'Roboto', sans-serif;
}

QLineEdit:focus {
    border: 1.5px solid #2b579a;
}

QComboBox {
    border: 1.5px solid #c8ced8;
    border-radius: 7px;
    padding: 7px 10px;
    font-size: 13px;
    color: #2c3e50;
    background-color: #ffffff;
    min-width: 100px;
    font-family: 'Segoe UI', 'Roboto', sans-serif;
}

QComboBox:focus {
    border: 1.5px solid #2b579a;
}

QComboBox::drop-down {
    border: none;
    width: 28px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #7b8a9e;
    margin-right: 8px;
}

QComboBox QAbstractItemView {
    border: 1px solid #c8ced8;
    border-radius: 7px;
    background-color: #ffffff;
    selection-background-color: #e8eef6;
    selection-color: #2b579a;
    padding: 3px;
}

QGroupBox {
    border: 1px solid #dce1e8;
    border-radius: 9px;
    margin-top: 10px;
    padding: 14px 10px 10px 10px;
    background-color: #ffffff;
    font-weight: 500;
    color: #2c3e50;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    color: #4a5568;
    font-size: 12px;
    font-weight: 600;
}

QTableWidget {
    border: 1px solid #dce1e8;
    border-radius: 8px;
    background-color: #ffffff;
    gridline-color: #edf0f5;
    font-size: 13px;
    color: #2c3e50;
    selection-background-color: #e8eef6;
    selection-color: #2b579a;
}

QTableWidget::item {
    padding: 5px 8px;
    border-bottom: 1px solid #f2f4f8;
}

QTableWidget::item:selected {
    background-color: #e8eef6;
}

QHeaderView::section {
    background-color: #f0f3f8;
    border: none;
    border-bottom: 2px solid #dce1e8;
    padding: 8px 10px;
    font-weight: 600;
    color: #4a5568;
    font-size: 12px;
}

QScrollBar:vertical {
    background-color: #f3f5f9;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background-color: #bcc5d3;
    border-radius: 4px;
    min-height: 28px;
}

QScrollBar::handle:vertical:hover {
    background-color: #9aa5b4;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #f3f5f9;
    height: 8px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal {
    background-color: #bcc5d3;
    border-radius: 4px;
    min-width: 28px;
}

QTextEdit {
    border: 1px solid #dce1e8;
    border-radius: 8px;
    background-color: #ffffff;
    font-size: 13px;
    color: #2c3e50;
    padding: 8px;
    font-family: 'Consolas', 'Courier New', monospace;
}

QLabel {
    color: #2c3e50;
    font-size: 13px;
    font-family: 'Segoe UI', 'Roboto', sans-serif;
}

QLabel#title {
    font-size: 17px;
    font-weight: 700;
    color: #1a2744;
}

QLabel#subtitle {
    font-size: 12px;
    color: #7b8a9e;
}

QSpinBox, QDoubleSpinBox {
    border: 1.5px solid #c8ced8;
    border-radius: 7px;
    padding: 7px 10px;
    font-size: 13px;
    color: #2c3e50;
    background-color: #ffffff;
}

QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1.5px solid #2b579a;
}

QSplitter::handle {
    background-color: #dce1e8;
    height: 2px;
    width: 2px;
}
"""
