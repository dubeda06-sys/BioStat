"""Ventana principal de BioStat."""
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget,
    QToolBar, QStatusBar, QFileDialog, QMessageBox, QApplication,
    QLabel, QWidget, QSizePolicy, QDockWidget, QMenu,
)
from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QAction, QActionGroup

from src.core.export import neutralizar_formulas
from src.ui.styles import MAIN_STYLE
from src.ui.icons import Icons
from src.ui.data_panel import DataPanel
from src.ui.analysis_panel import AnalysisPanel
from src.ui.graphs_panel import GraphsPanel
from src.ui.omni_panel import OmniPanel
from src.ui.menus import (
    MENU_ESTADISTICAS, ESTADISTICAS_SUELTAS, MENU_GRAFICOS, MENU_PRUEBAS, nombre_visible,
)
from src.ui.dialogs import DialogoAnalisis
from src.ui import previews
from src.ui.help_text import ANALYSIS_HELP
from src.ui import report_window
from src.ui.guia.modos import INFO_MODOS, Modo, guardar_modo, modo_guardado
from src.ui.guia.panel_guia import PanelGuia
from src.ui.guia.reflector import Reflector
from src.ui.guia.selector import SelectorModo
from src.ui.guia.rueditas import AsistenteRueditas
from src.ui.guia.ejemplos import OBJETIVOS, dataset
from src.ui.guia.analisis_datos import a_formato_largo
from src.analysis.omni_catalogo import POR_ID
from src.ui.formula_dialog import abrir_formula


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BioStat")
        self.setMinimumSize(1200, 750)
        self.resize(1350, 850)
        self.setStyleSheet(MAIN_STYLE)
        self._create_menu_bar()
        self._create_toolbar()
        self._create_status_bar()
        self._create_central_widget()
        self._crear_guia()

    def _create_menu_bar(self):
        mb = self.menuBar()

        fm = mb.addMenu("  Archivo  ")
        a = QAction("Abrir", self)
        a.setIcon(Icons.OPEN())
        a.setShortcut("Ctrl+O")
        a.triggered.connect(self._open_file)
        fm.addAction(a)

        a = QAction("Guardar", self)
        a.setIcon(Icons.SAVE())
        a.setShortcut("Ctrl+S")
        a.triggered.connect(self._save_file)
        fm.addAction(a)
        fm.addSeparator()

        ex = fm.addMenu("Exportar")
        a = QAction("CSV", self)
        a.triggered.connect(self._export_csv)
        ex.addAction(a)
        a = QAction("Excel", self)
        a.triggered.connect(self._export_excel)
        ex.addAction(a)
        a = QAction("HTML (Resultados)", self)
        a.triggered.connect(self._export_html)
        ex.addAction(a)
        fm.addSeparator()

        a = QAction("Salir", self)
        a.setShortcut("Ctrl+Q")
        a.triggered.connect(self.close)
        fm.addAction(a)

        em = mb.addMenu("Edición")
        copy = QAction("Copiar resultados", self)
        copy.setShortcut("Ctrl+C")
        copy.triggered.connect(self._copy_results)
        em.addAction(copy)

        # Por panel y no por indice: al sacar la pestaña de Control de Calidad
        # (27 sep) un indice fijo habria mandado "Omnianálisis" al vacio.
        vm = mb.addMenu("Ver")
        for nombre, atajo, panel in [
            ("Datos", "Ctrl+1", "data_panel"), ("Análisis", "Ctrl+2", "analysis_panel"),
            ("Gráficos", "Ctrl+3", "graphs_panel"), ("Omnianálisis", "Ctrl+4", "omni_panel"),
        ]:
            act = QAction(nombre, self)
            act.setShortcut(atajo)
            act.triggered.connect(
                lambda _checked, p=panel: self.tabs.setCurrentWidget(getattr(self, p)))
            vm.addAction(act)

        # Menu "Estadisticas": los 78 analisis agrupados por familia, como en
        # MedCalc. La tabla vive en src/ui/menus.py y tests/test_menus.py
        # comprueba que cada entrada apunte a un analisis que existe.
        sm = mb.addMenu("Estadísticas")
        sm.setToolTipsVisible(True)
        for grupo, items in MENU_ESTADISTICAS:
            sub = sm.addMenu(grupo)
            sub.setToolTipsVisible(True)
            for label, combo_text in items:
                sub.addAction(self._accion_analisis(label, combo_text))
        sm.addSeparator()
        for label, combo_text in ESTADISTICAS_SUELTAS:
            sm.addAction(self._accion_analisis(label, combo_text))

        gm = mb.addMenu("Gráficos")
        for label, combo_text in MENU_GRAFICOS:
            act = QAction(label, self)
            act.triggered.connect(lambda _checked, t=combo_text: self._goto_graph(t))
            gm.addAction(act)

        pm = mb.addMenu("Pruebas diagnósticas")
        pm.setToolTipsVisible(True)
        for label, combo_text in MENU_PRUEBAS:
            pm.addAction(self._accion_analisis(label, combo_text))

        om = mb.addMenu("Herramientas")
        act = QAction("Omnianálisis (elegir la prueba por mi)", self)
        act.triggered.connect(lambda: self.tabs.setCurrentWidget(self.omni_panel))
        om.addAction(act)

        # Menu "Ventana": se arma cada vez que se abre, con los informes vivos.
        self.menu_ventana = mb.addMenu("Ventana")
        self.menu_ventana.aboutToShow.connect(self._armar_menu_ventana)

        hm = mb.addMenu("Ayuda")
        about = QAction("Acerca de", self)
        about.triggered.connect(self._show_about)
        hm.addAction(about)

    def _accion_analisis(self, label, combo_text):
        """Entrada de menu con vista previa en el tooltip.

        Al pasar el mouse se ve la forma tipica del resultado antes de abrir
        nada: entre 78 rutinas, el nombre solo no alcanza para elegir.
        """
        act = QAction(label, self)
        act.setToolTip(previews.tooltip(combo_text, ANALYSIS_HELP.get(combo_text, "")))
        act.triggered.connect(lambda _checked, t=combo_text: self._goto_analysis(t))
        return act

    def _create_toolbar(self):
        tb = QToolBar()
        tb.setMovable(False)
        tb.setIconSize(QSize(16, 16))
        self.addToolBar(tb)
        self.toolbar = tb

        # Open button with SVG icon
        a = QAction(Icons.OPEN(), "Abrir", self)
        a.setToolTip("Abrir archivo CSV o Excel (Ctrl+O)")
        a.setShortcut("Ctrl+O")
        a.triggered.connect(self._open_file)
        tb.addAction(a)

        # Save button with SVG icon
        a = QAction(Icons.SAVE(), "Guardar", self)
        a.setToolTip("Guardar datos en archivo (Ctrl+S)")
        a.setShortcut("Ctrl+S")
        a.triggered.connect(self._save_file)
        tb.addAction(a)

        tb.addSeparator()

        # CSV button with SVG icon
        a = QAction(Icons.CSV(), "CSV", self)
        a.setToolTip("Exportar datos a CSV (Ctrl+E)")
        a.setShortcut("Ctrl+E")
        a.triggered.connect(self._export_csv)
        tb.addAction(a)

        # Excel button with SVG icon
        a = QAction(Icons.EXCEL(), "Excel", self)
        a.setToolTip("Exportar datos a Excel (Ctrl+Shift+E)")
        a.setShortcut("Ctrl+Shift+E")
        a.triggered.connect(self._export_excel)
        tb.addAction(a)

        tb.addSeparator()

        # Run button with SVG icon
        a = QAction(Icons.RUN(), "Analizar", self)
        a.setToolTip("Ejecutar análisis estadístico (Ctrl+R)")
        a.setShortcut("Ctrl+R")
        a.triggered.connect(self._run_analysis)
        tb.addAction(a)

        # Export button with SVG icon
        a = QAction(Icons.EXPORT(), "Exportar", self)
        a.setToolTip("Exportar resultados a HTML (Ctrl+Shift+X)")
        a.setShortcut("Ctrl+Shift+X")
        a.triggered.connect(self._export_html)
        tb.addAction(a)

    def _create_status_bar(self):
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage(
            "BioStat listo — importá un CSV o un Excel, o escribí en la tabla")

    def _create_central_widget(self):
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.setCentralWidget(self.tabs)

        self.data_panel = DataPanel()
        self.analysis_panel = AnalysisPanel()
        self.graphs_panel = GraphsPanel()
        self.omni_panel = OmniPanel()

        tabs_config = [
            (self.data_panel, "Datos"),
            (self.analysis_panel, "Análisis"),
            (self.graphs_panel, "Gráficos"),
            (self.omni_panel, "Omnianálisis"),
        ]
        for panel, name in tabs_config:
            self.tabs.addTab(panel, name)

        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.data_panel.dataChanged.connect(self._on_data_changed)

    def _on_data_changed(self, data):
        """Propaga los datos a todos los paneles al importar/limpiar, sin esperar
        a cambiar de pestaña."""
        if data is None:
            self.statusBar().showMessage(
                "Sin datos — importá un CSV o un Excel, o escribí en la tabla")
            return
        self.analysis_panel.set_data(data)
        self.graphs_panel.set_data(data)
        self.omni_panel.set_data(data)
        numericas = len(data.select_dtypes(include="number").columns)
        self.statusBar().showMessage(
            f"Datos: {len(data)} filas × {len(data.columns)} columnas "
            f"({numericas} numéricas)")

    def _on_tab_changed(self, index):
        data = self.data_panel.get_data()
        if data is None:
            return
        panel = self.tabs.widget(index)
        if panel is not self.data_panel:
            panel.set_data(data)

    def _run_analysis(self):
        """Ejecuta el analisis seleccionado: empuja datos y cambia a la pestaña Análisis."""
        data = self.data_panel.get_data()
        if data is None:
            QMessageBox.warning(self, "Sin datos", "Importa o ingresa datos antes de analizar.")
            self.tabs.setCurrentIndex(0)
            return
        self.analysis_panel.set_data(data)
        self.tabs.setCurrentWidget(self.analysis_panel)
        self.analysis_panel._run()

    def _goto_analysis(self, combo_text):
        """Abre el dialogo del analisis y, al aceptar, su ventana de informe.

        Es el flujo de MedCalc: menu -> dialogo con las variables -> informe en
        ventana propia. El calculo lo sigue haciendo `AnalysisPanel`; aca solo
        se le cargan las elecciones del dialogo y se le saca el resultado.
        """
        data = self.data_panel.get_data()
        if data is None:
            QMessageBox.warning(self, "Sin datos", "Importa o ingresa datos antes de analizar.")
            self.tabs.setCurrentIndex(0)
            return

        self.analysis_panel.set_data(data)
        idx = self.analysis_panel.combo_analysis.findText(combo_text)
        if idx >= 0:
            self.analysis_panel.combo_analysis.setCurrentIndex(idx)

        dialogo = DialogoAnalisis(combo_text, list(data.columns), self,
                                  alpha=self.analysis_panel.input_alpha.text(),
                                  columnas_numericas=list(
                                      data.select_dtypes(include="number").columns))
        if dialogo.exec() != DialogoAnalisis.DialogCode.Accepted:
            return

        eleccion = dialogo.seleccion()
        self._aplicar_eleccion(eleccion)
        self.analysis_panel._clear()
        self.analysis_panel._run()

        html = self.analysis_panel.txt_results.toHtml()
        # El grafico se muda a la ventana de informe; el panel repone su cartel.
        canvas = self.analysis_panel.tomar_grafico()
        report_window.abrir(nombre_visible(combo_text), html, canvas, self)
        self.statusBar().showMessage(
            f"{nombre_visible(combo_text)} — informe abierto en su ventana")

    def _armar_menu_ventana(self):
        """Rehace el menu Ventana con los informes abiertos en este momento."""
        self.menu_ventana.clear()
        ventanas = report_window.abiertas()
        if not ventanas:
            vacio = QAction("(no hay informes abiertos)", self)
            vacio.setEnabled(False)
            self.menu_ventana.addAction(vacio)
            return
        for ventana in ventanas:
            act = QAction(ventana.windowTitle().replace(" — BioStat", ""), self)
            act.triggered.connect(lambda _checked, v=ventana: (v.raise_(), v.activateWindow()))
            self.menu_ventana.addAction(act)
        self.menu_ventana.addSeparator()
        cerrar = QAction("Cerrar todos los informes", self)
        cerrar.triggered.connect(report_window.cerrar_todas)
        self.menu_ventana.addAction(cerrar)

    def _aplicar_eleccion(self, eleccion):
        """Vuelca lo elegido en el dialogo sobre los controles del panel."""
        panel = self.analysis_panel
        for clave, combo in (("c1", panel.combo_col1), ("c2", panel.combo_col2),
                             ("c3", panel.combo_col3)):
            valor = eleccion.get(clave)
            if not valor:
                continue
            idx = combo.findText(valor)
            if idx >= 0:
                combo.setCurrentIndex(idx)
        if eleccion.get("alpha"):
            panel.input_alpha.setText(eleccion["alpha"])
        # Las opciones de metodo no tienen control en el panel viejo: viajan
        # aparte, en un diccionario que el dispatch le pasa al analisis. Lo
        # mismo la lista de columnas tildadas y los parametros numericos.
        panel.opciones_metodo = eleccion.get("opciones") or {}
        panel.columnas_elegidas = eleccion.get("columnas")
        panel.parametros = eleccion.get("parametros") or {}

    def _goto_graph(self, combo_text):
        """Va al panel Graficos y selecciona el tipo de grafico."""
        data = self.data_panel.get_data()
        if data is not None:
            self.graphs_panel.set_data(data)
        self.tabs.setCurrentWidget(self.graphs_panel)
        idx = self.graphs_panel.combo_graph.findText(combo_text)
        if idx >= 0:
            self.graphs_panel.combo_graph.setCurrentIndex(idx)

    def _copy_results(self):
        """Copia el texto de resultados del análisis al portapapeles."""
        txt = self.analysis_panel.txt_results.toPlainText()
        if txt.strip():
            QApplication.clipboard().setText(txt)
            self.statusBar().showMessage("Resultados copiados al portapapeles")
        else:
            self.statusBar().showMessage("No hay resultados para copiar")

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir", "", "Datos (*.csv *.xlsx *.xls);;Todos (*)"
        )
        if path:
            self.data_panel.load_file(path)
            name = path.split("/")[-1].split("\\")[-1]
            self.statusBar().showMessage(f"Cargado: {name}")
            self.tabs.setCurrentIndex(0)

    def _save_file(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar", "", "CSV (*.csv);;Excel (*.xlsx);;Todos (*)"
        )
        if path:
            data = self.data_panel.get_data()
            if data is not None:
                if path.endswith(".csv"):
                    neutralizar_formulas(data).to_csv(path, index=False)
                else:
                    neutralizar_formulas(data).to_excel(path, index=False)
                self.statusBar().showMessage(f"Guardado: {path.split('/')[-1]}")

    def _show_about(self):
        from src.version import etiqueta
        QMessageBox.about(
            self, "Acerca de BioStat",
            "<h2>BioStat</h2>"
            f"<p>{etiqueta()}</p>"
            "<p>Software estadistico para laboratorio clinico.</p>"
            "<p>Permite importar datos, realizar analisis estadisticos "
            "y generar graficos.</p>"
        )

    def _export_csv(self):
        """Export data to CSV."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar CSV", "", "CSV (*.csv)"
        )
        if path:
            data = self.data_panel.get_data()
            if data is not None:
                neutralizar_formulas(data).to_csv(path, index=False)
                self.statusBar().showMessage(f"CSV exportado: {path.split('/')[-1]}")
            else:
                QMessageBox.warning(self, "Error", "No hay datos para exportar.")

    def _export_excel(self):
        """Export data to Excel."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar Excel", "", "Excel (*.xlsx)"
        )
        if path:
            data = self.data_panel.get_data()
            if data is not None:
                neutralizar_formulas(data).to_excel(path, index=False, engine='openpyxl')
                self.statusBar().showMessage(f"Excel exportado: {path.split('/')[-1]}")
            else:
                QMessageBox.warning(self, "Error", "No hay datos para exportar.")

    def _export_html(self):
        """Export results to HTML."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar HTML", "", "HTML (*.html)"
        )
        if path:
            from src.core.export import export_results_to_html
            results = self.analysis_panel.txt_results.toHtml()
            html = export_results_to_html({'Resultados': results}, "Informe BioStat")
            with open(path, 'w', encoding='utf-8') as f:
                f.write(html)
            self.statusBar().showMessage(f"HTML exportado: {path.split('/')[-1]}")

    # ================================================================
    #  Modos guía: Asistente, Docencia, Rueditas
    # ================================================================
    def _crear_guia(self):
        self._auditoria_guia = {}
        self._rueditas = None
        self._ultimo_ejemplo = None

        # Selector en la barra, pegado a la derecha.
        relleno = QWidget()
        relleno.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.toolbar.addWidget(relleno)
        self.selector_modo = SelectorModo()
        self.selector_modo.modoCambiado.connect(self._aplicar_modo)
        self.toolbar.addWidget(self.selector_modo)

        # Panel lateral.
        self.panel_guia = PanelGuia()
        self.dock_guia = QDockWidget("Guía", self)
        self.dock_guia.setObjectName("dock_guia")
        self.dock_guia.setWidget(self.panel_guia)
        self.dock_guia.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea
                                       | Qt.DockWidgetArea.RightDockWidgetArea)
        self.dock_guia.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable
                                   | QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_guia)
        self.resizeDocks([self.dock_guia], [380], Qt.Orientation.Horizontal)

        self.reflector = Reflector(self)

        p = self.panel_guia
        p.irAPestana.connect(self.tabs.setCurrentIndex)
        p.resaltar.connect(self._resaltar)
        p.cargarEjemplo.connect(self._cargar_ejemplo)
        p.abrirRueditas.connect(self._abrir_rueditas)
        p.cambiarModo.connect(self._aplicar_modo)
        p.abrirFormula.connect(self._formula_desde_guia)
        p.convertirLargo.connect(self._convertir_largo)
        self.tabs.currentChanged.connect(p.set_pestana)
        self.data_panel.dataChanged.connect(self._datos_para_guia)
        self.omni_panel.analisisTerminado.connect(self._analisis_para_guia)

        self._menu_guia()

        modo = modo_guardado()
        if modo is None:
            # Primera vez: el panel abierto ofrece elegir, sin diálogo que bloquee.
            self.selector_modo.set_modo(Modo.NORMAL)
            self.panel_guia.set_modo(Modo.NORMAL, eligiendo=True)
            self.dock_guia.show()
        else:
            self._aplicar_modo(modo.value, guardar=False, abrir=False)

    def _menu_guia(self):
        menu = QMenu("Guía", self)
        ayuda = next((a for a in self.menuBar().actions() if a.text() == "Ayuda"), None)
        if ayuda is not None:
            self.menuBar().insertMenu(ayuda, menu)
        else:
            self.menuBar().addMenu(menu)
        grupo = QActionGroup(self)
        self._acciones_modo = {}
        for modo, info in INFO_MODOS.items():
            a = QAction(f"Modo {info['nombre']}", self, checkable=True)
            a.setToolTip(info["lema"])
            a.triggered.connect(lambda _=False, m=modo: self._aplicar_modo(m.value))
            grupo.addAction(a)
            menu.addAction(a)
            self._acciones_modo[modo] = a
        menu.addSeparator()
        a = QAction("Elegir modo…", self)
        a.triggered.connect(self._elegir_modo)
        menu.addAction(a)
        a = QAction("Mostrar el panel guía", self)
        a.triggered.connect(self.dock_guia.show)
        menu.addAction(a)
        a = QAction("Rueditas: hacerle una pregunta a mis datos", self)
        a.setShortcut("Ctrl+Shift+R")
        a.triggered.connect(self._abrir_rueditas)
        menu.addAction(a)
        menu.addSeparator()
        sub = menu.addMenu("Cargar un ejemplo")
        for clave, obj in OBJETIVOS.items():
            a = QAction(obj.titulo, self)
            a.triggered.connect(lambda _=False, k=clave: self._cargar_ejemplo(k))
            sub.addAction(a)

    def _aplicar_modo(self, modo, guardar=True, abrir=True):
        modo = Modo(modo)
        self.selector_modo.set_modo(modo)
        if modo in getattr(self, "_acciones_modo", {}):
            self._acciones_modo[modo].setChecked(True)
        self.panel_guia.set_modo(modo)
        self.dock_guia.setVisible(modo != Modo.NORMAL)
        info = INFO_MODOS[modo]
        self.dock_guia.setWindowTitle(f"Guía — {info['nombre']}")
        if guardar:
            guardar_modo(modo)
            self.statusBar().showMessage(f"Modo {info['nombre']}: {info['lema']}", 5000)
        if modo == Modo.RUEDITAS and abrir:
            QTimer.singleShot(150, self._abrir_rueditas)

    def _elegir_modo(self):
        self.panel_guia.set_modo(self.panel_guia.modo, eligiendo=True)
        self.dock_guia.show()

    # ---------- estado hacia la guía ----------
    def _datos_para_guia(self, df):
        self.panel_guia.set_datos(df)
        if self._rueditas is not None and self._rueditas.isVisible():
            ejemplo, self._ultimo_ejemplo = self._ultimo_ejemplo, None
            self._rueditas.set_datos(df, ejemplo)

    def _analisis_para_guia(self, report, auditoria, casos):
        self._auditoria_guia = auditoria or {}
        self.panel_guia.set_analisis(casos)

    # ---------- acciones pedidas por la guía ----------
    def _resaltar(self, clave, titulo, texto):
        # Esperar a que la pestaña pedida termine de mostrarse antes de medir.
        QTimer.singleShot(80, lambda: self._resaltar_ahora(clave, titulo, texto))

    def _resaltar_ahora(self, clave, titulo, texto):
        from PyQt6.QtCore import QPoint, QRect
        omni = self.omni_panel
        objetivos = {
            "tabla": getattr(self.data_panel, "table", None),
            "omni_variables": getattr(omni, "list_vars", None),
            "omni_objetivo": getattr(omni, "cmb_target", None),
            "omni_ejecutar": getattr(omni, "btn_run", None),
            "omni_pestanas": getattr(omni, "tabs", None),
            "selector_modo": self.selector_modo,
        }
        color = INFO_MODOS[self.panel_guia.modo]["color"]
        if clave == "importar":
            a, b = self.data_panel.btn_csv, self.data_panel.btn_xlsx
            r1 = QRect(a.mapTo(self, QPoint(0, 0)), a.size())
            r2 = QRect(b.mapTo(self, QPoint(0, 0)), b.size())
            self.reflector.mostrar(r1.united(r2), titulo, texto, color)
            return
        w = objetivos.get(clave)
        if w is not None:
            self.reflector.mostrar(w, titulo, texto, color)

    def _cargar_ejemplo(self, clave):
        self._ultimo_ejemplo = clave
        self.data_panel.cargar_dataframe(dataset(clave),
                                         nombre=f"Ejemplo — {OBJETIVOS[clave].titulo}")
        if self._rueditas is None or not self._rueditas.isVisible():
            self._ultimo_ejemplo = None
            self.tabs.setCurrentIndex(0)

    def _convertir_largo(self, columnas):
        df = self.data_panel.get_data()
        if df is None:
            return
        r = QMessageBox.question(
            self, "Pasar a formato largo",
            "Voy a reemplazar la tabla por una con dos columnas:\n"
            "«grupo» (el nombre de cada columna original) y «valor».\n\n"
            f"Columnas que se apilan: {', '.join(columnas)}\n\n"
            "Si querés conservar la original, guardala antes. ¿Sigo?")
        if r == QMessageBox.StandardButton.Yes:
            self.data_panel.cargar_dataframe(a_formato_largo(df, columnas),
                                             nombre="tabla en formato largo")

    def _formula_desde_guia(self, ensayo_id):
        fila = next((f for f in self._auditoria_guia.get("filas", [])
                     if f["id"] == ensayo_id), {})
        ens = POR_ID.get(ensayo_id)
        abrir_formula(self, ensayo_id, nombre=ens.nombre if ens else ensayo_id,
                      estado=fila.get("estado"), ejecuciones=fila.get("ejecuciones"),
                      motivos=fila.get("motivos"))

    def _abrir_rueditas(self):
        if self._rueditas is not None and self._rueditas.isVisible():
            self._rueditas.raise_()
            self._rueditas.activateWindow()
            return
        dlg = AsistenteRueditas(self.data_panel.get_data(), self)
        dlg.pedirEjemplo.connect(self._cargar_ejemplo)
        dlg.pedirArchivo.connect(self._open_file)
        dlg.verDetalle.connect(self._detalle_rueditas)
        self._rueditas = dlg
        dlg.show()

    def _detalle_rueditas(self, columnas, pares):
        self.tabs.setCurrentWidget(self.omni_panel)
        self.omni_panel.set_data(self.data_panel.get_data())
        self.omni_panel.ejecutar_con(columnas, [tuple(p) for p in pares])
