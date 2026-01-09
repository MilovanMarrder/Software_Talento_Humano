import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox
from datetime import datetime
import threading

# Importamos servicios y vistas
from logics.perc_export_service import PercExportService
from views.modules.org_chart_view import OrgChartView # <--- NUEVO IMPORT

class ReportsView(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.service = PercExportService() 
        self.pack(fill=BOTH, expand=True, padx=10, pady=10)

        # --- TÍTULO PRINCIPAL ---
        lbl_title = ttk.Label(self, text="Módulo de Reportes e Inteligencia", font=("Helvetica", 16, "bold"))
        lbl_title.pack(pady=(0, 10), anchor="w")

        # --- SISTEMA DE PESTAÑAS (NOTEBOOK) ---
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=BOTH, expand=True)

        # Pestaña 1: Exportación de Archivos (Tu código original)
        self.tab_exports = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_exports, text="📂 Exportar Reportes Excel")

        # Pestaña 2: Organigrama Visual (Lo nuevo)
        self.tab_org = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_org, text="🌳 Organigrama Jerárquico")

        # --- INICIALIZAR PESTAÑAS ---
        self._init_export_tab()
        self._init_org_tab()

    def _init_org_tab(self):
        """Carga el componente visual del Organigrama en la pestaña 2"""
        # Simplemente instanciamos la clase que creamos en el Paso 2
        self.org_chart = OrgChartView(self.tab_org)

    def _init_export_tab(self):
        """Reconstruye tu lógica de reportes dentro de la Pestaña 1"""
        
        # Contenedor con scroll (Reparentado a tab_exports)
        self.main_container = ttk.Frame(self.tab_exports)
        self.main_container.pack(fill=BOTH, expand=True)

        # --------------------------------------------------
        # SECCIÓN DE REPORTES (Código Original Preservado)
        # --------------------------------------------------
        
        self._create_report_section(
            title="Plantilla PERC - Empleados",
            filename_prefix="EMPLEADOS_PERC",
            export_method=self.service.generate_empleados_perc_excel
        )

        self._create_report_with_input_section(
            title="Plantilla PERC - Programación de Horas",
            filename_prefix="PROGRAMACION_HORAS_PERC",
            export_method=self.service.generate_programacion_horas_perc_excel
        )
        
        self._create_report_section_attemporal(
            title="Descargar Base de Datos Completa (Backup)",
            filename_prefix="BACKUP_RRHH_FULL",
            export_method=self.service.export_database_to_excel 
        )

        # Separador visual y Zona de Importación
        ttk.Separator(self.main_container, orient=HORIZONTAL).pack(fill=X, pady=20)
        self._create_import_section()


    # ----------------------------------------------------------------------
    # MÉTODOS HELPER (Tu código original intacto, solo identado dentro de la clase)
    # ----------------------------------------------------------------------

    def _create_report_section(self, title, filename_prefix, export_method):
        card = ttk.Labelframe(self.main_container, text=title, padding=15)
        card.pack(fill=X, pady=10, anchor="n")
        row = ttk.Frame(card)
        row.pack(fill=X)

        ttk.Label(row, text="Mes:").pack(side=LEFT, padx=(0, 5))
        combo_mes = ttk.Combobox(row, values=[
            "01 - Enero", "02 - Febrero", "03 - Marzo", "04 - Abril",
            "05 - Mayo", "06 - Junio", "07 - Julio", "08 - Agosto",
            "09 - Septiembre", "10 - Octubre", "11 - Noviembre", "12 - Diciembre"
        ], state="readonly", width=15)
        combo_mes.current(datetime.now().month - 1)
        combo_mes.pack(side=LEFT, padx=(0, 15))

        ttk.Label(row, text="Año:").pack(side=LEFT, padx=(0, 5))
        spin_anio = ttk.Spinbox(row, from_=2020, to=2030, width=8)
        spin_anio.set(datetime.now().year)
        spin_anio.pack(side=LEFT, padx=(0, 15))

        progress = ttk.Progressbar(card, mode='indeterminate', bootstyle="success-striped")

        btn_generar = ttk.Button(
            row, text="Generar Excel", bootstyle="success",
            command=lambda: self._handle_generate_click(
                combo_mes, spin_anio, btn_generar, progress, filename_prefix, export_method
            )
        )
        btn_generar.pack(side=LEFT)

    def _handle_generate_click(self, combo_mes, spin_anio, btn, progress, prefix, method):
        mes_txt = combo_mes.get()
        mes_num = mes_txt.split(" - ")[0]
        anio = spin_anio.get()
        filename = f"{prefix}_{anio}_{mes_num}.xlsx"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx", filetypes=[("Excel Files", "*.xlsx")],
            initialfile=filename, title="Guardar Reporte"
        )
        if not filepath: return

        self._set_loading_state(True, combo_mes, spin_anio, btn, progress)
        thread = threading.Thread(
            target=self._run_export_logic, 
            args=(method, anio, mes_num, filepath, combo_mes, spin_anio, btn, progress)
        )
        thread.start()

    def _run_export_logic(self, method, year, month, filepath, *widgets):
        try:
            success, message = method(year, month, filepath)
        except Exception as e:
            success, message = False, f"Error inesperado: {str(e)}"
        self.after(0, lambda: self._on_export_finished(success, message, *widgets))

    def _on_export_finished(self, success, message, combo_mes, spin_anio, btn, progress):
        self._set_loading_state(False, combo_mes, spin_anio, btn, progress)
        if success: messagebox.showinfo("Éxito", message)
        else: messagebox.showerror("Error", message)

    def _create_report_with_input_section(self, title, filename_prefix, export_method):
        card = ttk.Labelframe(self.main_container, text=title, padding=15)
        card.pack(fill=X, pady=10)
        row1 = ttk.Frame(card)
        row1.pack(fill=X, pady=(0, 10))
        
        lbl_file = ttk.Label(row1, text="Plantilla PERC Descargada:", font=("Helvetica", 9, "italic"))
        lbl_file.pack(side=LEFT, padx=(0, 10))
        
        path_var = ttk.StringVar(value="")
        entry_path = ttk.Entry(row1, textvariable=path_var, state="readonly", width=50)
        entry_path.pack(side=LEFT, padx=(0, 5))

        def select_input_file():
            path = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx *.xls")])
            if path: path_var.set(path)

        ttk.Button(row1, text="Buscar...", command=select_input_file, bootstyle="secondary-outline").pack(side=LEFT)

        row2 = ttk.Frame(card)
        row2.pack(fill=X)
        ttk.Label(row2, text="Mes:").pack(side=LEFT, padx=(0, 5))
        combo_mes = ttk.Combobox(row2, values=[
            "01 - Enero", "02 - Febrero", "03 - Marzo", "04 - Abril",
            "05 - Mayo", "06 - Junio", "07 - Julio", "08 - Agosto",
            "09 - Septiembre", "10 - Octubre", "11 - Noviembre", "12 - Diciembre"
        ], state="readonly", width=15)
        combo_mes.current(datetime.now().month - 1)
        combo_mes.pack(side=LEFT, padx=(0, 10))

        ttk.Label(row2, text="Año:").pack(side=LEFT, padx=(0, 5))
        spin_anio = ttk.Spinbox(row2, from_=2020, to=2030, width=8)
        spin_anio.set(datetime.now().year)
        spin_anio.pack(side=LEFT, padx=(0, 15))

        progress = ttk.Progressbar(card, mode='indeterminate', bootstyle="success-striped")

        btn_generar = ttk.Button(
            row2, text="Procesar y Guardar", bootstyle="success",
            command=lambda: self._handle_generate_with_input(
                path_var.get(), combo_mes, spin_anio, btn_generar, progress, filename_prefix, export_method
            )
        )
        btn_generar.pack(side=LEFT)

    def _handle_generate_with_input(self, input_path, combo_mes, spin_anio, btn, progress, prefix, method):
        if not input_path:
            messagebox.showwarning("Atención", "Seleccione archivo de origen.")
            return
        mes_txt = combo_mes.get()
        mes_num = mes_txt.split(" - ")[0]
        anio = spin_anio.get()
        filename = f"{prefix}_{anio}_{mes_num}.xlsx"
        output_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx", filetypes=[("Excel Files", "*.xlsx")],
            initialfile=filename, title="Guardar Resultado"
        )
        if not output_path: return
        self._set_loading_state(True, combo_mes, spin_anio, btn, progress)
        thread = threading.Thread(
            target=self._run_export_logic_with_input, 
            args=(method, anio, mes_num, output_path, input_path, combo_mes, spin_anio, btn, progress)
        )
        thread.start()

    def _run_export_logic_with_input(self, method, year, month, output_path, input_path, *widgets):
        try:
            success, message = method(year, month, output_path, input_path)
        except Exception as e:
            success, message = False, f"Error: {str(e)}"
        self.after(0, lambda: self._on_export_finished(success, message, *widgets))

    def _create_report_section_attemporal(self, title, filename_prefix, export_method):
        card = ttk.Labelframe(self.main_container, text=title, padding=15)
        card.pack(fill=X, pady=10, anchor="n")
        row = ttk.Frame(card)
        row.pack(fill=X)
        progress = ttk.Progressbar(card, mode='indeterminate', bootstyle="success-striped")
        btn_generar = ttk.Button(
            row, text="Exportar Todo a Excel", bootstyle="warning",
            command=lambda: self._handle_generate_click_no_period(btn_generar, progress, filename_prefix, export_method)
        )
        btn_generar.pack(side=LEFT)

    def _handle_generate_click_no_period(self, btn, progress, prefix, method):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"{prefix}_{timestamp}.xlsx"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx", filetypes=[("Excel Files", "*.xlsx")],
            initialfile=filename, title="Guardar Backup"
        )
        if not filepath: return
        self._set_loading_state(True, btn, progress)
        thread = threading.Thread(
            target=self._run_simple_export_logic, 
            args=(method, filepath, btn, progress)
        )
        thread.start()

    def _run_simple_export_logic(self, method, filepath, *widgets):
        try:
            success, message = method(filepath)
        except Exception as e:
            success, message = False, f"Error: {str(e)}"
        self.after(0, lambda: self._on_export_finished_simple(success, message, *widgets))

    def _on_export_finished_simple(self, success, message, btn, progress):
        progress.stop()
        progress.pack_forget()
        btn.config(state="normal", text="Exportar Todo a Excel")
        if success: messagebox.showinfo("Éxito", message)
        else: messagebox.showerror("Error", message)

    def _set_loading_state(self, is_loading, *args):
        progress = args[-1]
        btn = args[-2]
        if is_loading:
            btn.config(state="disabled", text="Procesando...")
            progress.pack(fill=X, pady=(10, 0))
            progress.start(10)
            for w in args[:-2]:
                try: w.config(state="disabled")
                except: pass
        else:
            progress.stop()
            progress.pack_forget()
            btn.config(state="normal")
            for w in args[:-2]:
                try: 
                    if isinstance(w, ttk.Combobox): w.config(state="readonly")
                    else: w.config(state="normal")
                except: pass

    def _create_import_section(self):
        card = ttk.Labelframe(self.main_container, text="Restaurar Base de Datos desde Excel", padding=15, bootstyle="danger")
        card.pack(fill=X, pady=10, anchor="n")
        row = ttk.Frame(card)
        row.pack(fill=X)
        lbl_info = ttk.Label(row, text="⚠ ADVERTENCIA: Esta acción ELIMINA todos los datos actuales.", bootstyle="danger")
        lbl_info.pack(side=LEFT, padx=(0, 20))
        progress = ttk.Progressbar(card, mode='indeterminate', bootstyle="danger-striped")
        btn_importar = ttk.Button(
            row, text="Seleccionar Archivo y Restaurar", bootstyle="danger",
            command=lambda: self._handle_import_click(btn_importar, progress)
        )
        btn_importar.pack(side=RIGHT)

    def _handle_import_click(self, btn, progress):
        confirm = messagebox.askyesno(
            "Confirmación Crítica", 
            "¿Desea restaurar la base de datos?\n\nEsto ELIMINARÁ PERMANENTEMENTE los datos actuales.",
            icon='warning'
        )
        if not confirm: return
        input_path = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx *.xls")])
        if not input_path: return
        self._set_loading_state(True, btn, progress)
        thread = threading.Thread(
            target=self._run_import_logic,
            args=(input_path, btn, progress)
        )
        thread.start()

    def _run_import_logic(self, input_path, btn, progress):
        try:
            success, message = self.service.import_database_from_excel(input_path)
        except Exception as e:
            success, message = False, f"Error: {str(e)}"
        self.after(0, lambda: self._on_import_finished(success, message, btn, progress))

    def _on_import_finished(self, success, message, btn, progress):
        self._set_loading_state(False, btn, progress)
        if success: messagebox.showinfo("Restauración Exitosa", message)
        else: messagebox.showerror("Error", message)