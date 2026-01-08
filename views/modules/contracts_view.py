import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from views.components.employee_selector import EmployeeSelector
from models.contract_dao import ContractDAO
from models.catalogs_dao import CatalogsDAO
from views.components.contract_selector import ContractSelector 

class ContractsView(ttk.Frame):
    def __init__(self, parent, controller=None):
        super().__init__(parent)
        self.controller = controller
        self.dao = ContractDAO()
        self.cat_dao = CatalogsDAO()
        
        self.selected_contract_id = None 
        self.current_employee_id = None
        self.cost_distribution_list = [] 
        self.var_indefinido = ttk.BooleanVar(value=True) 
        
        # MEMORIA DE CATALOGOS (Para filtrado local)
        self.all_puestos = [] # Lista completa [(id, nombre, depto_nombre, ..., id_depto), ...]
        self.deptos_data = [] # Lista [(id, nombre), ...]

        self.pack(fill=BOTH, expand=True)
        self._create_ui()
        self._load_catalogs()
        self.toggle_fecha_fin()

    def _create_ui(self):
        main_content = ttk.Frame(self)
        main_content.pack(fill=BOTH, expand=True)

        # --- A: BUSCADOR ---
        search_frame = ttk.Labelframe(main_content, text="1. Colaborador", padding=10, bootstyle="info")
        search_frame.pack(fill=X, padx=10, pady=5)
        
        self.btn_search = ttk.Button(search_frame, text="🔍 Buscar Empleado", command=self.open_search_modal, bootstyle="info")
        self.btn_search.pack(side=LEFT, padx=5)
        
        self.lbl_employee_name = ttk.Label(search_frame, text="Seleccione un colaborador...", font=("Segoe UI", 11, "bold"))
        self.lbl_employee_name.pack(side=LEFT, padx=20)

        # --- B: DATOS CONTRATO (Lógica Modificada) ---
        details_frame = ttk.Labelframe(main_content, text="2. Datos Contractuales", padding=10, bootstyle="primary")
        details_frame.pack(fill=X, padx=10, pady=5)
        
        # Fila 0: DEPARTAMENTO (Ahora es el driver)
        ttk.Label(details_frame, text="Departamento:").grid(row=0, column=0, padx=5, pady=5, sticky=E)
        self.cb_depto = ttk.Combobox(details_frame, state="readonly", width=35)
        self.cb_depto.grid(row=0, column=1, padx=5, pady=5)
        self.cb_depto.bind("<<ComboboxSelected>>", self._on_depto_changed) # <--- EVENTO CLAVE

        # Fila 0: PUESTO (Ahora es esclavo del depto)
        ttk.Label(details_frame, text="Puesto (Filtrado):").grid(row=0, column=2, padx=5, pady=5, sticky=E)
        self.cb_puesto = ttk.Combobox(details_frame, state="readonly", width=35)
        self.cb_puesto.grid(row=0, column=3, padx=5, pady=5)
        
        # Fila 1
        ttk.Label(details_frame, text="Tipo Contrato:").grid(row=1, column=0, padx=5, pady=5, sticky=E)
        self.cb_tipo = ttk.Combobox(details_frame, state="readonly", width=35)
        self.cb_tipo.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(details_frame, text="Jornada:").grid(row=1, column=2, padx=5, pady=5, sticky=E)
        self.cb_jornada = ttk.Combobox(details_frame, state="readonly", width=35)
        self.cb_jornada.grid(row=1, column=3, padx=5, pady=5)
        
        # Fila 2
        ttk.Label(details_frame, text="Salario Base:").grid(row=2, column=0, padx=5, pady=5, sticky=E)
        self.entry_salario = ttk.Entry(details_frame, width=35)
        self.entry_salario.grid(row=2, column=1, padx=5, pady=5)

        # Fila 3: Vacaciones
        ttk.Label(details_frame, text="Inicio Contab. Vacaciones:", bootstyle="inverse-primary").grid(row=3, column=0, padx=5, pady=5, sticky=E)
        self.date_kardex = ttk.DateEntry(details_frame, dateformat='%Y-%m-%d')
        self.date_kardex.grid(row=3, column=1, padx=5, pady=5, sticky=W)
        
        ttk.Label(details_frame, text="Saldo Inicial (Días):", bootstyle="inverse-primary").grid(row=3, column=2, padx=5, pady=5, sticky=E)
        self.entry_saldo_ini = ttk.Entry(details_frame, width=10)
        self.entry_saldo_ini.insert(0, "0")
        self.entry_saldo_ini.grid(row=3, column=3, padx=5, pady=5, sticky=W)

        # Fila 4: Fechas
        ttk.Label(details_frame, text="Fecha Inicio:").grid(row=4, column=0, padx=5, pady=5, sticky=E)
        self.date_inicio = ttk.DateEntry(details_frame, dateformat='%Y-%m-%d')
        self.date_inicio.grid(row=4, column=1, padx=5, pady=5, sticky=W)
        
        ttk.Label(details_frame, text="Fecha Fin:").grid(row=4, column=2, padx=5, pady=5, sticky=E)
        self.date_fin = ttk.DateEntry(details_frame, dateformat='%Y-%m-%d', startdate=None)
        self.date_fin.grid(row=4, column=3, padx=5, pady=5, sticky=W)
        
        ttk.Checkbutton(details_frame, text="Indefinido", variable=self.var_indefinido, command=self.toggle_fecha_fin).grid(row=4, column=4, padx=5)

        # --- C: COSTOS ---
        cost_frame = ttk.Labelframe(main_content, text="3. Distribución de Unidades de Producción", padding=10, bootstyle="warning")
        cost_frame.pack(fill=X, padx=10, pady=5)
        
        c_controls = ttk.Frame(cost_frame)
        c_controls.pack(fill=X, pady=5)
        
        self.cb_unidad = ttk.Combobox(c_controls, state="readonly", width=40)
        self.cb_unidad.pack(side=LEFT, padx=5)
        
        ttk.Label(c_controls, text="%:").pack(side=LEFT)
        self.entry_pct = ttk.Entry(c_controls, width=8)
        self.entry_pct.insert(0, "100")
        self.entry_pct.pack(side=LEFT, padx=5)
        
        ttk.Button(c_controls, text="+ Agregar", command=self.add_cost_line, bootstyle="secondary-outline").pack(side=LEFT, padx=5)
        ttk.Button(c_controls, text="x Quitar Selecc.", command=self.remove_cost_line, bootstyle="danger-outline").pack(side=LEFT, padx=5)

        self.tree_costos = ttk.Treeview(cost_frame, columns=("id", "nombre", "pct"), show="headings", height=3)
        self.tree_costos.heading("nombre", text="Unidad / Fuente")
        self.tree_costos.heading("pct", text="% Asignado")
        self.tree_costos.column("id", width=0, stretch=False)
        self.tree_costos.column("pct", width=100, anchor=CENTER)
        self.tree_costos.pack(fill=X)

        # BOTONES ACCIÓN
        actions_frame = ttk.Frame(main_content, padding=10)
        actions_frame.pack(fill=X)
        
        self.btn_save = ttk.Button(actions_frame, text="Guardar Contrato", command=self.save_contract, bootstyle="success")
        self.btn_save.pack(side=RIGHT, padx=5)

        self.btn_delete = ttk.Button(actions_frame, text="Eliminar Contrato", command=self.delete_current_contract, bootstyle="danger")
        self.btn_delete.pack(side=RIGHT, padx=5)
        self.btn_delete.hide = lambda: self.btn_delete.pack_forget()
        self.btn_delete.show = lambda: self.btn_delete.pack(side=RIGHT, padx=5)
        self.btn_delete.hide()
        
        self.btn_cancel = ttk.Button(actions_frame, text="Cancelar Edición", command=self.clear_form, bootstyle="secondary")
        self.btn_cancel.pack(side=RIGHT, padx=5)
        self.btn_cancel.hide = lambda: self.btn_cancel.pack_forget()
        self.btn_cancel.show = lambda: self.btn_cancel.pack(side=RIGHT, padx=5)
        self.btn_cancel.hide()

        # BARRA INFERIOR
        tools_frame = ttk.Frame(main_content, padding=10)
        tools_frame.pack(fill=X, side=BOTTOM)
        
        ttk.Label(tools_frame, text="Gestión de Contratos:", font=("Segoe UI", 10, "bold")).pack(side=LEFT, padx=5)
        
        ttk.Button(tools_frame, text="📂 Buscar Contrato Existente", command=self.open_contract_search, bootstyle="info-outline").pack(side=LEFT, padx=10)
        ttk.Button(tools_frame, text="✨ Nuevo Contrato (Limpiar)", command=self.clear_form, bootstyle="secondary").pack(side=LEFT)

    # --- LÓGICA REFACTORIZADA ---

    def _load_catalogs(self):
        # 1. Cargamos TODOS los puestos en memoria (con su departamento ID)
        # get_puestos_detailed retorna: (id, nombre, depto_nombre, ..., id_depto (idx 6))
        self.all_puestos = self.cat_dao.get_puestos_detailed()
        
        self.deptos_data = self.cat_dao.get_departamentos()
        self.tipos_data = self.cat_dao.get_tipos_contrato()
        self.unidades_data = self.cat_dao.get_unidades_produccion()
        self.jornadas_data = self.cat_dao.get_jornadas()

        # Llenamos Combos Independientes
        self.cb_depto['values'] = [x[1] for x in self.deptos_data]
        self.cb_tipo['values'] = [x[1] for x in self.tipos_data]
        self.cb_unidad['values'] = [x[1] for x in self.unidades_data]
        self.cb_jornada['values'] = [x[1] for x in self.jornadas_data]
        
        # El Puesto inicia vacío hasta que se elija Depto
        self.cb_puesto.set('')
        self.cb_puesto['values'] = []

    def _on_depto_changed(self, event):
        """ Filtra los puestos basados en el departamento seleccionado """
        depto_nombre = self.cb_depto.get()
        if not depto_nombre: return
        
        # 1. Buscar ID del Depto seleccionado
        id_depto = next((d[0] for d in self.deptos_data if d[1] == depto_nombre), None)
        if not id_depto: return
        
        # 2. Filtrar Puestos
        # Recordar: p[6] es id_departamento en la tupla devuelta por get_puestos_detailed
        puestos_filtrados = [p[1] for p in self.all_puestos if p[6] == id_depto]
        
        # 3. Actualizar Combo Puestos
        self.cb_puesto['values'] = sorted(puestos_filtrados)
        self.cb_puesto.set('')

    # ... (open_contract_search, on_contract_selected_from_modal, open_search_modal, on_employee_selected se mantienen igual) ...
    def open_contract_search(self):
        ContractSelector(self, self.on_contract_selected_from_modal)

    def on_contract_selected_from_modal(self, id_contrato):
        self._load_contract_to_form(id_contrato)

    def open_search_modal(self):
        if self.selected_contract_id:
            Messagebox.show_warning("No puede cambiar el empleado en modo edición. Cancele primero.")
            return
        EmployeeSelector(self, self.on_employee_selected)

    def on_employee_selected(self, emp_id, emp_code, emp_name):
        self.current_employee_id = emp_id
        self.lbl_employee_name.config(text=f"{emp_code} - {emp_name}", bootstyle="success")

    def toggle_fecha_fin(self):
        state = "disabled" if self.var_indefinido.get() else "normal"
        self.date_fin.entry.configure(state=state)
        if state == "disabled": self.date_fin.entry.delete(0, END)

    def add_cost_line(self):
        unidad_nombre = self.cb_unidad.get()
        try:
            pct = float(self.entry_pct.get())
        except ValueError: return
        if not unidad_nombre: return
        unidad_id = next((x[0] for x in self.unidades_data if x[1] == unidad_nombre), None)
        if unidad_id:
            for u_id, _ in self.cost_distribution_list:
                if u_id == unidad_id: return
            self.cost_distribution_list.append((unidad_id, pct))
            self._refresh_cost_tree()
            self.cb_unidad.set("")
            self.entry_pct.delete(0, END)
            self.entry_pct.insert(0, "0")

    def remove_cost_line(self):
        sel = self.tree_costos.selection()
        if not sel: return
        item = self.tree_costos.item(sel[0])
        unidad_id_to_remove = item['values'][0]
        self.cost_distribution_list = [
            (uid, pct) for uid, pct in self.cost_distribution_list 
            if uid != unidad_id_to_remove
        ]
        self._refresh_cost_tree()

    def _refresh_cost_tree(self):
        for i in self.tree_costos.get_children(): self.tree_costos.delete(i)
        for uid, pct in self.cost_distribution_list:
            u_name = next((x[1] for x in self.unidades_data if x[0] == uid), "Desconocido")
            self.tree_costos.insert("", END, values=(uid, u_name, pct))

    # --- LÓGICA EDICIÓN (ADAPTADA) ---
    def _load_contract_to_form(self, id_contrato):
        contrato, empleado, costos = self.dao.get_contract_details(id_contrato)
        
        self.selected_contract_id = id_contrato
        self.btn_save.config(text="Actualizar Contrato", bootstyle="warning")
        self.btn_cancel.show()
        self.btn_delete.show()
        
        self.current_employee_id = empleado[0]
        self.lbl_employee_name.config(text=f"{empleado[1]} - {empleado[2]} {empleado[3]}", bootstyle="warning")
        
        # 1. Cargar Departamento Primero
        depto_txt = next((x[1] for x in self.deptos_data if x[0] == contrato[3]), "")
        self.cb_depto.set(depto_txt)
        
        # 2. Disparar filtro manual para llenar puestos
        self._on_depto_changed(None)
        
        # 3. Cargar Puesto (Ahora que la lista está filtrada y disponible)
        puesto_txt = next((x[1] for x in self.all_puestos if x[0] == contrato[2]), "")
        self.cb_puesto.set(puesto_txt)

        # Resto de campos
        tipo_txt = next((x[1] for x in self.tipos_data if x[0] == contrato[4]), "")
        jornada_txt = next((x[1] for x in self.jornadas_data if x[0] == contrato[5]), "")
        self.cb_tipo.set(tipo_txt)
        self.cb_jornada.set(jornada_txt)

        self.entry_salario.delete(0, END)
        self.entry_salario.insert(0, contrato[8] if contrato[8] else 0)
        
        self.entry_saldo_ini.delete(0, END)
        self.entry_saldo_ini.insert(0, contrato[10] if contrato[10] is not None else "0.0")

        self.date_kardex.entry.delete(0, END)
        if contrato[9]: self.date_kardex.entry.insert(0, contrato[9])

        self.date_inicio.entry.delete(0, END)
        self.date_inicio.entry.insert(0, contrato[6] if contrato[6] else "")
        
        self.date_fin.entry.delete(0, END)
        if contrato[7]:
            self.var_indefinido.set(False)
            self.date_fin.entry.configure(state="normal")
            self.date_fin.entry.insert(0, contrato[7])
        else:
            self.var_indefinido.set(True)
            self.toggle_fecha_fin()
            
        self.cost_distribution_list = [(c[0], c[2]) for c in costos]
        self._refresh_cost_tree()

    def clear_form(self):
        self.selected_contract_id = None
        self.current_employee_id = None
        self.lbl_employee_name.config(text="Seleccione un colaborador...", bootstyle="inverse")
        self.cb_depto.set("")
        self.cb_puesto.set("")
        self.cb_puesto['values'] = [] # Limpiar cascada
        self.cb_tipo.set("")
        self.cb_jornada.set("")
        self.entry_salario.delete(0, END)
        self.entry_saldo_ini.delete(0, END)
        self.entry_saldo_ini.insert(0, "0")
        self.cost_distribution_list = []
        self._refresh_cost_tree()
        self.btn_save.config(text="Guardar Contrato", bootstyle="success")
        self.btn_cancel.hide()
        self.btn_delete.hide()

    def delete_current_contract(self):
        if not self.selected_contract_id: return
        if Messagebox.yesno("¿Está seguro de eliminar este contrato?", "Confirmar") == 'Yes': 
            ok, msg = self.dao.delete_contract(self.selected_contract_id)
            if ok:
                Messagebox.show_info(msg, "Eliminado")
                self.clear_form()
            else:
                Messagebox.show_error(msg, "Error")

    def save_contract(self):
        # Validaciones
        if not self.current_employee_id: return Messagebox.show_warning("Seleccione un empleado", "Advertencia")
        if not self.cb_depto.get(): return Messagebox.show_warning("Seleccione el departamento", "Advertencia")
        if not self.cb_puesto.get(): return Messagebox.show_warning("Seleccione el puesto", "Advertencia")
        
        total = sum(x[1] for x in self.cost_distribution_list)
        if abs(total - 100) > 0.1: return Messagebox.show_error("La distribución debe sumar 100%", "Error")

        try:
            # Obtener IDs
            id_depto = next(x[0] for x in self.deptos_data if x[1] == self.cb_depto.get())
            # Ojo: Buscamos en self.all_puestos, no en el combo filtrado, para asegurar integridad
            id_puesto = next(x[0] for x in self.all_puestos if x[1] == self.cb_puesto.get() and x[6] == id_depto)
            
            id_tipo = next(x[0] for x in self.tipos_data if x[1] == self.cb_tipo.get())
            id_jornada = next(x[0] for x in self.jornadas_data if x[1] == self.cb_jornada.get())

            f_fin = None if self.var_indefinido.get() else self.date_fin.entry.get()
            salario = float(self.entry_salario.get() or 0)
            f_kardex = self.date_kardex.entry.get() or None
            s_ini = float(self.entry_saldo_ini.get() or 0)

            if self.selected_contract_id is None:
                data = (self.current_employee_id, id_puesto, id_depto, id_tipo, id_jornada, f_kardex, s_ini, self.date_inicio.entry.get(), f_fin, salario)
                ok, msg = self.dao.create_contract(data, self.cost_distribution_list)
            else:
                data = (id_puesto, id_depto, id_tipo, id_jornada, f_kardex, s_ini, self.date_inicio.entry.get(), f_fin, salario, self.selected_contract_id)
                ok, msg = self.dao.update_contract(self.selected_contract_id, data, self.cost_distribution_list)

            if ok:
                Messagebox.show_info(msg, "Éxito")
                self.clear_form()
            else:
                Messagebox.show_error(msg, "Error")

        except StopIteration:
            Messagebox.show_error("Error interno validando IDs (probablemente el puesto no coincida con el departamento).", "Error")
        except ValueError:
            Messagebox.show_error("Error de formato numérico.", "Error")