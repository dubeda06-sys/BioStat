"""Estilos globales para BioStat — tema 'Clinico Clasico', versión 2.

Sigue siendo denso, al modo de MedCalc: tipografía de 12 px, controles bajos,
mucha información por pantalla, que es como se trabaja con la planilla al lado
del analizador. Lo que cambió (27 sep, tanda 2 de la interfaz) es la terminación:

- bordes suaves en vez del gris marcado de 1 px en todo;
- los recuadros son tarjetas blancas con el título en el color de acento, en
  vez de marcos grises con el título indentado a fuerza de espacios;
- pestañas planas con la elegida subrayada, botón principal con relleno;
- selección en el tono del acento, no el azul de Windows;
- barras de desplazamiento finas, sin flechas;
- los combos vuelven a tener flecha: la regla de `::drop-down` la borraba y
  quedaba un recuadro gris vacío. La hoja de estilos solo acepta la flecha
  como imagen (el triángulo hecho con bordes, en Qt 6, sale como una barrita),
  así que se dibuja al importar este módulo en un PNG temporal: no hay que
  buscar archivos adentro del .exe.

El informe (`src/resultado/render_html.py`) usa el mismo acento y los mismos
grises.

Tokens:
  bg        #f2f4f7   fondo de ventana
  surface   #ffffff   tarjetas, tablas, informes, campos
  line      #dde2e8   borde suave (tarjetas, separadores, grilla)
  field     #c3cad3   borde de campos y botones
  ink       #1b2430   texto principal
  muted     #5b6573   texto secundario
  primary   #0e7490   acento teal (títulos, pestaña elegida, foco, botón principal)
  primary-  #0b5f76   acento al pasar el mouse
  soft      #e4f1f5   fondo de selección y de hover
"""
import os
import tempfile


