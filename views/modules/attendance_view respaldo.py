import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from views.components.employee_selector import EmployeeSelector
from models.attendance_dao import AttendanceDAO
from tkinter.simpledialog import askfloat
from datetime import datetime
from logics.time_calculator import TimeCalculator

class AttendanceView(ttk.Frame):
    # def __init__(self, parent):
    #     # super().__init__(parent)
    #     # self.pack(fill=BOTH, expand=True)
    #     # self.dao = AttendanceDAO()
        
    #     # # Estados
    #     # self.current_emp_id = None
    #     # self.contracts_map = [] # Guardará [(id, texto), ...] para mapear selección
    #     # self.types_map = []     # Guardará [(id, texto), ...] para tipos
        
    #     # self._setup_ui()
    #     # self._load_initial_catalogs()
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        # Variables de control
        self.var_fecha_ini = ttk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self.var_fecha_fin = ttk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        
        # VARIABLE CLAVE: Días a aplicar (Editable)
        self.var_dias_calculados = ttk.DoubleVar(value=0.0) 
        
        # Variable para controlar si es por horas o días (Asumo que ya tienes esto)
        self.var_es_por_horas = ttk.BooleanVar(value=False)

        self._build_ui()



    def _setup_ui(self):
        # TÍTULO
        ttk.Label(self, text="Gestión de Inasistencias, Permisos e Incapacidades", font=("Segoe UI", 18, "bold")).pack(pady=10)

        # 1. BARRA DE BÚSQUEDA (Top)
        search_frame = ttk.Labelframe(self, text="Colaborador", padding=10, bootstyle="info")
        search_frame.pack(fill=X, padx=10, pady=5)
        
        ttk.Button(search_frame, text="🔍 Buscar Empleado", command=self.open_search, bootstyle="info").pack(side=LEFT, padx=5)
        self.lbl_emp_info = ttk.Label(search_frame, text="Ningún colaborador seleccionado", font=("Segoe UI", 12))
        self.lbl_emp_info.pack(side=LEFT, padx=15)

        # CONTENEDOR PRINCIPAL (2 Columnas: Formulario | Historial)
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)

        # --- COLUMNA IZQUIERDA: FORMULARIO DE REGISTRO ---
        form_frame = ttk.Labelframe(main_frame, text="Registrar Nueva Falta", padding=10, bootstyle="primary")
        form_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 5))

        # Contrato
        ttk.Label(form_frame, text="Aplicar al Contrato (Puesto):").pack(anchor=W, pady=(5,0))
        self.cb_contrato = ttk.Combobox(form_frame, state="readonly")
        self.cb_contrato.pack(fill=X, pady=5)
        # Evento: Al cambiar contrato, actualizar saldo
        self.cb_contrato.bind("<<ComboboxSelected>>", self.on_contract_change)

        # --- NUEVO: LABEL DE SALDO ---
        self.lbl_saldo = ttk.Label(form_frame, text="Saldo Vacaciones: --", font=("Segoe UI", 10, "bold"), bootstyle="secondary")
        self.lbl_saldo.pack(anchor=E, pady=2)


        # Tipo Falta
        ttk.Label(form_frame, text="Tipo de Inasistencia:").pack(anchor=W, pady=(10,0))
        self.cb_tipo = ttk.Combobox(form_frame, state="readonly")
        self.cb_tipo.pack(fill=X, pady=5)



        # --- SECCIÓN FECHAS Y HORAS ---
        dates_frame = ttk.Frame(form_frame)
        dates_frame.pack(fill=X, pady=10)
        
        # Checkbox "Por Horas"
        self.var_por_horas = ttk.BooleanVar(value=False)
        ttk.Checkbutton(dates_frame, text="¿Es permiso por horas?", variable=self.var_por_horas, command=self.toggle_hours_inputs).pack(anchor=W, pady=(0, 5))

        # Contenedor Fechas
        f_fechas = ttk.Frame(dates_frame)
        f_fechas.pack(fill=X)
        
        # Fecha Inicio
        f1 = ttk.Frame(f_fechas)
        f1.pack(side=LEFT, fill=X, expand=True)
        ttk.Label(f1, text="Fecha:").pack(anchor=W)
        self.date_ini = ttk.DateEntry(f1, dateformat='%Y-%m-%d', width=12)
        self.date_ini.pack(anchor=W)

        # Fecha Fin (Se ocultará si es por horas)
        self.frame_fin = ttk.Frame(f_fechas)
        self.frame_fin.pack(side=LEFT, fill=X, expand=True, padx=5)
        ttk.Label(self.frame_fin, text="Hasta Fecha:").pack(anchor=W)
        self.date_fin = ttk.DateEntry(self.frame_fin, dateformat='%Y-%m-%d', width=12)
        self.date_fin.pack(anchor=W)

        # --- CAMPOS DE HORA (Inicialmente ocultos) ---
        self.frame_horas = ttk.Frame(dates_frame)
        # No hacemos pack aquí, lo hacemos en toggle
        
        # Hora Inicio
        fh1 = ttk.Frame(self.frame_horas)
        fh1.pack(side=LEFT, fill=X, expand=True)
        ttk.Label(fh1, text="Hora Inicio (HH:MM):").pack(anchor=W)
        self.entry_hora_ini = ttk.Entry(fh1, width=10)
        self.entry_hora_ini.insert(0, "08:00")
        self.entry_hora_ini.pack(anchor=W)

        # Hora Fin
        fh2 = ttk.Frame(self.frame_horas)
        fh2.pack(side=LEFT, fill=X, expand=True, padx=5)
        ttk.Label(fh2, text="Hora Fin (HH:MM):").pack(anchor=W)
        self.entry_hora_fin = ttk.Entry(fh2, width=10)
        self.entry_hora_fin.insert(0, "16:00")
        self.entry_hora_fin.pack(anchor=W)

        # Detalle
        ttk.Label(form_frame, text="Detalle / Observación:").pack(anchor=W, pady=(10,0))
        self.entry_detalle = ttk.Entry(form_frame)
        self.entry_detalle.pack(fill=X, pady=5)

        # Botón Guardar
        ttk.Button(form_frame, text="Registrar Inasistencia", command=self.save, bootstyle="success").pack(fill=X, pady=20)


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
        
        # Botón Eliminar Historial
        ttk.Button(hist_frame, text="Eliminar Registro Seleccionado", command=self.delete_record, bootstyle="danger-outline").pack(anchor=E, pady=5)


    def _load_initial_catalogs(self):
        # Cargar Tipos de Inasistencia
        self.types_map = self.dao.get_tipos_inasistencia_combo()
        self.cb_tipo['values'] = [x[1] for x in self.types_map]

    def open_search(self):
        EmployeeSelector(self, self.on_employee_selected)

