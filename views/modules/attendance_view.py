import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from datetime import datetime
from tkinter.simpledialog import askfloat

# Importaciones del proyecto
from views.components.employee_selector import EmployeeSelector
from models.attendance_dao import AttendanceDAO
from logics.time_calculator import TimeCalculator

class AttendanceView(ttk.Frame):
    def __init__(self, parent, controller=None):
        super().__init__(parent)
        self.pack(fill=BOTH, expand=True)
        self.controller = controller
        self.dao = AttendanceDAO() # Instancia local para datos directos
        
        # --- ESTADOS Y VARIABLES ---
        self.current_emp_id = None
        self.contracts_map = [] # [(id, texto), ...]
        self.types_map = []     # [(id, texto), ...]
        
        # Variables de Fecha (Con valores por defecto hoy)
        hoy = datetime.now().strftime("%Y-%m-%d")
        self.var_fecha_ini = ttk.StringVar(value=hoy)
        self.var_fecha_fin = ttk.StringVar(value=hoy)
        
        # Variables de Hora (Valores default jornada estándar)
        self.var_hora_ini = ttk.StringVar(value="08:00")
        self.var_hora_fin = ttk.StringVar(value="16:00")
        
        # Variable Lógica
        self.var_es_por_horas = ttk.BooleanVar(value=False)
        
        # Variable Cálculo (La que edita el usuario)
        self.var_dias_calculados = ttk.DoubleVar(value=0.0)

        # --- "ESPIAS" (Traces) ---
        # Detectan cambios en las fechas sin tocar el widget calendario (evita errores)
        self.var_fecha_ini.trace_add("write", self._on_dates_changed)
        self.var_fecha_fin.trace_add("write", self._on_dates_changed)

        # Construir Interfaz y Cargar Datos
        self._build_ui()
        self._load_initial_catalogs()

    def _build_ui(self):
        # TÍTULO
        ttk.Label(self, text="Gestión de Permisos, Vacaciones e Incapacidades", font=("Segoe UI", 18, "bold")).pack(pady=10)

        # 1. BARRA DE BÚSQUEDA
        search_frame = ttk.Labelframe(self, text="Colaborador", padding=10, bootstyle="info")
        search_frame.pack(fill=X, padx=10, pady=5)
        
        ttk.Button(search_frame, text="🔍 Buscar Empleado", command=self.open_search, bootstyle="info").pack(side=LEFT, padx=5)
        self.lbl_emp_info = ttk.Label(search_frame, text="Ningún colaborador seleccionado", font=("Segoe UI", 12))
        self.lbl_emp_info.pack(side=LEFT, padx=15)

        # CONTENEDOR PRINCIPAL (2 Columnas)
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)

        # --- COLUMNA IZQUIERDA: FORMULARIO ---
        form_frame = ttk.Labelframe(main_frame, text="Registrar Nueva Falta", padding=10, bootstyle="primary")
        form_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 5))

        # Contrato
        ttk.Label(form_frame, text="Aplicar al Contrato (Puesto):").pack(anchor=W, pady=(5,0))
        self.cb_contrato = ttk.Combobox(form_frame, state="readonly")
        self.cb_contrato.pack(fill=X, pady=5)
        self.cb_contrato.bind("<<ComboboxSelected>>", self.on_contract_change)

        self.lbl_saldo = ttk.Label(form_frame, text="Saldo Vacaciones: --", font=("Segoe UI", 10, "bold"), bootstyle="secondary")
        self.lbl_saldo.pack(anchor=E, pady=2)

        # Tipo Falta
        ttk.Label(form_frame, text="Tipo de Inasistencia:").pack(anchor=W, pady=(5,0))
        self.cb_tipo = ttk.Combobox(form_frame, state="readonly")
        self.cb_tipo.pack(fill=X, pady=5)

        # Switch Por Horas
        ttk.Checkbutton(
            form_frame, 
            text="Es un permiso por horas (mismo día)", 
            variable=self.var_es_por_horas, 
            command=self.toggle_hours_inputs,
            bootstyle="round-toggle"
        ).pack(anchor=W, pady=10)

        # --- SECCIÓN FECHAS ---
        lbl_fechas = ttk.Labelframe(form_frame, text="Periodo", padding=10)
        lbl_fechas.pack(fill=X, pady=5)

        # Fila Inicio
        row_ini = ttk.Frame(lbl_fechas)
        row_ini.pack(fill=X, pady=2)
        ttk.Label(row_ini, text="Desde:", width=8).pack(side=LEFT)
        self.date_ini = ttk.DateEntry(row_ini, dateformat="%Y-%m-%d", firstweekday=0)
        self.date_ini.entry.config(textvariable=self.var_fecha_ini)
        self.date_ini.pack(side=LEFT, fill=X, expand=True)

        # Fila Fin (Dinámica: Se oculta si es por horas)
        self.frame_fin = ttk.Frame(lbl_fechas)
        self.frame_fin.pack(fill=X, pady=2)
        ttk.Label(self.frame_fin, text="Hasta:", width=8).pack(side=LEFT)
        self.date_fin = ttk.DateEntry(self.frame_fin, dateformat="%Y-%m-%d", firstweekday=0)
        self.date_fin.entry.config(textvariable=self.var_fecha_fin)
        self.date_fin.pack(side=LEFT, fill=X, expand=True)

        # Fila Horas (Dinámica: Se muestra si es por horas)
        self.frame_horas = ttk.Frame(lbl_fechas)
        # No hacemos pack aquí, se hace en toggle_hours_inputs
        ttk.Label(self.frame_horas, text="Horario:", width=8).pack(side=LEFT)
        ttk.Entry(self.frame_horas, textvariable=self.var_hora_ini, width=8).pack(side=LEFT, padx=2)
        ttk.Label(self.frame_horas, text=" a ").pack(side=LEFT)
        ttk.Entry(self.frame_horas, textvariable=self.var_hora_fin, width=8).pack(side=LEFT, padx=2)

        # --- DÍAS CALCULADOS (Editable) ---
        row_calc = ttk.Frame(form_frame)
        row_calc.pack(fill=X, pady=15)
        
        ttk.Label(row_calc, text="Días a aplicar:", bootstyle="inverse-warning").pack(side=LEFT)
        
        self.spin_dias = ttk.Spinbox(
            row_calc, 
            textvariable=self.var_dias_calculados, 
            from_=0, to=365, increment=0.5, 
            width=10, 
            bootstyle="warning"
        )
        self.spin_dias.pack(side=LEFT, padx=10)
        ttk.Label(row_calc, text="(Puede editar este valor)", font=("Arial", 8, "italic")).pack(side=LEFT)

        # Detalle
        ttk.Label(form_frame, text="Observación / Detalle:").pack(anchor=W)
        self.entry_detalle = ttk.Entry(form_frame)
        self.entry_detalle.pack(fill=X, pady=5)

        # Botón Guardar
        ttk.Button(form_frame, text="GUARDAR REGISTRO", command=self._handle_save, bootstyle="success").pack(fill=X, pady=20)

        # Botón Ajuste Manual Saldo (Extra)
        ttk.Button(form_frame, text="Ajuste Manual Saldo", command=self.add_balance_manual, bootstyle="secondary-outline").pack(fill=X)

        # --- COLUMNA DERECHA: HISTORIAL ---
        hist_frame = ttk.Labelframe(main_frame, text="Historial Reciente", padding=10, bootstyle="secondary")
        hist_frame.pack(side=RIGHT, fill=BOTH, expand=True, padx=(5, 0))

        cols = ("id", "ini", "fin", "tipo", "puesto")
        self.tree = ttk.Treeview(hist_frame, columns=cols, show="headings", height=10)
        
        self.tree.heading("id", text="ID")
        self.tree.column("id", width=40, stretch=False)
        self.tree.heading("ini", text="Desde")
        self.tree.column("ini", width=90)
        self.tree.heading("fin", text="Hasta")
        self.tree.column("fin", width=90)
        self.tree.heading("tipo", text="Motivo")
        self.tree.heading("puesto", text="Puesto Afectado")
        
        self.tree.pack(fill=BOTH, expand=True)
        
        ttk.Button(hist_frame, text="Eliminar Seleccionado", command=self.delete_record, bootstyle="danger-outline").pack(anchor=E, pady=5)

    # --- LÓGICA DE NEGOCIO ---

    def _load_initial_catalogs(self):
        """Carga los tipos de inasistencia al iniciar"""
        self.types_map = self.dao.get_tipos_inasistencia_combo()
        self.cb_tipo['values'] = [x[1] for x in self.types_map]

    def open_search(self):
        EmployeeSelector(self, self.on_employee_selected)

    def on_employee_selected(self, emp_id, emp_code, emp_name):
        self.current_emp_id = emp_id
        self.lbl_emp_info.config(text=f"{emp_code} - {emp_name}", bootstyle="primary")
        
        # Cargar Contratos
        self.contracts_map = self.dao.get_active_contracts_by_employee(emp_id)
        
        if not self.contracts_map:
            Messagebox.show_warning("El empleado no tiene contratos activos.")
            self.cb_contrato.set('')
            self.cb_contrato['values'] = []
            self.cb_contrato.configure(state="disabled")
            self.lbl_saldo.config(text="Saldo: --")
        else:
            self.cb_contrato.configure(state="readonly")
            nombres_contratos = [c[1] for c in self.contracts_map]
            self.cb_contrato['values'] = nombres_contratos
            self.cb_contrato.current(0) 
            self.on_contract_change(None)
            
        self._refresh_history()

    def on_contract_change(self, event):
        txt_contrato = self.cb_contrato.get()
        if not txt_contrato: return
        
        id_contrato = next((x[0] for x in self.contracts_map if x[1] == txt_contrato), None)
        if id_contrato:
            saldo = self.dao.get_kardex_balance(id_contrato)
            color = "success" if saldo > 0 else "danger"
            self.lbl_saldo.config(text=f"Saldo Disponible: {saldo} días", bootstyle=color)

    def toggle_hours_inputs(self):
        """Alterna entre vista de Fechas (Días) y Vista de Horas"""
        if self.var_es_por_horas.get():
            # MODO HORAS
            self.frame_fin.pack_forget() # Ocultar fecha fin
            self.frame_horas.pack(fill=X, pady=2) # Mostrar horas
            # En modo horas, sugerimos 0 días por defecto (se calcula diferente) o dejamos que calculen fracción
            self.var_dias_calculados.set(0.0) 
        else:
            # MODO DÍAS
            self.frame_horas.pack_forget()
            self.frame_fin.pack(fill=X, pady=2)
            # Recalcular días inmediatamente
            self._on_dates_changed()

    def _on_dates_changed(self, *args):
        """Calcula duración automáticamente al escribir/seleccionar fechas"""
        if self.var_es_por_horas.get():
            return 

        f_ini = self.var_fecha_ini.get()
        f_fin = self.var_fecha_fin.get()
        
        # Evitar cálculos con fechas incompletas
        if len(f_ini) < 10 or len(f_fin) < 10: return

        try:
            dias_sugeridos = TimeCalculator.calculate_duration(
                fecha_ini=f_ini, fecha_fin=f_fin, es_por_horas=False
            )
            self.var_dias_calculados.set(dias_sugeridos)
        except Exception:
            pass 

    def _handle_save(self):
        """Proceso unificado de guardado"""
        # 1. Validaciones Básicas
        if not self.current_emp_id: return Messagebox.show_warning("Seleccione un empleado.")
        if not self.cb_contrato.get(): return Messagebox.show_warning("Seleccione un contrato.")
        if not self.cb_tipo.get(): return Messagebox.show_warning("Seleccione el tipo de inasistencia.")

        # 2. Obtener IDs
        txt_contrato = self.cb_contrato.get()
        id_contrato = next((x[0] for x in self.contracts_map if x[1] == txt_contrato), None)
        
        txt_tipo = self.cb_tipo.get()
        id_tipo = next((x[0] for x in self.types_map if x[1] == txt_tipo), None)

        # 3. Obtener Datos de Tiempo
        es_por_horas = self.var_es_por_horas.get()
        f_ini = self.var_fecha_ini.get()
        f_fin = self.var_fecha_fin.get() if not es_por_horas else f_ini
        
        h_ini = self.var_hora_ini.get() if es_por_horas else "00:00"
        h_fin = self.var_hora_fin.get() if es_por_horas else "00:00"

        # 4. Validar Fecha Lógica
        if not es_por_horas and f_ini > f_fin:
             return Messagebox.show_error("La fecha de inicio no puede ser posterior a la fecha fin.")

        # 5. OBTENER DÍAS MANUALES (El punto crítico)
        try:
            dias_finales = float(self.var_dias_calculados.get())
        except ValueError:
            return Messagebox.show_error("El número de días no es válido.")

        # Confirmación si es 0
        if dias_finales == 0 and not es_por_horas:
            if Messagebox.show_question("¿Guardar registro con 0 días?", "Confirmar") != 'Yes':
                return

        detalle = self.entry_detalle.get() or "Sin observación"

        # 6. LLAMADA AL DAO (Pasando dias_manual)
        success, message = self.dao.insert_inasistencia(
            id_con=id_contrato,
            id_tipo=id_tipo,
            f_ini=f_ini,
            f_fin=f_fin,
            es_horas=es_por_horas,
            h_ini=h_ini,
            h_fin=h_fin,
            detalle=detalle,
            dias_manual=dias_finales # <--- AQUÍ SE ENVÍA LO QUE EL USUARIO EDITÓ
        )

        if success:
            Messagebox.show_info(message, "Éxito")
            self.entry_detalle.delete(0, END)
            self._refresh_history()
            self.on_contract_change(None) # Actualizar saldo
        else:
            Messagebox.show_error(message, "Error de Base de Datos")

    def _refresh_history(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        if not self.current_emp_id: return

        rows = self.dao.get_history_by_employee(self.current_emp_id)
        for r in rows:
            self.tree.insert("", END, values=r[:5])

    def delete_record(self):
        sel = self.tree.selection()
        if not sel: return
        
        id_inasistencia = self.tree.item(sel[0])['values'][0]
        
        if Messagebox.yesno("¿Eliminar este registro y revertir el saldo?", "Confirmar") == 'Yes':
            ok, msg = self.dao.delete_inasistencia(id_inasistencia)
            if ok:
                self._refresh_history()
                self.on_contract_change(None) 
            else:
                Messagebox.show_error(msg, "Error")

    def add_balance_manual(self):
        txt_contrato = self.cb_contrato.get()
        if not txt_contrato: return Messagebox.show_warning("Seleccione contrato primero")
        
        id_contrato = next((x[0] for x in self.contracts_map if x[1] == txt_contrato), None)
        
        dias = askfloat("Ajuste Manual", "Ingrese días a sumar (Saldo Inicial):", parent=self)
        if dias is not None:
            ok, msg = self.dao.insert_kardex_manual(id_contrato, "SALDO_INICIAL", dias, "Carga Manual UI")
            if ok:
                Messagebox.show_info("Saldo actualizado", "Éxito")
                self.on_contract_change(None)