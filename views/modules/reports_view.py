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
        # CAMBIO 1: Vinculamos al método real del servicio
        self._create_report_section_attemporal(
            title="Descargar Base de Datos Completa",
            filename_prefix="BACKUP_RRHH_FULL",
            export_method=self.service.export_database_to_excel 
        )

# --------------------------------------------------
        # SECCIÓN DE MANTENIMIENTO (IMPORTACIÓN)
        # --------------------------------------------------
        # Separador visual
        ttk.Separator(self.main_container, orient=HORIZONTAL).pack(fill=X, pady=20)
        # lbl_danger = ttk.Label(self.main_container, text="Zona de Peligro - Restauración", font=("Helvetica", 12, "bold"), bootstyle="danger")
        # lbl_danger.pack(anchor="w", pady=(0, 10))

        self._create_import_section()

#----------------------------------------------FIN-SECCIÓN DE REPORTES-------------------------------------------

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










# --------------------------- Códgio nuevo . 


    def _create_report_section_attemporal(self, title, filename_prefix, export_method):
        """Caja de reporte SIN periodo (Corrección del Handler)"""
        card = ttk.Labelframe(self.main_container, text=title, padding=15)
        card.pack(fill=X, pady=10, anchor="n")

        row = ttk.Frame(card)
        row.pack(fill=X)
        
        progress = ttk.Progressbar(card, mode='indeterminate', bootstyle="success-striped")

        btn_generar = ttk.Button(
            row, 
            text="Exportar Todo a Excel", 
            bootstyle="warning", # Cambié a warning para destacar que es una descarga masiva
            command=lambda: self._handle_generate_click_no_period(
              btn_generar, progress, filename_prefix, export_method
            )
        )
        btn_generar.pack(side=LEFT)

    def _handle_generate_click_no_period(self, btn, progress, prefix, method):
        """Maneja el clic para reportes sin fecha"""
        # Generar nombre con timestamp para evitar sobreescritura
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"{prefix}_{timestamp}.xlsx"
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")],
            initialfile=filename,
            title="Guardar Base de Datos"
        )

        if not filepath:
            return

        self._set_loading_state(True, btn, progress)

        # CAMBIO 2: Llamamos a un runner simplificado, NO a _run_export_logic
        thread = threading.Thread(
            target=self._run_simple_export_logic, 
            args=(method, filepath, btn, progress)
        )
        thread.start()

    # --- NUEVO MÉTODO RUNNER (Para evitar el error de argumentos) ---
    def _run_simple_export_logic(self, method, filepath, *widgets):
        """Ejecuta métodos que solo requieren filepath"""
        try:
            success, message = method(filepath)
        except Exception as e:
            success, message = False, f"Error inesperado: {str(e)}"
        
        self.after(0, lambda: self._on_export_finished_simple(success, message, *widgets))

    # --- NUEVO MÉTODO FINISHER (Simplificado) ---
    def _on_export_finished_simple(self, success, message, btn, progress):
        """Restaura la UI después de exportar"""
        progress.stop()
        progress.pack_forget()
        btn.config(state="normal", text="Exportar Todo a Excel")
        
        if success:
            messagebox.showinfo("Éxito", message)
        else:
            messagebox.showerror("Error", message)

    # ... (resto de métodos: _set_loading_state, etc. ajustados para soportar widgets opcionales) ...
    
    def _set_loading_state(self, is_loading, *args):
        """
        Versión polimórfica de _set_loading_state.
        Detecta qué widgets llegaron para deshabilitarlos.
        """
        # El último argumento siempre es la barra de progreso
        progress = args[-1] 
        # El penúltimo es el botón
        btn = args[-2] 

        if is_loading:
            btn.config(state="disabled", text="Procesando...")
            progress.pack(fill=X, pady=(10, 0))
            progress.start(10)
            
            # Si hay más argumentos (Combos/Spins), los deshabilitamos
            for w in args[:-2]:
                try: w.config(state="disabled")
                except: pass
        else:
            progress.stop()
            progress.pack_forget()
            btn.config(state="normal") # El texto se restaura en el finisher específico
            
            for w in args[:-2]:
                try: 
                    if isinstance(w, ttk.Combobox): w.config(state="readonly")
                    else: w.config(state="normal")
                except: pass


    # --- NUEVO MÉTODO PARA UI DE IMPORTACIÓN ---
    def _create_import_section(self):
        """Crea la tarjeta para importar/restaurar la BD"""
        card = ttk.Labelframe(self.main_container, text="Restaurar Base de Datos desde Excel", padding=15, bootstyle="danger")
        card.pack(fill=X, pady=10, anchor="n")

        row = ttk.Frame(card)
        row.pack(fill=X)

        lbl_info = ttk.Label(row, text="⚠ ADVERTENCIA: Esta acción borrará todos los datos actuales y los reemplazará con los del Excel.", bootstyle="danger")
        lbl_info.pack(side=LEFT, padx=(0, 20))

        progress = ttk.Progressbar(card, mode='indeterminate', bootstyle="danger-striped")

        btn_importar = ttk.Button(
            row, 
            text="Seleccionar Archivo y Restaurar", 
            bootstyle="danger",
            command=lambda: self._handle_import_click(btn_importar, progress)
        )
        btn_importar.pack(side=RIGHT)

    def _handle_import_click(self, btn, progress):
        """Manejador del botón importar"""
        # 1. Confirmación de seguridad
        confirm = messagebox.askyesno(
            "Confirmación Crítica", 
            "¿Está SEGURO de que desea restaurar la base de datos?\n\n"
            "Esto ELIMINARÁ PERMANENTEMENTE los datos actuales y cargará los del archivo Excel.\n"
            "Esta acción no se puede deshacer.",
            icon='warning'
        )
        if not confirm:
            return

        # 2. Seleccionar archivo
        input_path = filedialog.askopenfilename(
            filetypes=[("Excel Files", "*.xlsx *.xls")],
            title="Seleccionar archivo de respaldo (Backup)"
        )
        if not input_path:
            return

        # 3. Bloquear UI
        self._set_loading_state(True, btn, progress) # Reutilizamos tu método polimórfico existente

        # 4. Hilo
        thread = threading.Thread(
            target=self._run_import_logic,
            args=(input_path, btn, progress)
        )
        thread.start()

    def _run_import_logic(self, input_path, btn, progress):
        """Ejecuta la importación en segundo plano"""
        try:
            success, message = self.service.import_database_from_excel(input_path)
        except Exception as e:
            success, message = False, f"Error inesperado: {str(e)}"
        
        self.after(0, lambda: self._on_import_finished(success, message, btn, progress))

    def _on_import_finished(self, success, message, btn, progress):
        """Restaura UI tras importar"""
        self._set_loading_state(False, btn, progress)
        
        if success:
            messagebox.showinfo("Restauración Exitosa", message)
            # Opcional: Sugerir reiniciar la app para refrescar todas las vistas cacheadas
        else:
            messagebox.showerror("Error en Restauración", message)