# views/modules/attendance_view.py

    # ... dentro de AttendanceView ...

    def on_employee_selected(self, emp_id, emp_code, emp_name):
        self.current_emp_id = emp_id
        self.lbl_emp_info.config(text=f"{emp_code} - {emp_name}", bootstyle="primary")
        
        # 1. Cargar Contratos
        self.contracts_map = self.dao.get_active_contracts_by_employee(emp_id)
        
        if not self.contracts_map:
            Messagebox.show_warning("El empleado no tiene contratos activos.")
            self.cb_contrato.set('')
            self.cb_contrato['values'] = []
            self.cb_contrato.configure(state="disabled")
            self.lbl_saldo.config(text="Saldo: --") # Limpiar saldo
        else:
            self.cb_contrato.configure(state="readonly")
            nombres_contratos = [c[1] for c in self.contracts_map]
            self.cb_contrato['values'] = nombres_contratos
            
            # --- MEJORA UX (Punto A): Auto-seleccionar y mostrar saldo ---
            self.cb_contrato.current(0) 
            self.on_contract_change(None) # <--- Forzamos el evento manualmente
            
        # 2. Cargar Historial
        self._refresh_history()

    def on_contract_change(self, event):
        txt_contrato = self.cb_contrato.get()
        if not txt_contrato: return
        
        id_contrato = next((x[0] for x in self.contracts_map if x[1] == txt_contrato), None)
        
        if id_contrato:
            # Solo pedimos un saldo (el ordinario)
            saldo = self.dao.get_kardex_balance(id_contrato)
            
            # Feedback visual
            color = "success" if saldo > 0 else "danger"
            self.lbl_saldo.config(text=f"Saldo Disponible: {saldo} días", bootstyle=color)

    def _refresh_history(self):
        # Limpiar
        for item in self.tree.get_children(): self.tree.delete(item)
        if not self.current_emp_id: return

        rows = self.dao.get_history_by_employee(self.current_emp_id)
        for r in rows:
            # r = (id, ini, fin, tipo, puesto, estado)
            # Mostramos en tabla
            self.tree.insert("", END, values=r[:5]) # Omitimos estado por espacio si queremos

    def save(self):
            if not self.current_emp_id: return Messagebox.show_warning("Falta empleado")
            if not self.cb_contrato.get(): return Messagebox.show_warning("Falta contrato")
            if not self.cb_tipo.get(): return Messagebox.show_warning("Falta tipo")

            # IDs
            txt_contrato = self.cb_contrato.get()
            id_contrato = next((x[0] for x in self.contracts_map if x[1] == txt_contrato), None)
            
            txt_tipo = self.cb_tipo.get()
            id_tipo = next((x[0] for x in self.types_map if x[1] == txt_tipo), None)

            # DATOS TIEMPO
            es_por_horas = self.var_por_horas.get()
            fecha_ini = self.date_ini.entry.get()
            
            if es_por_horas:
                fecha_fin = fecha_ini # En permisos por hora, inicio=fin
                hora_ini = self.entry_hora_ini.get()
                hora_fin = self.entry_hora_fin.get()
                # Validación simple de formato hora
                if len(hora_ini) != 5 or len(hora_fin) != 5:
                    return Messagebox.show_error("Formato de hora incorrecto (Use HH:MM)")
            else:
                fecha_fin = self.date_fin.entry.get()
                hora_ini = "00:00" # Defaults
                hora_fin = "00:00"
                if fecha_ini > fecha_fin:
                    return Messagebox.show_error("La fecha inicio no puede ser mayor a la fin.")

            detalle = self.entry_detalle.get()

            # DAO CALL
            ok, msg = self.dao.insert_inasistencia(
                id_contrato, id_tipo, 
                fecha_ini, fecha_fin, 
                es_por_horas, hora_ini, hora_fin, # NUEVOS PARAMS
                detalle
            )

            if ok:
                Messagebox.show_info(msg, "Registrado")
                self.entry_detalle.delete(0, END)
                self._refresh_history()
                self.on_contract_change(None) 
            else:
                Messagebox.show_error(msg, "Error")

    def delete_record(self):
        sel = self.tree.selection()
        if not sel: return
        
        id_inasistencia = self.tree.item(sel[0])['values'][0]
        
        if Messagebox.yesno("¿Eliminar este registro?", "Confirmar") == 'Yes':
            ok, msg = self.dao.delete_inasistencia(id_inasistencia)
            if ok:
                self._refresh_history()
                self.on_contract_change(None) 
            else:
                Messagebox.show_error(msg, "Error")

    def toggle_hours_inputs(self):
        if self.var_por_horas.get():
            # MODO HORAS: Ocultar Fecha Fin, Mostrar Horas
            self.frame_fin.pack_forget()
            self.frame_horas.pack(fill=X, pady=5)
        else:
            # MODO DÍAS: Mostrar Fecha Fin, Ocultar Horas
            self.frame_horas.pack_forget()
            self.frame_fin.pack(side=LEFT, fill=X, expand=True, padx=5)

    

    def add_balance_manual(self):
        txt_contrato = self.cb_contrato.get()
        if not txt_contrato: return Messagebox.show_warning("Seleccione contrato")
        
        id_contrato = next((x[0] for x in self.contracts_map if x[1] == txt_contrato), None)
        
        # Popup simple
        dias = askfloat("Ajuste Manual", "Ingrese días a sumar (Saldo Inicial):", parent=self)
        
        if dias is not None:
            ok, msg = self.dao.insert_kardex_manual(id_contrato, "SALDO_INICIAL", dias, "Carga Manual")
            if ok:
                Messagebox.show_info("Saldo actualizado", "Éxito")
                self.on_contract_change(None)

    # Fragmento para la lógica de guardado en AttendanceView

    def calcular_dias_automaticos(self):
        f_ini = self.fecha_inicio.get()
        f_fin = self.fecha_fin.get()
        
        # Llamamos a tu TimeCalculator
        dias_sistema = self.time_calculator.calculate_duration(f_ini, f_fin)
        
        # Regla 1: Predefinir el valor con el cálculo del sistema
        self.dias_usuario_var.set(dias_sistema)
        self.limite_sistema = dias_sistema # Guardamos el "techo"

    def validar_y_guardar(self):
        try:
            valor_final = float(self.dias_usuario_var.get())
            
            # Regla 2: El usuario solo puede establecer un valor MENOR o IGUAL
            if valor_final > self.limite_sistema:
                Messagebox.showerror(
                    "Error de Validación",
                    f"No se permite registrar {valor_final} días.\n"
                    f"El máximo calculado para estas fechas es {self.limite_sistema}."
                )
                return

            # Regla 4: Mensaje de confirmación si es menor
            if valor_final < self.limite_sistema:
                msg = f"El sistema calculó {self.limite_sistema} días, pero usted está guardando {valor_final}. ¿Desea continuar?"
                if not Messagebox.askyesno("Confirmar ajuste manual", msg):
                    return

            # Si pasa las validaciones, procedemos al DAO
            self.proceder_al_guardado(valor_final)
            
        except ValueError:
            Messagebox.showerror("Error", "Por favor ingrese un número válido de días.")