def _flecha(color):
    """Ruta a una flechita PNG de ese color (el doble de tamaño, para pantallas
    con escala). QImage dibuja sin que exista la aplicación. "" si no se pudo:
    el combo queda sin flecha, como antes, pero la app arranca igual."""
    try:
        from PyQt6.QtCore import QPointF, Qt
        from PyQt6.QtGui import QColor, QImage, QPainter, QPolygonF
        img = QImage(20, 12, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        pintor = QPainter(img)
        pintor.setRenderHint(QPainter.RenderHint.Antialiasing)
        pintor.setPen(Qt.PenStyle.NoPen)
        pintor.setBrush(QColor(color))
        pintor.drawPolygon(QPolygonF([QPointF(2, 2), QPointF(18, 2), QPointF(10, 10)]))
        pintor.end()
        ruta = os.path.join(tempfile.gettempdir(), f"biostat_flecha_{color.lstrip('#')}.png")
        return ruta.replace("\\", "/") if img.save(ruta) else ""
    except Exception:  # noqa: BLE001 — un adorno no puede impedir que arranque
        return ""


def _regla_flecha():
    normal, apagada = _flecha("#5b6573"), _flecha("#a3abb5")
    if not normal:
        return ""
    return (f'QComboBox::down-arrow {{ image: url("{normal}"); width: 10px; height: 6px; }}\n'
            f'QComboBox::down-arrow:disabled {{ image: url("{apagada or normal}"); }}')


_PLANTILLA = """
* { font-family: 'Segoe UI', 'Tahoma', sans-serif; font-size: 12px; }

QMainWindow, QDialog { background-color: #f2f4f7; }
QWidget { color: #1b2430; }

/* ---------- Menú ---------- */
QMenuBar {
    background-color: #f2f4f7;
    border-bottom: 1px solid #dde2e8;
    padding: 1px 2px;
}
QMenuBar::item { padding: 4px 10px; background: transparent; border-radius: 3px; }
QMenuBar::item:selected { background-color: #e4f1f5; }
QMenuBar::item:pressed { background-color: #d3e8ef; }

QMenu {
    background-color: #ffffff;
    border: 1px solid #c3cad3;
    padding: 3px;
}
QMenu::item { padding: 4px 26px 4px 22px; border-radius: 3px; }
QMenu::item:selected { background-color: #e4f1f5; color: #1b2430; }
QMenu::item:disabled { color: #a3abb5; }
QMenu::separator { height: 1px; background: #dde2e8; margin: 3px 4px; }
QMenu::right-arrow { width: 10px; height: 10px; }

/* ---------- Barra de herramientas ---------- */
QToolBar {
    background-color: #f2f4f7;
    border-bottom: 1px solid #dde2e8;
    padding: 2px;
    spacing: 2px;
}
QToolBar::separator { width: 1px; background: #dde2e8; margin: 3px 5px; }
QToolBar QToolButton {
    padding: 3px 6px;
    border: 1px solid transparent;
    border-radius: 4px;
    background: transparent;
}
QToolBar QToolButton:hover { background-color: #e4f1f5; }
QToolBar QToolButton:pressed { background-color: #d3e8ef; }

/* ---------- Barra de estado ---------- */
QStatusBar {
    background-color: #f2f4f7;
    border-top: 1px solid #dde2e8;
    color: #5b6573;
}
QStatusBar::item { border: none; }

/* ---------- Pestañas: planas, la elegida subrayada ---------- */
QTabWidget::pane { border: none; border-top: 1px solid #dde2e8; background-color: #f2f4f7; }
QTabBar { background-color: #f2f4f7; }
QTabBar::tab {
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 5px 14px;
    margin-right: 2px;
    color: #5b6573;
}
QTabBar::tab:selected { color: #0e7490; border-bottom: 2px solid #0e7490; font-weight: 600; }
QTabBar::tab:hover:!selected { color: #1b2430; background-color: #e9edf1; }

/* ---------- Botones ---------- */
QPushButton {
    background-color: #ffffff;
    border: 1px solid #c3cad3;
    border-radius: 4px;
    padding: 4px 12px;
    min-height: 18px;
    color: #1b2430;
}
QPushButton:hover { background-color: #f3f9fb; border-color: #8fb9c6; }
QPushButton:pressed { background-color: #e4f1f5; }
QPushButton:disabled { background-color: #f2f4f7; color: #a3abb5; border-color: #dde2e8; }

/* El principal de cada pantalla (Ejecutar, Aceptar): con relleno. */
QPushButton#primario, QPushButton:default {
    background-color: #0e7490;
    border: 1px solid #0e7490;
    color: #ffffff;
    font-weight: 600;
}
QPushButton#primario:hover, QPushButton:default:hover { background-color: #0b5f76; border-color: #0b5f76; }
QPushButton#primario:pressed, QPushButton:default:pressed { background-color: #094d60; }

QPushButton#primario:disabled { background-color: #b9c7cd; border-color: #b9c7cd; color: #ffffff; }

QPushButton#secondary { background-color: #ffffff; }
QPushButton#danger { color: #b42318; border-color: #e6b8b3; }
QPushButton#danger:hover { background-color: #fdf1f0; border-color: #d98c84; }

/* ---------- Campos ---------- */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #ffffff;
    border: 1px solid #c3cad3;
    border-radius: 3px;
    padding: 2px 6px;
    min-height: 18px;
    selection-background-color: #cfe7ee;
    selection-color: #1b2430;
}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover { border-color: #9aa5b1; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #0e7490;
}
QLineEdit:disabled, QComboBox:disabled { background-color: #f2f4f7; color: #8a939e; }
QComboBox { min-width: 90px; padding-right: 20px; }
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 18px;
    border: none;
    background: transparent;
}
@FLECHA@
QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #c3cad3;
    selection-background-color: #e4f1f5;
    selection-color: #1b2430;
    outline: none;
}

/* ---------- Listas ---------- */
QListWidget {
    background-color: #ffffff;
    border: 1px solid #dde2e8;
    border-radius: 4px;
    outline: none;
}
/* Alto fijo: el estilo nativo de Windows 11 hace renglones de 30 px. */
QListWidget::item { height: 22px; padding: 0 4px; }
QListWidget::item:selected { background-color: #cfe7ee; color: #1b2430; }
QListWidget::item:hover:!selected { background-color: #f3f9fb; }

/* ---------- Recuadros: tarjeta blanca, título en el acento ---------- */
QGroupBox {
    background-color: #ffffff;
    border: 1px solid #dde2e8;
    border-radius: 6px;
    margin-top: 16px;
    padding: 8px 6px 6px 6px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 4px;
    padding: 0 2px;
    color: #0e7490;
    font-weight: 600;
}
QGroupBox:disabled { background-color: #f7f8fa; }
QGroupBox::title:disabled { color: #8a939e; }

/* ---------- Planilla de datos ---------- */
QTableWidget, QTableView {
    background-color: #ffffff;
    alternate-background-color: #f7f9fb;
    border: 1px solid #dde2e8;
    gridline-color: #e6e9ee;
    selection-background-color: #cfe7ee;
    selection-color: #1b2430;
}
QTableWidget::item, QTableView::item { padding: 1px 4px; border: none; }

QHeaderView { background-color: #f5f7f9; }
QHeaderView::section {
    background-color: #f5f7f9;
    border: none;
    border-right: 1px solid #e3e7ec;
    border-bottom: 1px solid #c9d0d8;
    padding: 3px 6px;
    color: #2c3642;
    font-weight: 600;
}
QHeaderView::section:checked { background-color: #e4f1f5; color: #0e7490; }
QTableCornerButton::section { background-color: #f5f7f9; border: none;
    border-right: 1px solid #e3e7ec; border-bottom: 1px solid #c9d0d8; }

/* ---------- Texto e informes ---------- */
QTextEdit, QPlainTextEdit {
    background-color: #ffffff;
    border: 1px solid #dde2e8;
    border-radius: 4px;
    padding: 4px;
    selection-background-color: #cfe7ee;
    selection-color: #1b2430;
}

/* ---------- Barras de desplazamiento finas, sin flechas ---------- */
QScrollBar:vertical { background: transparent; width: 10px; margin: 0; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 0; }
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #c5ccd4;
    border-radius: 4px;
    margin: 2px;
    min-height: 24px;
    min-width: 24px;
}
QScrollBar::handle:hover { background: #a3adb8; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0px; height: 0px; border: none; background: none; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }

QSplitter::handle { background-color: #f2f4f7; }
QSplitter::handle:horizontal { width: 5px; }
QSplitter::handle:vertical { height: 5px; }
QSplitter::handle:hover { background-color: #d3e8ef; }

QScrollArea { border: 1px solid #dde2e8; background-color: #ffffff; }

/* ---------- Etiquetas con papel propio ---------- */
QLabel#subtitle { color: #5b6573; }
QLabel#tituloDialogo { font-size: 14px; font-weight: 700; color: #0e7490; }
QLabel#ayudaDialogo { color: #4a5563; }
QLabel#vistaPrevia {
    border: 1px solid #dde2e8;
    border-radius: 4px;
    background-color: #ffffff;
}
QLabel#pieVistaPrevia { color: #5b6573; font-size: 11px; }
/* Pie de un selector de opción de método: explica qué cambia al elegir. */
QLabel#ayudaOpcion { color: #5b6573; font-size: 11px; padding: 0 0 4px 0; }
QLabel#avisoDialogo {
    color: #7a4a00;
    background-color: #fdf6e7;
    border: 1px solid #efd9ad;
    border-radius: 4px;
    padding: 5px 8px;
}
QToolTip {
    background-color: #ffffff;
    color: #1b2430;
    border: 1px solid #c3cad3;
    padding: 4px 6px;
}
"""

MAIN_STYLE = _PLANTILLA.replace("@FLECHA@", _regla_flecha())
