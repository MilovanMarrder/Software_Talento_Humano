import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from views.components.employee_selector import EmployeeSelector
from models.attendance_dao import AttendanceDAO
from tkinter.simpledialog import askfloat

class AttendanceView(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.pack(fill=BOTH, expand=True)
        self.dao = AttendanceDAO()
        
        # Estados
        self.current_emp_id = None
        self.contracts_map = [] # Guardará [(id, texto), ...] para mapear selección
        self.types_map = []     # Guardará [(id, texto), ...] para tipos
        
        self._setup_ui()
        self._load_initial_catalogs()

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
                self.current_emp_id, id_contrato, id_tipo, 
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