# -------------------------------------------

class AttendanceView(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        # Variables de control
        self.var_fecha_ini = ttk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self.var_fecha_fin = ttk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        
        # VARIABLE CLAVE: Días a aplicar (Editable)
        self.var_dias_calculados = ttk.DoubleVar(value=0.0) 
        
        # Variable para controlar si es por horas o días (Asumo que ya tienes esto)
        self.var_es_por_horas = ttk.BooleanVar(value=False)

        self._build_ui()
        
    def _build_ui(self):
        # ... (Código previo de tu formulario) ...

        # --- SECCIÓN DE FECHAS ---
        lbl_fechas = ttk.Labelframe(self, text="Periodo de Inasistencia", padding=10)
        lbl_fechas.pack(fill=X, pady=10)

        # Fecha Inicio
        ttk.Label(lbl_fechas, text="Desde:").grid(row=0, column=0, padx=5)
        self.date_ini = ttk.DateEntry(lbl_fechas, dateformat="%Y-%m-%d", firstweekday=0)
        self.date_ini.entry.config(textvariable=self.var_fecha_ini)
        self.date_ini.grid(row=0, column=1, padx=5)
        
        # EVENTO: Cuando cambia la fecha, recalculamos
        self.date_ini.entry.bind("<FocusOut>", self._on_dates_changed)
        self.date_ini.calendar.bind("<<CalendarSelected>>", self._on_date_selected_calendar)

        # Fecha Fin
        ttk.Label(lbl_fechas, text="Hasta:").grid(row=0, column=2, padx=5)
        self.date_fin = ttk.DateEntry(lbl_fechas, dateformat="%Y-%m-%d", firstweekday=0)
        self.date_fin.entry.config(textvariable=self.var_fecha_fin)
        self.date_fin.grid(row=0, column=3, padx=5)
        
        # EVENTO: Cuando cambia la fecha fin
        self.date_fin.entry.bind("<FocusOut>", self._on_dates_changed)
        self.date_fin.calendar.bind("<<CalendarSelected>>", self._on_date_selected_calendar)

        # --- SECCIÓN DE DURACIÓN (EL CAMBIO CLAVE) ---
        row_duracion = ttk.Frame(self)
        row_duracion.pack(fill=X, pady=10)

        ttk.Label(row_duracion, text="Días a Descontar/Pagar:").pack(side=LEFT, padx=5)
        
        # Usamos Spinbox para permitir edición fácil pero sugiriendo números
        self.spin_dias = ttk.Spinbox(
            row_duracion, 
            textvariable=self.var_dias_calculados, 
            from_=0, 
            to=365, 
            increment=1,
            width=10,
            bootstyle="warning" # Color visual para indicar "Atención, verifica este dato"
        )
        self.spin_dias.pack(side=LEFT, padx=5)
        
        ttk.Label(row_duracion, text="(Puede editar este valor manualmente)", font=("Arial", 8, "italic")).pack(side=LEFT)

        # Botón Guardar
        btn_save = ttk.Button(self, text="Guardar Registro", command=self._save_record, bootstyle="success")
        btn_save.pack(pady=20)

    # --- MÉTODOS DE LÓGICA DE UI ---

    def _on_date_selected_calendar(self, event):
        """Wrapper porque el evento del calendario a veces necesita un pequeño delay o manejo de string"""
        self.after(50, self._on_dates_changed)

    def _on_dates_changed(self, event=None):
        """
        Calcula la duración sugerida basada en fechas y actualiza el campo editable.
        SOLO lo hace si NO estamos en modo 'Por Horas'.
        """
        if self.var_es_por_horas.get():
            return # Si es por horas, la lógica es distinta (intra-día)

        f_ini = self.date_ini.entry.get()
        f_fin = self.date_fin.entry.get()

        # Usamos tu lógica existente en TimeCalculator
        dias_sugeridos = TimeCalculator.calculate_duration(
            fecha_ini=f_ini,
            fecha_fin=f_fin,
            es_por_horas=False
        )

        # Actualizamos la vista con la sugerencia, pero el usuario puede borrarla luego
        self.var_dias_calculados.set(dias_sugeridos)

    def _save_record(self):
        # 1. Obtenemos el valor FINAL que decidió el usuario
        try:
            dias_finales = float(self.var_dias_calculados.get())
        except ValueError:
            Messagebox.show_error("El valor de días debe ser un número válido.", "Error de Validación")
            return

        # 2. Validaciones Lógicas
        if dias_finales <= 0:
            # Quizás permitas 0 para registros informativos, pero usualmente es un error
            if Messagebox.show_question("¿Está registrando una inasistencia de 0 días? ¿Desea continuar?", "Advertencia") != "Yes":
                return

        # 3. Empaquetar datos para el controlador/DAO
        attendance_data = {
            # ... otros campos (id_empleado, tipo, etc.)
            "fecha_inicio": self.date_ini.entry.get(),
            "fecha_fin": self.date_fin.entry.get(),
            "dias_aplicados": dias_finales, # <--- ENVIAMOS LO QUE ESCRIBIÓ EL USUARIO
            "es_por_horas": self.var_es_por_horas.get()
        }
        
        # 4. Llamar al controlador para guardar
        # self.controller.create_attendance(attendance_data) 
        print(f"Guardando registro con: {dias_finales} días.")