"""Estilos globales para BioStat — Tema 'Clinical Fresh'.

Refresco visual cohesivo con tokens consistentes: superficie blanca sobre
fondo slate, acento teal clínico, radios y estados (hover/focus/disabled)
uniformes y una escala tipográfica clara. Pensado para lectura prolongada de
tablas y resultados en laboratorio.

Tokens:
  bg        #eef2f6   fondo app (slate-100)
  surface   #ffffff   tarjetas/paneles
  border    #e2e8f0   bordes suaves (slate-200)
  ink       #1e293b   texto principal (slate-800)
  muted     #64748b   texto secundario (slate-500)
  primary   #0e7490   acento teal (cyan-700)
  primary+  #0f8aa3   hover
  primary-  #0b5566   pressed
  danger    #dc2626   destructivo
"""

MAIN_STYLE = """
* { font-family: 'Segoe UI', 'Inter', 'Roboto', sans-serif; }

QMainWindow { background-color: #eef2f6; }

/* ---------- Menu ---------- */
QMenuBar {
    background-color: #ffffff;
    border-bottom: 1px solid #e2e8f0;
    padding: 3px 8px;
    font-size: 13px;
    color: #334155;
}
QMenuBar::item { padding: 6px 14px; border-radius: 6px; margin: 1px 2px; }
QMenuBar::item:selected { background-color: #e0f2f1; color: #0e7490; }

QMenu { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 5px; }
QMenu::item { padding: 7px 28px; border-radius: 6px; color: #334155; }
QMenu::item:selected { background-color: #e0f2f1; color: #0e7490; }
QMenu::separator { height: 1px; background: #e2e8f0; margin: 4px 8px; }

/* ---------- Toolbar ---------- */
QToolBar {
    background-color: #ffffff;
    border-bottom: 1px solid #e2e8f0;
    spacing: 4px;
    padding: 5px 8px;
}
QToolBar::separator { width: 1px; background: #e2e8f0; margin: 4px 6px; }
QToolBar QToolButton {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 7px;
    padding: 6px 12px;
    color: #334155;
    font-size: 12px;
    font-weight: 500;
}
QToolBar QToolButton:hover { background-color: #e0f2f1; color: #0e7490; border-color: #cdeceb; }
QToolBar QToolButton:pressed { background-color: #cdeceb; }

/* ---------- Status bar ---------- */
QStatusBar { background-color: #ffffff; border-top: 1px solid #e2e8f0; color: #64748b; font-size: 12px; }
QStatusBar::item { border: none; }

/* ---------- Pestanas ---------- */
QTabWidget::pane { border: none; background-color: #eef2f6; }
QTabBar { background-color: #ffffff; border-bottom: 1px solid #e2e8f0; }
QTabBar::tab {
    background-color: transparent;
    border: none;
    padding: 12px 22px;
    margin-right: 2px;
    color: #64748b;
    font-size: 13px;
    font-weight: 600;
    border-bottom: 2.5px solid transparent;
}
QTabBar::tab:selected { color: #0e7490; border-bottom: 2.5px solid #0e7490; }
QTabBar::tab:hover:!selected { color: #334155; background-color: #f1f5f9; }

/* ---------- Botones ---------- */
QPushButton {
    background-color: #0e7490;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton:hover { background-color: #0f8aa3; }
QPushButton:pressed { background-color: #0b5566; }
QPushButton:disabled { background-color: #cbd5e1; color: #94a3b8; }

QPushButton#secondary { background-color: #eef2f6; color: #334155; border: 1px solid #e2e8f0; }
QPushButton#secondary:hover { background-color: #e2e8f0; }
QPushButton#secondary:pressed { background-color: #cbd5e1; }

QPushButton#danger { background-color: #dc2626; }
QPushButton#danger:hover { background-color: #b91c1c; }
QPushButton#danger:pressed { background-color: #991b1b; }

/* ---------- Entradas ---------- */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    border: 1.5px solid #cbd5e1;
    border-radius: 8px;
    padding: 7px 10px;
    font-size: 13px;
    color: #1e293b;
    background-color: #ffffff;
    selection-background-color: #99e0e6;
    selection-color: #0b5566;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus { border: 1.5px solid #0e7490; }
QLineEdit:hover, QComboBox:hover { border-color: #94a3b8; }
QComboBox { min-width: 100px; }
QComboBox::drop-down { border: none; width: 26px; }
QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #64748b;
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    background-color: #ffffff;
    selection-background-color: #e0f2f1;
    selection-color: #0e7490;
    padding: 4px;
    outline: none;
}

/* ---------- GroupBox (tarjetas) ---------- */
QGroupBox {
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    margin-top: 12px;
    padding: 16px 12px 12px 12px;
    background-color: #ffffff;
    font-weight: 600;
    color: #334155;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 2px 8px;
    color: #0e7490;
    font-size: 12px;
    font-weight: 700;
}

/* ---------- Tablas ---------- */
QTableWidget {
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    background-color: #ffffff;
    gridline-color: #f1f5f9;
    font-size: 13px;
    color: #1e293b;
    selection-background-color: #e0f2f1;
    selection-color: #0b5566;
    alternate-background-color: #f8fafc;
}
QTableWidget::item { padding: 6px 8px; border-bottom: 1px solid #f1f5f9; }
QTableWidget::item:selected { background-color: #e0f2f1; }
QHeaderView::section {
    background-color: #f1f5f9;
    border: none;
    border-bottom: 2px solid #e2e8f0;
    padding: 9px 10px;
    font-weight: 700;
    color: #475569;
    font-size: 12px;
}
QTableCornerButton::section { background-color: #f1f5f9; border: none; }

/* ---------- Scrollbars ---------- */
QScrollBar:vertical { background-color: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background-color: #cbd5e1; border-radius: 5px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background-color: #94a3b8; }
QScrollBar:horizontal { background-color: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background-color: #cbd5e1; border-radius: 5px; min-width: 30px; }
QScrollBar::handle:horizontal:hover { background-color: #94a3b8; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0px; width: 0px; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

/* ---------- Texto / resultados ---------- */
QTextEdit {
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    background-color: #ffffff;
    font-size: 13px;
    color: #1e293b;
    padding: 10px;
    selection-background-color: #99e0e6;
}

/* ---------- Labels ---------- */
QLabel { color: #1e293b; font-size: 13px; }
QLabel#title { font-size: 18px; font-weight: 800; color: #0f172a; }
QLabel#subtitle { font-size: 12px; color: #64748b; }

QSplitter::handle { background-color: #e2e8f0; }
QSplitter::handle:horizontal { width: 2px; }
QSplitter::handle:vertical { height: 2px; }
QToolTip {
    background-color: #1e293b; color: #f8fafc; border: none;
    border-radius: 6px; padding: 6px 9px; font-size: 12px;
}
"""
