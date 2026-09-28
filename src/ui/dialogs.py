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
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QFrame, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QScrollArea, QVBoxLayout, QWidget,
)

from src.ui import previews
from src.ui.analysis_specs import (
    etiqueta, multi, opciones, parametros, secciones, sobre_toda_la_hoja, variables,
)
from src.ui.help_text import ANALYSIS_HELP
from src.ui.menus import nombre_visible

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
        self.setWindowTitle(nombre_visible(analisis))
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
        titulo = QLabel(nombre_visible(self.analisis))
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
            form.addRow(etiqueta(self.analisis, "c1", "Variable 1") + ":", self.combo_col1)
        if "c2" in usa:
            self.combo_col2 = self._combo(indice=1)
            form.addRow(etiqueta(self.analisis, "c2", "Variable 2") + ":", self.combo_col2)
        if "c3" in usa:
            self.combo_col3 = self._combo(opcional=True)
            form.addRow("Variable 3:", self.combo_col3)
        if "alpha" in usa:
            self.input_alpha = QLineEdit(alpha)
            self.input_alpha.setMaximumWidth(80)
            form.addRow("Alfa:", self.input_alpha)

        # Cada campo que no es una variable se arma como filas (rótulo, widget)
        # bajo su clave, y después se reparten: al formulario principal, o a su
        # sección si el análisis las tiene (analysis_specs.SECCIONES).
        filas = {}

        # Opciones de metodo: no son variables, son decisiones sobre COMO se
        # calcula. Van despues de las columnas porque se eligen despues.
        self.combos_opcion = {}
        for opcion in opciones(self.analisis):
            combo = QComboBox()
            for valor, texto in opcion.valores:
                combo.addItem(texto, valor)
            self.combos_opcion[opcion.clave] = combo
            filas[opcion.clave] = [(f"{opcion.etiqueta}:", combo)]
            if opcion.ayuda:
                filas[opcion.clave].append(("", self._pie(opcion.ayuda)))

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
                item.setCheckState(Qt.CheckState.Checked
                                   if spec_multi.tildadas and col != elegida
                                   else Qt.CheckState.Unchecked)
                self.lista_columnas.addItem(item)
            texto = ((f"Mínimo {spec_multi.minimo}. " if spec_multi.minimo else "Opcional. ")
                     + spec_multi.ayuda)
            filas["multi"] = [(f"{spec_multi.etiqueta}:", self.lista_columnas),
                              ("", self._pie(texto.strip()))]

        # Parametros numericos (tamano de muestra, poder).
        self.inputs_parametro = {}
        for par in parametros(self.analisis):
            campo = QLineEdit("" if par.defecto is None else f"{par.defecto:g}")
            campo.setMaximumWidth(120)
            self.inputs_parametro[par.clave] = campo
            filas[par.clave] = [(f"{par.etiqueta}:", campo)]

        # Las secciones: cada una un recuadro con su formulario. Las que piden
        # la lista tildada se apagan mientras no haya nada tildado.
        self.secciones = {}
        self._requieren_lista = []
        cajas = []
        for seccion in secciones(self.analisis):
            caja = QGroupBox(seccion.titulo)
            forma = QFormLayout(caja)
            forma.setSpacing(6)
            forma.setContentsMargins(8, 4, 8, 6)
            if seccion.ayuda:
                forma.addRow(self._pie(seccion.ayuda))
            for clave in seccion.claves:
                for rotulo, widget in filas.pop(clave, []):
                    forma.addRow(rotulo, widget)
            self.secciones[seccion.titulo] = caja
            if seccion.requiere_lista:
                self._requieren_lista.append(caja)
            cajas.append(caja)
        # Lo que no está en ninguna sección, al formulario principal, en orden.
        for filas_de_clave in filas.values():
            for rotulo, widget in filas_de_clave:
                form.addRow(rotulo, widget)

        if sobre_toda_la_hoja(self.analisis):
            aviso = QLabel(
                "Este análisis toma la hoja completa: usa todas las columnas "
                "de datos tal como están cargadas, sin elegir una en particular."
            )
            aviso.setWordWrap(True)
            aviso.setObjectName("avisoDialogo")
            form.addRow("", aviso)

        # Todo lo que se completa va en un área con desplazamiento: si no entra
        # en la pantalla, se desplaza y los botones quedan siempre a la vista.
        contenido = QWidget()
        cuerpo = QVBoxLayout(contenido)
        cuerpo.setContentsMargins(0, 0, 6, 0)
        cuerpo.setSpacing(8)
        cuerpo.addLayout(form)
        for caja in cajas:
            cuerpo.addWidget(caja)
        cuerpo.addStretch()
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setWidget(contenido)
        layout.addWidget(self._scroll, stretch=1)

        if self._requieren_lista and self.lista_columnas is not None:
            self.lista_columnas.itemChanged.connect(self._actualizar_secciones)
            self._actualizar_secciones()

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            Qt.Orientation.Horizontal, self,
        )
        botones.button(QDialogButtonBox.StandardButton.Ok).setText("Aceptar")
        botones.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)
        self._ajustar_alto(contenido)

    def _ajustar_alto(self, contenido):
        """Todo el contenido si entra; si no, el 90 % de la pantalla y el
        resto se desplaza."""
        from PyQt6.QtGui import QGuiApplication
        pantalla = self.screen() or QGuiApplication.primaryScreen()
        alto_contenido = contenido.sizeHint().height()
        self._scroll.setMinimumWidth(contenido.sizeHint().width() + 16)
        self._scroll.setMinimumHeight(alto_contenido)
        if pantalla is not None:
            limite = int(pantalla.availableGeometry().height() * 0.9)
            sobra = self.sizeHint().height() - limite
            if sobra > 0:
                self._scroll.setMinimumHeight(max(160, alto_contenido - sobra))
        self.adjustSize()

    def _actualizar_secciones(self, *_):
        """Las secciones que piden corridas se prenden con la primera tildada."""
        hay = any(self.lista_columnas.item(i).checkState() == Qt.CheckState.Checked
                  for i in range(self.lista_columnas.count()))
        for caja in self._requieren_lista:
            caja.setEnabled(hay)

    @staticmethod
    def _pie(texto):
        pie = QLabel(texto)
        pie.setWordWrap(True)
        pie.setObjectName("ayudaOpcion")
        return pie

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
