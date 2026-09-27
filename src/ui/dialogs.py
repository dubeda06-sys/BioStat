"""Cuadro de dialogo por analisis, al modo de MedCalc.

En MedCalc no hay un panel con selectores siempre a la vista: se elige el
procedimiento en el menu, se abre su dialogo, se eligen las variables y recien
ahi sale el informe. Este es ese dialogo.

Muestra solo lo que el analisis usa de verdad — la ficha esta en
`src/ui/analysis_specs.py` — y avisa cuando el analisis trabaja sobre toda la
hoja en vez de sobre columnas sueltas.
"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout,
)

from src.ui import previews
from src.ui.analysis_specs import (
    multi, opciones, parametros, sobre_toda_la_hoja, variables,
)
from src.ui.help_text import ANALYSIS_HELP

SIN_COLUMNA = "(ninguna)"


class DialogoAnalisis(QDialog):
    """Pide las variables de un analisis. `seleccion()` devuelve lo elegido."""

    def __init__(self, analisis, columnas, parent=None, alpha="0.05",
                 columnas_numericas=None):
        super().__init__(parent)
        self.analisis = analisis
        self.columnas = list(columnas)
        # La lista tildable solo ofrece columnas numericas; si quien abre el
        # dialogo no las distingue, se ofrecen todas.
        self.columnas_numericas = (list(columnas_numericas) if columnas_numericas is not None
                                   else list(columnas))
        self.setWindowTitle(analisis)
        self.setModal(True)
        self.setMinimumWidth(620)
        self._construir(alpha)

    def _construir(self, alpha):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        encabezado = QHBoxLayout()
        encabezado.setSpacing(10)

        texto = QVBoxLayout()
        texto.setSpacing(4)
        titulo = QLabel(self.analisis)
        titulo.setObjectName("tituloDialogo")
        texto.addWidget(titulo)

        ayuda = QLabel(ANALYSIS_HELP.get(self.analisis, ""))
        ayuda.setWordWrap(True)
        ayuda.setMinimumWidth(240)
        ayuda.setObjectName("ayudaDialogo")
        texto.addWidget(ayuda)
        texto.addStretch()
        encabezado.addLayout(texto, stretch=1)

        # Vista previa: la forma tipica de la salida, con datos de ejemplo.
        vista = QVBoxLayout()
        vista.setSpacing(2)
        imagen = QLabel()
        imagen.setPixmap(previews.pixmap(self.analisis))
        imagen.setObjectName("vistaPrevia")
        imagen.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vista.addWidget(imagen)

        pie = QLabel(previews.descripcion(self.analisis) + "\nDatos de ejemplo.")
        pie.setWordWrap(True)
        pie.setMaximumWidth(300)
        pie.setObjectName("pieVistaPrevia")
        vista.addWidget(pie)
        encabezado.addLayout(vista)

        layout.addLayout(encabezado)

        linea = QFrame()
        linea.setFrameShape(QFrame.Shape.HLine)
        linea.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(linea)

        form = QFormLayout()
        form.setSpacing(6)
        usa = variables(self.analisis)

        self.combo_col1 = self.combo_col2 = self.combo_col3 = None
        self.input_alpha = None

        if "c1" in usa:
            self.combo_col1 = self._combo()
            form.addRow("Variable 1:", self.combo_col1)
        if "c2" in usa:
            self.combo_col2 = self._combo(indice=1)
            form.addRow("Variable 2:", self.combo_col2)
        if "c3" in usa:
            self.combo_col3 = self._combo(opcional=True)
            form.addRow("Variable 3:", self.combo_col3)
        if "alpha" in usa:
            self.input_alpha = QLineEdit(alpha)
            self.input_alpha.setMaximumWidth(80)
            form.addRow("Alfa:", self.input_alpha)

        # Opciones de metodo: no son variables, son decisiones sobre COMO se
        # calcula. Van despues de las columnas porque se eligen despues.
        self.combos_opcion = {}
        for opcion in opciones(self.analisis):
            combo = QComboBox()
            for valor, texto in opcion.valores:
                combo.addItem(texto, valor)
            self.combos_opcion[opcion.clave] = combo
            form.addRow(f"{opcion.etiqueta}:", combo)
            if opcion.ayuda:
                pie = QLabel(opcion.ayuda)
                pie.setWordWrap(True)
                pie.setObjectName("ayudaOpcion")
                form.addRow("", pie)

        # Lista de columnas: se tildan las que entran. Arranca con todas las
        # numericas tildadas menos las ya elegidas como Variable 1, para que se
        # vea de entrada que entra y se pueda sacar lo que no corresponde (un ID,
        # una edad) antes de correr.
        self.lista_columnas = None
        spec_multi = multi(self.analisis)
        if spec_multi is not None:
            self.lista_columnas = QListWidget()
            self.lista_columnas.setMaximumHeight(150)
            elegida = self.combo_col1.currentText() if self.combo_col1 is not None else None
            for col in self.columnas_numericas:
                item = QListWidgetItem(col)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked if col == elegida
                                   else Qt.CheckState.Checked)
                self.lista_columnas.addItem(item)
            form.addRow(f"{spec_multi.etiqueta}:", self.lista_columnas)
            texto = f"Mínimo {spec_multi.minimo}. " + spec_multi.ayuda
            pie = QLabel(texto.strip())
            pie.setWordWrap(True)
            pie.setObjectName("ayudaOpcion")
            form.addRow("", pie)

        # Parametros numericos (tamano de muestra, poder).
        self.inputs_parametro = {}
        for par in parametros(self.analisis):
            campo = QLineEdit("" if par.defecto is None else f"{par.defecto:g}")
            campo.setMaximumWidth(120)
            self.inputs_parametro[par.clave] = campo
            form.addRow(f"{par.etiqueta}:", campo)

        if sobre_toda_la_hoja(self.analisis):
            aviso = QLabel(
                "Este analisis toma la hoja completa: usa todas las columnas "
                "de datos tal como estan cargadas, sin elegir una en particular."
            )
            aviso.setWordWrap(True)
            aviso.setObjectName("avisoDialogo")
            form.addRow("", aviso)

        layout.addLayout(form)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            Qt.Orientation.Horizontal, self,
        )
        botones.button(QDialogButtonBox.StandardButton.Ok).setText("Aceptar")
        botones.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def _combo(self, indice=0, opcional=False):
        combo = QComboBox()
        if opcional:
            combo.addItem(SIN_COLUMNA)
        combo.addItems(self.columnas)
        if indice and combo.count() > indice:
            combo.setCurrentIndex(indice)
        return combo

    def seleccion(self):
        """Lo elegido, listo para volcar en AnalysisPanel."""
        def texto(combo, por_defecto=""):
            return combo.currentText() if combo is not None else por_defecto

        return {
            "c1": texto(self.combo_col1),
            "c2": texto(self.combo_col2),
            "c3": texto(self.combo_col3, SIN_COLUMNA),
            "alpha": self.input_alpha.text() if self.input_alpha else None,
            # currentData(), no currentText(): el texto es para leer, el valor
            # es el que entiende el analisis.
            "opciones": {clave: combo.currentData()
                         for clave, combo in self.combos_opcion.items()},
            # None = el analisis no usa lista; [] = usa lista y no se tildo nada.
            "columnas": (None if self.lista_columnas is None else
                         [self.lista_columnas.item(i).text()
                          for i in range(self.lista_columnas.count())
                          if self.lista_columnas.item(i).checkState() == Qt.CheckState.Checked]),
            # Texto crudo: el analisis lo valida y dice que esta mal si algo no
            # es un numero, en vez de que el dialogo lo trague en silencio.
            "parametros": {clave: campo.text() for clave, campo in self.inputs_parametro.items()},
        }
