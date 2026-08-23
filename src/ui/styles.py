"""Estilos globales para BioStat — tema 'Clinico Clasico'.

Aspecto de aplicacion de escritorio Windows clasica, al modo de MedCalc: gris
de sistema, densidad alta, bordes finos de 1 px, radios casi nulos y
tipografia chica. La idea no es que sea bonito de mirar en una captura sino que
entre mucha informacion en pantalla y se lea rapido — que es como se trabaja
con una planilla de resultados al lado del analizador.

Reemplaza al tema 'Clinical Fresh' (superficie blanca sobre slate, acento teal,
radios de 6-10 px, tipografia holgada), que ocupaba mucho alto por control.

Tokens:
  bg        #f0f0f0   fondo de ventana (gris de sistema)
  surface   #ffffff   areas de contenido (tablas, informes, campos)
  border    #a0a0a0   borde marcado (campos, tablas)
  border-   #d4d0c8   borde suave (separadores, marcos de grupo)
  ink       #1a1a1a   texto principal
  muted     #606060   texto secundario
  primary   #0e7490   acento teal (encabezados, seleccion de pestana)
  select    #cce4f7   fondo de seleccion (azul Windows)
  select-b  #7da2ce   borde de seleccion
"""

MAIN_STYLE = """
* { font-family: 'Segoe UI', 'Tahoma', sans-serif; font-size: 12px; }

QMainWindow, QDialog { background-color: #f0f0f0; }
QWidget { color: #1a1a1a; }

/* ---------- Menu ---------- */
QMenuBar {
    background-color: #f0f0f0;
    border-bottom: 1px solid #d4d0c8;
    padding: 0px;
}
QMenuBar::item { padding: 4px 10px; background: transparent; }
QMenuBar::item:selected { background-color: #cce4f7; }
QMenuBar::item:pressed { background-color: #b8d9f5; }

QMenu {
    background-color: #ffffff;
    border: 1px solid #a0a0a0;
    padding: 2px;
}
QMenu::item { padding: 4px 26px 4px 22px; }
QMenu::item:selected { background-color: #cce4f7; }
QMenu::item:disabled { color: #a0a0a0; }
QMenu::separator { height: 1px; background: #d4d0c8; margin: 3px 2px; }
QMenu::right-arrow { width: 10px; height: 10px; }

/* ---------- Toolbar ---------- */
QToolBar {
    background-color: #f0f0f0;
    border-bottom: 1px solid #d4d0c8;
    padding: 1px;
    spacing: 1px;
}
QToolBar::separator { width: 1px; background: #d4d0c8; margin: 2px 4px; }
QToolBar QToolButton {
    padding: 3px 6px;
    border: 1px solid transparent;
    background: transparent;
}
QToolBar QToolButton:hover { background-color: #e3effa; border-color: #7da2ce; }
QToolBar QToolButton:pressed { background-color: #cce4f7; border-color: #7da2ce; }

/* ---------- Barra de estado ---------- */
QStatusBar {
    background-color: #f0f0f0;
    border-top: 1px solid #d4d0c8;
    color: #404040;
}
QStatusBar::item { border: none; }

/* ---------- Pestanas ---------- */
QTabWidget::pane { border: 1px solid #a0a0a0; background-color: #f0f0f0; top: -1px; }
QTabBar { background-color: #f0f0f0; }
QTabBar::tab {
    background-color: #e4e4e4;
    border: 1px solid #a0a0a0;
    border-bottom: none;
    padding: 3px 12px;
    margin-right: 1px;
    color: #404040;
}
QTabBar::tab:selected { background-color: #f0f0f0; color: #0e7490; font-weight: 600; }
QTabBar::tab:hover:!selected { background-color: #eef4fa; }

/* ---------- Botones ---------- */
QPushButton {
    background-color: #e8e8e8;
    border: 1px solid #a0a0a0;
    border-radius: 2px;
    padding: 3px 12px;
    min-height: 18px;
    color: #1a1a1a;
}
QPushButton:hover { background-color: #e3effa; border-color: #7da2ce; }
QPushButton:pressed { background-color: #cce4f7; }
QPushButton:default { border: 1px solid #0e7490; font-weight: 600; }
QPushButton:disabled { background-color: #f0f0f0; color: #a0a0a0; border-color: #d4d0c8; }

QPushButton#secondary { background-color: #f0f0f0; }
QPushButton#danger { background-color: #f5e0e0; border-color: #c08080; }
QPushButton#danger:hover { background-color: #f0c8c8; }

/* ---------- Campos ---------- */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #ffffff;
    border: 1px solid #a0a0a0;
    border-radius: 0px;
    padding: 2px 4px;
    min-height: 18px;
    selection-background-color: #cce4f7;
    selection-color: #1a1a1a;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #0e7490;
}
QLineEdit:disabled, QComboBox:disabled { background-color: #f0f0f0; color: #808080; }
QComboBox { min-width: 90px; }
QComboBox::drop-down {
    border-left: 1px solid #a0a0a0;
    background-color: #e8e8e8;
    width: 16px;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #a0a0a0;
    selection-background-color: #cce4f7;
    selection-color: #1a1a1a;
}

/* ---------- Marcos de grupo ---------- */
QGroupBox {
    background-color: #f0f0f0;
    border: 1px solid #d4d0c8;
    border-radius: 0px;
    margin-top: 8px;
    padding-top: 6px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 6px;
    padding: 0 3px;
    color: #404040;
    font-weight: 600;
}

/* ---------- Planilla de datos ---------- */
QTableWidget, QTableView {
    background-color: #ffffff;
    alternate-background-color: #f7f9fb;
    border: 1px solid #a0a0a0;
    gridline-color: #d4d0c8;
    selection-background-color: #cce4f7;
    selection-color: #1a1a1a;
}
QTableWidget::item, QTableView::item { padding: 1px 3px; border: none; }

QHeaderView { background-color: #e8e8e8; }
QHeaderView::section {
    background-color: #e8e8e8;
    border: none;
    border-right: 1px solid #a0a0a0;
    border-bottom: 1px solid #a0a0a0;
    padding: 2px 5px;
    color: #303030;
    font-weight: 600;
}
QHeaderView::section:checked { background-color: #cce4f7; }
QTableCornerButton::section { background-color: #e8e8e8; border: 1px solid #a0a0a0; }

/* ---------- Texto e informes ---------- */
QTextEdit, QPlainTextEdit {
    background-color: #ffffff;
    border: 1px solid #a0a0a0;
    border-radius: 0px;
    padding: 4px;
    selection-background-color: #cce4f7;
    selection-color: #1a1a1a;
}

/* ---------- Barras y divisores ---------- */
QScrollBar:vertical { background: #f0f0f0; width: 14px; margin: 0; }
QScrollBar:horizontal { background: #f0f0f0; height: 14px; margin: 0; }
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #c8c8c8;
    border: 1px solid #a0a0a0;
    min-height: 20px;
    min-width: 20px;
}
QScrollBar::handle:hover { background: #b0b0b0; }
QScrollBar::add-line, QScrollBar::sub-line { background: #e8e8e8; border: 1px solid #a0a0a0; }
QScrollBar::add-page, QScrollBar::sub-page { background: #f0f0f0; }

QSplitter::handle { background-color: #d4d0c8; }
QSplitter::handle:horizontal { width: 3px; }
QSplitter::handle:vertical { height: 3px; }

QScrollArea { border: 1px solid #a0a0a0; background-color: #ffffff; }

/* ---------- Etiquetas con papel propio ---------- */
QLabel#subtitle { color: #606060; }
QLabel#tituloDialogo { font-size: 13px; font-weight: 700; color: #0e7490; }
QLabel#ayudaDialogo { color: #505050; }
QLabel#vistaPrevia {
    border: 1px solid #d4d0c8;
    background-color: #ffffff;
}
QLabel#pieVistaPrevia { color: #606060; font-size: 11px; }
/* Pie de un selector de opcion de metodo: explica que cambia al elegir. */
QLabel#ayudaOpcion { color: #606060; font-size: 11px; padding: 0 0 4px 0; }
QLabel#avisoDialogo {
    color: #7a5300;
    background-color: #fdf6e3;
    border: 1px solid #e0c8a0;
    padding: 4px 6px;
}
QToolTip {
    background-color: #ffffe1;
    color: #1a1a1a;
    border: 1px solid #767676;
    padding: 2px 4px;
}
"""
