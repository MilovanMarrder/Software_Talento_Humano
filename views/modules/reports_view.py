# 


import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox
from datetime import datetime
import threading

# Importamos el servicio
from logics.perc_export_service import PercExportService

class ReportsView(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.service = PercExportService() # Instancia única del servicio
        self.pack(fill=BOTH, expand=True, padx=20, pady=20)

        # Título principal
        lbl_title = ttk.Label(self, text="Generación de Reportes", font=("Helvetica", 16, "bold"))
        lbl_title.pack(pady=(0, 20), anchor="w")

        # Contenedor con scroll (por si hay muchos reportes)
        self.main_container = ttk.Frame(self)
        self.main_container.pack(fill=BOTH, expand=True)



#--------------------------------------------------SECCIÓN DE REPORTES-------------------------------------------
        # --- DEFINICIÓN DE REPORTES ---
        # Solo tienes que agregar elementos a esta lista para crear nuevos botones
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
            title="Descargar Base de Datos en Excel",
            filename_prefix="Base de datos Talento Humano",
            export_method=self.service.generate_horas_extras_excel # Aún en contrucción solo generé el maquetado
        )


#----------------------------------------------FIN-SECCIÓN DE REPORTES-------------------------------------------
    def _create_report_section_attemporal(self, title, filename_prefix, export_method):
        """
        Caja de reporte sin un periodo en especifico.
        Pensado para reportes de descarga de tablas de la base de datos.
        """
        card = ttk.Labelframe(self.main_container, text=title, padding=15)
        card.pack(fill=X, pady=10, anchor="n")

        row = ttk.Frame(card)
        row.pack(fill=X)
        # --- Barra de progreso (oculta) ---
        progress = ttk.Progressbar(card, mode='indeterminate', bootstyle="success-striped")

        # --- Botón de Generar ---
        # Usamos una función lambda para pasar los widgets específicos de esta card
        btn_generar = ttk.Button(
            row, 
            text="Generar Excel", 
            bootstyle="success",
            command=lambda: self._handle_generate_click_no_period(
              btn_generar, progress, filename_prefix, export_method
            )
        )
        btn_generar.pack(side=LEFT)


    def _create_report_section(self, title, filename_prefix, export_method):
        """Crea una fila de controles para un reporte específico"""
        card = ttk.Labelframe(self.main_container, text=title, padding=15)
        card.pack(fill=X, pady=10, anchor="n")

        row = ttk.Frame(card)
        row.pack(fill=X)


        # --- Selector de Mes ---
        ttk.Label(row, text="Mes:").pack(side=LEFT, padx=(0, 5))
        combo_mes = ttk.Combobox(row, values=[
            "01 - Enero", "02 - Febrero", "03 - Marzo", "04 - Abril",
            "05 - Mayo", "06 - Junio", "07 - Julio", "08 - Agosto",
            "09 - Septiembre", "10 - Octubre", "11 - Noviembre", "12 - Diciembre"
        ], state="readonly", width=15)
        combo_mes.current(datetime.now().month - 1)
        combo_mes.pack(side=LEFT, padx=(0, 15))

        # --- Selector de Año ---
        ttk.Label(row, text="Año:").pack(side=LEFT, padx=(0, 5))
        spin_anio = ttk.Spinbox(row, from_=2020, to=2030, width=8)
        spin_anio.set(datetime.now().year)
        spin_anio.pack(side=LEFT, padx=(0, 15))

        # --- Barra de progreso (oculta) ---
        progress = ttk.Progressbar(card, mode='indeterminate', bootstyle="success-striped")

        # --- Botón de Generar ---
        # Usamos una función lambda para pasar los widgets específicos de esta card
        btn_generar = ttk.Button(
            row, 
            text="Generar Excel", 
            bootstyle="success",
            command=lambda: self._handle_generate_click(
                combo_mes, spin_anio, btn_generar, progress, filename_prefix, export_method
            )
        )
        btn_generar.pack(side=LEFT)

    def _handle_generate_click_no_period(self, btn, progress, prefix, method):
        """Lógica genérica para el botón de generar"""

        filename = f"{prefix}_.xlsx"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")],
            initialfile=filename,
            title="Guardar Reporte"
        )

        if not filepath:
            return

        # Bloquear UI de esta card específica
        self._set_loading_state(True,  btn, progress)

        # Ejecutar en hilo separado
        thread = threading.Thread(
            target=self._run_export_logic, 
            args=(method, filepath,  btn, progress)
        )
        thread.start()

    def _handle_generate_click(self, combo_mes, spin_anio, btn, progress, prefix, method):
        """Lógica genérica para el botón de generar"""
        mes_txt = combo_mes.get()
        mes_num = mes_txt.split(" - ")[0]
        anio = spin_anio.get()

        filename = f"{prefix}_{anio}_{mes_num}.xlsx"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")],
            initialfile=filename,
            title="Guardar Reporte"
        )

        if not filepath:
            return

        # Bloquear UI de esta card específica
        self._set_loading_state(True, combo_mes, spin_anio, btn, progress)

        # Ejecutar en hilo separado
        thread = threading.Thread(
            target=self._run_export_logic, 
            args=(method, anio, mes_num, filepath, combo_mes, spin_anio, btn, progress)
        )
        thread.start()

    def _run_export_logic(self, method, year, month, filepath, *widgets):
        """Ejecuta la función del servicio recibida por parámetro"""
        try:
            # Llamamos al método que se pasó por argumento
            success, message = method(year, month, filepath)
        except Exception as e:
            success, message = False, f"Error inesperado: {str(e)}"
        
        # Volver al hilo principal para actualizar UI
        self.after(0, lambda: self._on_export_finished(success, message, *widgets))

    def _on_export_finished(self, success, message, combo_mes, spin_anio, btn, progress):
        self._set_loading_state(False, combo_mes, spin_anio, btn, progress)
        if success:
            messagebox.showinfo("Éxito", message)
        else:
            messagebox.showerror("Error", message)

    def _set_loading_state(self, is_loading, combo, spin, btn, progress):
        """Habilita o deshabilita los widgets de una card específica"""
        if is_loading:
            btn.config(state="disabled", text="Generando...")
            combo.config(state="disabled")
            spin.config(state="disabled")
            progress.pack(fill=X, pady=(10, 0))
            progress.start(10)
        else:
            progress.stop()
            progress.pack_forget()
            btn.config(state="normal", text="Generar Excel")
            combo.config(state="readonly")
            spin.config(state="normal")
    def _create_report_with_input_section(self, title, filename_prefix, export_method):
        """Crea una card que requiere cargar un archivo antes de generar"""
        card = ttk.Labelframe(self.main_container, text=title, padding=15)
        card.pack(fill=X, pady=10)

        # Fila 1: Selección de archivo
        row1 = ttk.Frame(card)
        row1.pack(fill=X, pady=(0, 10))
        
        lbl_file = ttk.Label(row1, text="Plantilla PERC Descargada (Programación Horas):", font=("Helvetica", 9, "italic"))
        lbl_file.pack(side=LEFT, padx=(0, 10))
        
        path_var = ttk.StringVar(value="No se ha seleccionado archivo...")
        entry_path = ttk.Entry(row1, textvariable=path_var, state="readonly", width=50)
        entry_path.pack(side=LEFT, padx=(0, 5))

        def select_input_file():
            path = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx *.xls")])
            if path:
                path_var.set(path)

        btn_browse = ttk.Button(row1, text="Buscar...", command=select_input_file, bootstyle="secondary-outline")
        btn_browse.pack(side=LEFT)

        # Fila 2: Periodo y Generar
        row2 = ttk.Frame(card)
        row2.pack(fill=X)

        ttk.Label(row2, text="Mes:").pack(side=LEFT, padx=(0, 5))
        #combo_mes = ttk.Combobox(row2, values=[f"{i:02d}" for i in range(1, 13)], width=5, state="readonly")
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
            row2, 
            text="Procesar y Guardar", 
            bootstyle="success",
            command=lambda: self._handle_generate_with_input(
                path_var.get(), combo_mes, spin_anio, btn_generar, progress, filename_prefix, export_method
            )
        )
        btn_generar.pack(side=LEFT)

    def _handle_generate_with_input(self, input_path, combo_mes, spin_anio, btn, progress, prefix, method):
        # Validar que seleccionó archivo
        if "No se ha seleccionado" in input_path or not input_path:
            messagebox.showwarning("Atención", "Por favor seleccione el archivo Excel de origen primero.")
            return

        mes_txt = combo_mes.get()
        mes_num = mes_txt.split(" - ")[0]
        anio = spin_anio.get()
        
        # Pedir donde GUARDAR
        filename = f"{prefix}_{anio}_{mes_num}.xlsx"
        output_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")],
            initialfile=filename,
            title="Guardar Resultado"
        )

        if not output_path: return

        # Bloquear UI
        self._set_loading_state(True, combo_mes, spin_anio, btn, progress)

        # Hilo
        thread = threading.Thread(
            target=self._run_export_logic_with_input, 
            args=(method, anio, mes_num, output_path, input_path, combo_mes, spin_anio, btn, progress)
        )
        thread.start()

    def _run_export_logic_with_input(self, method, year, month, output_path, input_path, *widgets):
        """Ejecuta la lógica pasando el input_path adicional"""
        try:
            # Aquí pasamos tanto el output_path como el input_path
            success, message = method(year, month, output_path, input_path)
        except Exception as e:
            success, message = False, f"Error: {str(e)}"
        
        self.after(0, lambda: self._on_export_finished(success, message, *widgets))