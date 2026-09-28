"""Panel de datos - Importacion, entrada manual y visualizacion."""
import re

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QLabel, QFileDialog,
    QHeaderView, QGroupBox, QMessageBox, QInputDialog, QStyledItemDelegate
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
import pandas as pd
import numpy as np

from src.analysis import omni_analyzer as omni
from src.ui.icons import Icons

MAX_VISIBLE_ROWS = 500


def letra_columna(indice):
    """A, B, ... Z, AA, AB... como en una planilla."""
    letras = ""
    indice += 1
    while indice:
        indice, resto = divmod(indice - 1, 26)
        letras = chr(65 + resto) + letras
    return letras


_NUMERO = re.compile(r"^[+-]?(\d+([.,]\d*)?|[.,]\d+)([eE][+-]?\d+)?$")


def numero(texto):
    """El número escrito en una celda, con punto o con coma decimal; None si
    no es un número. Antes «12,5» escrito a mano quedaba como texto y la
    columna entera dejaba de ser numérica (27 sep)."""
    t = str(texto).strip()
    if not _NUMERO.match(t):
        return None
    return float(t.replace(",", "."))


def para_mostrar(texto):
    """Cómo se ve un número en la hoja: sin la cola de decimales de coma
    flotante (181.115415006832 → 181.1154) y los enteros sin «.0». Solo es la
    vista: el valor guardado no cambia, y al editar la celda aparece entero."""
    v = numero(texto)
    if v is None:
        return str(texto)
    if v == int(v) and abs(v) < 1e15:
        return str(int(v))
    if abs(v) < 0.01 or abs(v) >= 1e7:
        return f"{v:.4g}"
    return f"{v:.4f}".rstrip("0").rstrip(".")


class _Numeros(QStyledItemDelegate):
    """Muestra los números con `para_mostrar`; la edición usa el texto entero.

    También pinta el fondo propio de la celda (el de las vacías): con una regla
    `QTableWidget::item` en la hoja de estilos, Qt deja de pintarlo solo.
    """

    def displayText(self, value, locale):  # noqa: N802 (nombre de Qt)
        return para_mostrar(value) if value is not None else ""

    def paint(self, painter, option, index):
        fondo = index.data(Qt.ItemDataRole.BackgroundRole)
        if fondo is not None:
            painter.fillRect(option.rect, fondo)
        super().paint(painter, option, index)


def encabezado(indice, nombre):
    """Texto del encabezado: la letra de columna y el nombre de la variable."""
    return f"{letra_columna(indice)}  {nombre}"


# Fondo de una celda vacía en datos cargados: se ve dónde faltan datos antes de
# que un análisis deje afuera la fila.
FONDO_FALTANTE = QColor("#fbeccc")

_TIPO_CORTO = {
    omni.NUMERIC_CONTINUOUS: "numérica",
    omni.NUMERIC_DISCRETE: "numérica discreta",
    omni.CATEGORICAL_NOMINAL: "categórica",
    omni.CATEGORICAL_ORDINAL: "ordinal",
    omni.BINARY: "binaria",
    omni.DATETIME: "fecha",
    omni.AMBIGUOUS: "a confirmar",
}


def tipo_en_la_hoja(serie):
    """(rótulo, explicación) del tipo de una columna, tal como la lee el
    Omnianálisis. El rótulo va en el segundo renglón del encabezado («numérica
    · 3 vacías», «códigos 1–3»); la explicación, en su ayuda. None si la
    columna está vacía del todo."""
    info = omni.tipo_de_columna(serie)
    n, validos = info["n"], info["n_valid"]
    if validos == 0:
        return None
    if info.get("codigos"):
        s = serie.dropna()
        corto = f"códigos {int(round(s.min()))}–{int(round(s.max()))}"
    else:
        corto = _TIPO_CORTO.get(info["tipo"], info["tipo"])
    faltan = n - validos
    if faltan:
        corto += f" · {faltan} vacía" + ("s" if faltan > 1 else "")
    ayuda = (f"Tipo: {info['tipo']}. {validos} de {n} filas con dato, "
             f"{info['n_unique']} valores distintos.")
    if info.get("nota"):
        ayuda += f"\n{info['nota']}"
    ayuda += "\nEs como la lee el Omnianálisis. Doble clic para renombrar."
    return corto, ayuda


