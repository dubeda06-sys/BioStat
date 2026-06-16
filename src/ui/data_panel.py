"""Panel de datos - Importacion, entrada manual y visualizacion."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QLabel, QFileDialog,
    QHeaderView, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt
import pandas as pd
import numpy as np

from src.ui.icons import Icons

MAX_VISIBLE_ROWS = 500


class DataPanel(QWidget):
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

        btn_csv = QPushButton(f"{Icons.CSV} CSV")
        btn_csv.setToolTip("Importar archivo de valores separados por coma (.csv)")
        btn_csv.clicked.connect(self._import_csv)
        btn_csv.setMinimumHeight(32)
        btn_layout.addWidget(btn_csv)

        btn_xlsx = QPushButton(f"{Icons.EXCEL} Excel")
        btn_xlsx.setToolTip("Importar archivo de Microsoft Excel (.xlsx, .xls)")
        btn_xlsx.setObjectName("secondary")
        btn_xlsx.clicked.connect(self._import_excel)
        btn_xlsx.setMinimumHeight(32)
        btn_layout.addWidget(btn_xlsx)

        btn_layout.addSpacing(8)

        btn_add_col = QPushButton(f"{Icons.ADD} Col")
        btn_add_col.setToolTip("Agregar una columna nueva a la tabla")
        btn_add_col.setObjectName("secondary")
        btn_add_col.clicked.connect(self._add_column)
        btn_add_col.setMinimumHeight(32)
        btn_layout.addWidget(btn_add_col)

        btn_add_row = QPushButton(f"{Icons.DOWN()} Fila")
        btn_add_row.setToolTip("Agregar una fila nueva a la tabla")
        btn_add_row.setObjectName("secondary")
        btn_add_row.clicked.connect(self._add_row)
        btn_add_row.setMinimumHeight(32)
        btn_layout.addWidget(btn_add_row)

        btn_clear = QPushButton(f"{Icons.TRASH()} Limpiar")
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

        self.table = QTableWidget()
        self.table.setMinimumHeight(160)
        self.table.setAlternatingRowColors(True)
        self.table.setRowCount(20)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Columna 1", "Columna 2", "Columna 3", "Columna 4", "Columna 5"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.cellChanged.connect(self._on_cell_changed)
        self.table.setToolTip("Escribe directamente aqui o importa un archivo. Las columnas numericas se usan para analisis.")
        layout.addWidget(self.table)

        stats_group = QGroupBox(f"  {Icons.STATS}  Estadisticas automaticas")
        stats_layout = QVBoxLayout()
        stats_layout.setContentsMargins(10, 6, 10, 6)
        self.lbl_stats = QLabel("Al cargar o escribir datos numericos, aqui apareceran: media, desviacion estandar, min, max y n.")
        self.lbl_stats.setObjectName("subtitle")
        self.lbl_stats.setWordWrap(True)
        stats_layout.addWidget(self.lbl_stats)
        stats_group.setLayout(stats_layout)
        stats_group.setMaximumHeight(110)
        layout.addWidget(stats_group)

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
            if file_path.endswith(".csv"):
                self.data = pd.read_csv(file_path)
            elif file_path.endswith((".xlsx", ".xls")):
                self.data = self._read_excel_smart(file_path)
            else:
                return
            self._clean_data()
            name = file_path.split("/")[-1].split("\\")[-1]
            self.lbl_info.setText(f"{name}  •  {len(self.data)} filas × {len(self.data.columns)} cols")
            self._populate_table()
            self._update_stats()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al cargar:\n{str(e)}")

    def _read_excel_smart(self, file_path):
        raw = pd.read_excel(file_path, header=None)
        header_row = 0
        for i in range(min(10, len(raw))):
            if raw.iloc[i].notna().sum() >= 2:
                header_row = i
                break
        df = pd.read_excel(file_path, header=header_row)
        df.columns = [str(c).strip() for c in df.columns]
        drop = [c for c in df.columns if "unnamed" in c.lower() or df[c].isna().all()]
        if drop:
            df = df.drop(columns=drop)
        return df.dropna(how="all")

    def _clean_data(self):
        if self.data is None:
            return
        drop = [c for c in self.data.columns if "unnamed" in str(c).lower() or self.data[c].isna().all()]
        if drop:
            self.data = self.data.drop(columns=drop)
        self.data = self.data.dropna(how="all")
        errors = ["#REF!", "#DIV/0!", "#N/A", "#VALUE!", "#NAME?", "#NULL!", "#NUM!"]
        for col in self.data.columns:
            if self.data[col].dtype == object:
                cleaned = self.data[col]
                for e in errors:
                    cleaned = cleaned.astype(str).str.replace(e, "", regex=False)
                try:
                    self.data[col] = pd.to_numeric(cleaned)
                except (ValueError, AttributeError):
                    pass

    def _populate_table(self):
        if self.data is None:
            return
        self.table.blockSignals(True)
        show = self.data.head(MAX_VISIBLE_ROWS)
        self.table.setRowCount(len(show))
        self.table.setColumnCount(len(self.data.columns))
        self.table.setHorizontalHeaderLabels(self.data.columns.tolist())
        for i, row in show.iterrows():
            for j, val in enumerate(row):
                self.table.setItem(i, j, QTableWidgetItem("" if pd.isna(val) else str(val)))
        self.table.blockSignals(False)
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
        self.table.setHorizontalHeaderItem(c, QTableWidgetItem(f"Col {c+1}"))
        if self.data is not None:
            self.data[f"Col {c+1}"] = ""

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
            self.table.setHorizontalHeaderLabels(["Columna 1", "Columna 2", "Columna 3", "Columna 4", "Columna 5"])
            self.table.blockSignals(False)
            self.lbl_info.setText("")
            self.lbl_stats.setText("Al cargar datos numericos aqui apareceran estadisticas automaticas.")

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
        headers = [self.table.horizontalHeaderItem(c).text() if self.table.horizontalHeaderItem(c) else f"C{c+1}" for c in range(self.table.columnCount())]
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
