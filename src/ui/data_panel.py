"""Panel de datos - Importacion, entrada manual y visualizacion."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QLabel, QFileDialog,
    QHeaderView, QGroupBox, QMessageBox, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
import pandas as pd
import numpy as np

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


def encabezado(indice, nombre):
    """Texto del encabezado: la letra de columna y el nombre de la variable."""
    return f"{letra_columna(indice)}  {nombre}"


class DataPanel(QWidget):
    # Se emite cuando cambian los datos cargados (import o limpiar).
    dataChanged = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.data = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(10, 4, 10, 4)

        tip = QLabel("Importa CSV/Excel o escribe en la tabla.")
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
        self.table.setToolTip(
            "Escribe directamente aqui o importa un archivo. Doble clic en el "
            "encabezado para renombrar la variable."
        )
        self._nombres_por_defecto()
        layout.addWidget(self.table)

        stats_group = QGroupBox(f"    Estadisticas automaticas")
        stats_layout = QVBoxLayout()
        stats_layout.setContentsMargins(10, 6, 10, 6)
        self.lbl_stats = QLabel("Al cargar o escribir datos numericos, aqui apareceran: media, desviacion estandar, min, max y n.")
        self.lbl_stats.setObjectName("subtitle")
        self.lbl_stats.setWordWrap(True)
        stats_layout.addWidget(self.lbl_stats)
        stats_group.setLayout(stats_layout)
        stats_group.setMaximumHeight(110)
        layout.addWidget(stats_group)

    def _nombres_por_defecto(self):
        self._poner_encabezados([f"Var{i + 1}" for i in range(self.table.columnCount())])

    def _poner_encabezados(self, nombres):
        """Escribe los encabezados con su letra de columna delante."""
        self.table.setHorizontalHeaderLabels(
            [encabezado(i, n) for i, n in enumerate(nombres)])

    def nombres_de_columna(self):
        """Nombres de variable actuales, sin la letra de columna."""
        nombres = []
        for i in range(self.table.columnCount()):
            item = self.table.horizontalHeaderItem(i)
            texto = item.text() if item else ""
            prefijo = letra_columna(i) + "  "
            nombres.append(texto[len(prefijo):] if texto.startswith(prefijo) else texto)
        return nombres

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
        self._poner_encabezados(nombres)
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
                self.table.setItem(i, j, QTableWidgetItem("" if pd.isna(val) else str(val)))
        self.table.blockSignals(False)
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
        if self.data is not None and row < len(self.data) and col < len(self.data.columns):
            item = self.table.item(row, col)
            if item:
                cn = self.data.columns[col]
                try:
                    self.data.at[self.data.index[row], cn] = float(item.text())
                except ValueError:
                    self.data.at[self.data.index[row], cn] = item.text()
        self._update_stats()

    def _add_column(self):
        c = self.table.columnCount()
        self.table.setColumnCount(c + 1)
        self.table.setHorizontalHeaderItem(c, QTableWidgetItem(encabezado(c, f"Var{c + 1}")))
        if self.data is not None:
            self.data[f"Var{c + 1}"] = ""

    def _add_row(self):
        self.table.setRowCount(self.table.rowCount() + 1)

    def _clear_data(self):
        if QMessageBox.question(
            self, "Confirmar", "Borrar todos los datos?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            self.data = None
            self.table.blockSignals(True)
            self.table.clearContents()
            self.table.setRowCount(20)
            self.table.setColumnCount(5)
            self._nombres_por_defecto()
            self.table.blockSignals(False)
            self.lbl_info.setText("")
            self.lbl_stats.setText("Al cargar datos numericos aqui apareceran estadisticas automaticas.")
            self.dataChanged.emit(None)

    def _update_stats(self):
        df = self.get_data()
        if df is None:
            return
        nums = df.select_dtypes(include="number").columns
        if len(nums) == 0:
            self.lbl_stats.setText("Sin columnas numericas detectadas.")
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
            try:
                df[col] = pd.to_numeric(df[col])
            except (ValueError, TypeError):
                pass
        return df