class DataPanel(QWidget):
    # Se emite cuando cambian los datos cargados (import o limpiar).
    dataChanged = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.data = None
        self._tipos = {}   # índice de columna → (rótulo, explicación) del tipo
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(10, 4, 10, 4)

        tip = QLabel("Importá un CSV o un Excel, o escribí en la tabla (el decimal puede ir con coma).")
        tip.setObjectName("subtitle")
        layout.addWidget(tip)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)

        btn_csv = QPushButton("CSV")
        btn_csv.setIcon(Icons.CSV())
        btn_csv.setToolTip("Importar archivo de valores separados por coma (.csv)")
        btn_csv.clicked.connect(self._import_csv)
        btn_csv.setMinimumHeight(32)
        btn_layout.addWidget(btn_csv)

        btn_xlsx = QPushButton("Excel")
        btn_xlsx.setIcon(Icons.EXCEL())
        btn_xlsx.setToolTip("Importar archivo de Microsoft Excel (.xlsx, .xls)")
        btn_xlsx.setObjectName("secondary")
        btn_xlsx.clicked.connect(self._import_excel)
        btn_xlsx.setMinimumHeight(32)
        btn_layout.addWidget(btn_xlsx)

        btn_layout.addSpacing(8)

        btn_add_col = QPushButton("Col")
        btn_add_col.setIcon(Icons.ADD())
        btn_add_col.setToolTip("Agregar una columna nueva a la tabla")
        btn_add_col.setObjectName("secondary")
        btn_add_col.clicked.connect(self._add_column)
        btn_add_col.setMinimumHeight(32)
        btn_layout.addWidget(btn_add_col)

        btn_add_row = QPushButton("Fila")
        btn_add_row.setIcon(Icons.DOWN())
        btn_add_row.setToolTip("Agregar una fila nueva a la tabla")
        btn_add_row.setObjectName("secondary")
        btn_add_row.clicked.connect(self._add_row)
        btn_add_row.setMinimumHeight(32)
        btn_layout.addWidget(btn_add_row)

        btn_clear = QPushButton("Limpiar")
        btn_clear.setIcon(Icons.TRASH())
        btn_clear.setToolTip("Borrar todos los datos de la tabla")
        btn_clear.setObjectName("danger")
        btn_clear.clicked.connect(self._clear_data)
        btn_clear.setMinimumHeight(32)
        btn_layout.addWidget(btn_clear)

        btn_layout.addStretch()

        self.lbl_info = QLabel("")
        self.lbl_info.setObjectName("subtitle")
        btn_layout.addWidget(self.lbl_info)

        layout.addLayout(btn_layout)

        # Planilla: filas bajas, columnas de ancho fijo y encabezado con la
        # letra de columna delante del nombre, como en MedCalc.
        self.table = QTableWidget()
        self.table.setMinimumHeight(280)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(20)
        self.table.verticalHeader().setMinimumWidth(34)
        self.table.setRowCount(30)
        self.table.setColumnCount(5)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setDefaultSectionSize(110)
        self.table.horizontalHeader().sectionDoubleClicked.connect(self._renombrar_columna)
        self.table.cellChanged.connect(self._on_cell_changed)
        self.table.setItemDelegate(_Numeros(self.table))
        self.table.setToolTip(
            "Escribí directamente acá o importá un archivo. Doble clic en el "
            "encabezado para renombrar la variable."
        )
        self._nombres_por_defecto()
        layout.addWidget(self.table)

        stats_group = QGroupBox("    Estadísticas automáticas")
        stats_layout = QVBoxLayout()
        stats_layout.setContentsMargins(10, 6, 10, 6)
        self.lbl_stats = QLabel("Al cargar o escribir datos numéricos, aquí aparecen: media, desviación estándar, mínimo, máximo y n.")
        self.lbl_stats.setObjectName("subtitle")
        self.lbl_stats.setWordWrap(True)
        stats_layout.addWidget(self.lbl_stats)
        stats_group.setLayout(stats_layout)
        stats_group.setMaximumHeight(110)
        layout.addWidget(stats_group)

    def _nombres_por_defecto(self):
        self._poner_encabezados([f"Var{i + 1}" for i in range(self.table.columnCount())])

    def _poner_encabezados(self, nombres, tipos=None):
        """Escribe los encabezados: la letra de columna delante del nombre y, si
        se conoce, el tipo de la columna en un segundo renglón. El nombre de la
        variable se guarda aparte (UserRole), porque el texto ya no es solo eso."""
        for i, nombre in enumerate(nombres):
            texto = encabezado(i, nombre)
            tipo = (tipos or {}).get(i)
            item = QTableWidgetItem(texto if tipo is None else f"{texto}\n{tipo[0]}")
            item.setData(Qt.ItemDataRole.UserRole, nombre)
            item.setToolTip(f"{nombre}\n{tipo[1]}" if tipo else "Doble clic para renombrar.")
            self.table.setHorizontalHeaderItem(i, item)

    def nombres_de_columna(self):
        """Nombres de variable actuales, sin la letra de columna ni el tipo."""
        nombres = []
        for i in range(self.table.columnCount()):
            item = self.table.horizontalHeaderItem(i)
            nombre = item.data(Qt.ItemDataRole.UserRole) if item else None
            if nombre is None:
                texto = item.text() if item else ""
                prefijo = letra_columna(i) + "  "
                nombre = texto[len(prefijo):] if texto.startswith(prefijo) else texto
            nombres.append(nombre)
        return nombres

    def _marcar_tipos(self, columnas=None):
        """El tipo de cada columna en su encabezado; `columnas` = solo esas
        (al editar una celda no hace falta volver a leer toda la hoja)."""
        df = self.get_data()
        nombres = self.nombres_de_columna()
        if df is None:
            self._tipos = {}
        else:
            for j in (range(min(len(nombres), df.shape[1])) if columnas is None else columnas):
                if j < df.shape[1]:
                    tipo = tipo_en_la_hoja(df.iloc[:, j])
                    if tipo is None:
                        self._tipos.pop(j, None)
                    else:
                        self._tipos[j] = tipo
        self._poner_encabezados(nombres, self._tipos)

    def _pintar(self, item, vacia):
        """Fondo de celda vacía; sin señales, que un cambio de fondo también
        dispara cellChanged."""
        bloqueadas = self.table.blockSignals(True)
        if vacia:
            item.setBackground(FONDO_FALTANTE)
        else:
            item.setData(Qt.ItemDataRole.BackgroundRole, None)
        self.table.blockSignals(bloqueadas)

    def _renombrar_columna(self, indice):
        """Doble clic en el encabezado: renombra la variable."""
        actual = self.nombres_de_columna()[indice]
        nuevo, ok = QInputDialog.getText(
            self, "Nombre de la variable",
            f"Columna {letra_columna(indice)}:", text=actual)
        nuevo = nuevo.strip()
        if not ok or not nuevo or nuevo == actual:
            return
        nombres = self.nombres_de_columna()
        nombres[indice] = nuevo
        self._poner_encabezados(nombres, self._tipos)
        if self.data is not None and indice < len(self.data.columns):
            self.data.rename(columns={self.data.columns[indice]: nuevo}, inplace=True)
            self.dataChanged.emit(self.data)

    def _import_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "CSV", "", "CSV (*.csv);;Todos (*)")
        if path:
            self.load_file(path)

    def _import_excel(self):
        path, _ = QFileDialog.getOpenFileName(self, "Excel", "", "Excel (*.xlsx *.xls);;Todos (*)")
        if path:
            self.load_file(path)

    def load_file(self, file_path):
        try:
            from src.io.importers import read_any
            self.data = read_any(file_path)
            if self.data is None:
                return
            import os
            name = os.path.basename(file_path)
            self.lbl_info.setText(f"{name}  •  {len(self.data)} filas × {len(self.data.columns)} cols")
            self._populate_table()
            self._update_stats()
            self.dataChanged.emit(self.data)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al cargar:\n{str(e)}")

    def _populate_table(self):
        if self.data is None:
            return
        self.table.blockSignals(True)
        show = self.data.head(MAX_VISIBLE_ROWS)
        self.table.setRowCount(len(show))
        self.table.setColumnCount(len(self.data.columns))
        self._poner_encabezados(self.data.columns.tolist())
        # Indexar por POSICION (i), no por la etiqueta del indice del DataFrame,
        # que puede no ser contigua tras limpiar filas.
        for i, (_, row) in enumerate(show.iterrows()):
            for j, val in enumerate(row):
                vacia = pd.isna(val)
                item = QTableWidgetItem("" if vacia else str(val))
                if vacia:
                    item.setBackground(FONDO_FALTANTE)
                self.table.setItem(i, j, item)
        self.table.blockSignals(False)
        self._tipos = {}
        self._marcar_tipos()
        # Ancho por contenido, pero sin columnas mezquinas: el encabezado lleva
        # la letra delante y los nombres largos quedaban cortados.
        self.table.resizeColumnsToContents()
        for c in range(self.table.columnCount()):
            self.table.setColumnWidth(c, max(80, min(220, self.table.columnWidth(c) + 12)))
        total = len(self.data)
        self.lbl_info.setText(
            f"{total} filas × {len(self.data.columns)} cols"
            + (f"  (mostrando {len(show)})" if total > len(show) else "")
        )

    def _on_cell_changed(self, row, col):
        item = self.table.item(row, col)
        if self.data is not None and col < len(self.data.columns) and item is not None:
            if row >= len(self.data):
                # Una fila agregada con «Fila»: antes lo escrito ahí se perdía.
                self.data = self.data.reset_index(drop=True).reindex(range(row + 1))
            self._escribir(row, col, item.text())
            self._pintar(item, item.text().strip() == "")
            self._marcar_tipos([col])
        else:
            self._marcar_tipos()
        self._update_stats()

    def _escribir(self, fila, col, texto):
        """Guarda lo escrito en una celda de los datos cargados: un número (con
        punto o con coma), un texto, o nada. Vacía es un dato faltante; antes
        quedaba "" y la columna entera dejaba de ser numérica."""
        cn = self.data.columns[col]
        t = texto.strip()
        v = numero(t)
        valor = np.nan if t == "" else (t if v is None else v)
        # La columna tiene que poder guardar el valor: pandas avisa (y en la
        # versión 3 falla) si se mete un texto en una columna de números.
        serie = self.data[cn]
        if isinstance(valor, str):
            if serie.dtype != object:
                self.data[cn] = serie.astype(object)
        elif pd.api.types.is_integer_dtype(serie) or pd.api.types.is_bool_dtype(serie):
            self.data[cn] = serie.astype(float)
        elif pd.api.types.is_datetime64_any_dtype(serie) and v is not None:
            self.data[cn] = serie.astype(object)
        self.data.at[self.data.index[fila], cn] = valor
        # Si al corregir se fue el único texto, la columna vuelve a ser numérica.
        serie = self.data[cn]
        if serie.dtype == object:
            resto = serie.dropna()
            if len(resto) and all(isinstance(x, (int, float, np.integer, np.floating))
                                  and not isinstance(x, (bool, np.bool_)) for x in resto):
                self.data[cn] = pd.to_numeric(serie)

    def _add_column(self):
        c = self.table.columnCount()
        self.table.setColumnCount(c + 1)
        nombres = self.nombres_de_columna()
        nombres[c] = f"Var{c + 1}"
        self._poner_encabezados(nombres, self._tipos)
        if self.data is not None:
            self.data[f"Var{c + 1}"] = np.nan

    def _add_row(self):
        if self.data is not None and len(self.data) > self.table.rowCount():
            QMessageBox.information(
                self, "Agregar fila",
                f"La hoja muestra las primeras {self.table.rowCount()} filas de "
                f"{len(self.data)}: una fila nueva quedaría fuera de la vista. "
                "Agregala en el archivo y volvé a importarlo.")
            return
        self.table.setRowCount(self.table.rowCount() + 1)

    def _clear_data(self):
        if QMessageBox.question(
            self, "Confirmar", "¿Borrar todos los datos?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            self.data = None
            self.table.blockSignals(True)
            self.table.clearContents()
            self.table.setRowCount(20)
            self.table.setColumnCount(5)
            self._tipos = {}
            self._nombres_por_defecto()
            self.table.blockSignals(False)
            self.lbl_info.setText("")
            self.lbl_stats.setText("Al cargar datos numéricos, aquí aparecen las estadísticas automáticas.")
            self.dataChanged.emit(None)

    def _update_stats(self):
        df = self.get_data()
        if df is None:
            return
        nums = df.select_dtypes(include="number").columns
        if len(nums) == 0:
            self.lbl_stats.setText("No hay columnas numéricas.")
            return
        parts = []
        for col in nums[:5]:
            d = df[col].dropna()
            if len(d) == 0:
                continue
            parts.append(f"<b>{col}</b>: x\u0304={d.mean():.2f}  s={d.std():.2f}  [{d.min():.2f}\u2013{d.max():.2f}]  n={len(d)}")
        self.lbl_stats.setText("<br>".join(parts))

    def get_data(self):
        if self.data is not None and len(self.data) > 0:
            return self.data
        return self._build_from_table()

    def _build_from_table(self):
        # Sin la letra de columna: el DataFrame lleva el nombre de la variable.
        headers = self.nombres_de_columna()
        rows = []
        for r in range(self.table.rowCount()):
            rd, has = [], False
            for c in range(self.table.columnCount()):
                item = self.table.item(r, c)
                v = item.text().strip() if item else ""
                if v:
                    has = True
                rd.append(v)
            if has:
                rows.append(rd)
        if not rows:
            return None
        df = pd.DataFrame(rows, columns=headers)
        for col in df.columns:
            # Numérica si todo lo escrito es un número, con punto o con coma.
            valores = [numero(v) if v != "" else np.nan for v in df[col]]
            if all(v is not None for v in valores):
                df[col] = pd.Series(valores, index=df.index, dtype=float)
            else:
                # Una celda vacía es un dato faltante, no la categoría "".
                df[col] = df[col].mask(df[col] == "")
        return df
