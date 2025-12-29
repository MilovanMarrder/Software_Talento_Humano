import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox, MessageDialog 
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
        
        self.selected_contract_id = None # Control de Estado (None=Crear, ID=Editar)
        self.current_employee_id = None
        self.cost_distribution_list = [] # Lista de tuplas (id_unidad, pct)
        self.var_indefinido = ttk.BooleanVar(value=True) 
        self.pack(fill=BOTH, expand=True)
        self._create_ui()
        self._load_catalogs()
        #self._load_contract_list() # se comenta porqué ahora será una busqueda con el componente
        self.toggle_fecha_fin()

    def _create_ui(self):
        # Crear un Canvas con Scroll si la pantalla es pequeña, 
        # pero para simplificar usaremos pack directo asumiendo resolución HD.
        
        main_content = ttk.Frame(self)
        main_content.pack(fill=BOTH, expand=True)

        # --- PARTE A: BUSCADOR ---
        search_frame = ttk.Labelframe(main_content, text="1. Colaborador", padding=10, bootstyle="info")
        search_frame.pack(fill=X, padx=10, pady=5)
        
        self.btn_search = ttk.Button(search_frame, text="🔍 Buscar Empleado", command=self.open_search_modal, bootstyle="info")
        self.btn_search.pack(side=LEFT, padx=5)
        
        self.lbl_employee_name = ttk.Label(search_frame, text="Seleccione un colaborador...", font=("Segoe UI", 11, "bold"))
        self.lbl_employee_name.pack(side=LEFT, padx=20)

        # --- PARTE B: DATOS CONTRATO ---
        details_frame = ttk.Labelframe(main_content, text="2. Datos Contractuales", padding=10, bootstyle="primary")
        details_frame.pack(fill=X, padx=10, pady=5)
        
        # Fila 0
        ttk.Label(details_frame, text="Puesto:").grid(row=0, column=0, padx=5, pady=5, sticky=E)
        self.cb_puesto = ttk.Combobox(details_frame, state="readonly", width=35)
        self.cb_puesto.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(details_frame, text="Departamento:").grid(row=0, column=2, padx=5, pady=5, sticky=E)
        self.cb_depto = ttk.Combobox(details_frame, state="readonly", width=35)
        self.cb_depto.grid(row=0, column=3, padx=5, pady=5)
        

        # Fila 1: Modalidad y Jornada (Agrupamos lo legal)
        ttk.Label(details_frame, text="Tipo Contrato:").grid(row=1, column=0, padx=5, pady=5, sticky=E)
        self.cb_tipo = ttk.Combobox(details_frame, state="readonly", width=35)
        self.cb_tipo.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(details_frame, text="Jornada:").grid(row=1, column=2, padx=5, pady=5, sticky=E)
        self.cb_jornada = ttk.Combobox(details_frame, state="readonly", width=35) # <--- NUEVO
        self.cb_jornada.grid(row=1, column=3, padx=5, pady=5)
        
        # Fila 2: Aspecto Económico
        ttk.Label(details_frame, text="Salario Base:").grid(row=2, column=0, padx=5, pady=5, sticky=E)
        self.entry_salario = ttk.Entry(details_frame, width=35)
        self.entry_salario.grid(row=2, column=1, padx=5, pady=5)

        # ... (Fila de Salario) ...
        
        # Fila Nueva: Configuración Vacaciones
        ttk.Label(details_frame, text="Inicio Contab. Vacaciones:", bootstyle="inverse-primary").grid(row=3, column=0, padx=5, pady=5, sticky=E)
        self.date_kardex = ttk.DateEntry(details_frame, dateformat='%Y-%m-%d')
        self.date_kardex.grid(row=3, column=1, padx=5, pady=5, sticky=W)
        
        ttk.Label(details_frame, text="Saldo Inicial (Días):", bootstyle="inverse-primary").grid(row=3, column=2, padx=5, pady=5, sticky=E)
        self.entry_saldo_ini = ttk.Entry(details_frame, width=10)
        self.entry_saldo_ini.insert(0, "0")
        self.entry_saldo_ini.grid(row=3, column=3, padx=5, pady=5, sticky=W)

        # Fila 4: Fechas contrato (Bajamos las fechas originales)
        # ... (Ajusta el row=4 en date_inicio, date_fin y check indefinido) ...
        
        # Fila 3: Tiempos (Bajamos esto para dar aire)
        ttk.Label(details_frame, text="Fecha Inicio:").grid(row=4, column=0, padx=5, pady=5, sticky=E)
        self.date_inicio = ttk.DateEntry(details_frame, dateformat='%Y-%m-%d')
        self.date_inicio.grid(row=4, column=1, padx=5, pady=5, sticky=W)
        
        ttk.Label(details_frame, text="Fecha Fin:").grid(row=4, column=2, padx=5, pady=5, sticky=E)
        self.date_fin = ttk.DateEntry(details_frame, dateformat='%Y-%m-%d', startdate=None)
        self.date_fin.grid(row=4, column=3, padx=5, pady=5, sticky=W)
        
        self.var_indefinido = ttk.BooleanVar(value=True)
        ttk.Checkbutton(details_frame, text="Indefinido", variable=self.var_indefinido, command=self.toggle_fecha_fin).grid(row=4, column=4, padx=5)
        # --- PARTE C: COSTOS ---
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
        # BOTÓN NUEVO: Eliminar Línea
        ttk.Button(c_controls, text="x Quitar Selecc.", command=self.remove_cost_line, bootstyle="danger-outline").pack(side=LEFT, padx=5)

        # Treeview pequeña para costos
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

        # Botón Eliminar (Solo visible en edición)
        self.btn_delete = ttk.Button(actions_frame, text="Eliminar Contrato", command=self.delete_current_contract, bootstyle="danger")
        self.btn_delete.pack(side=RIGHT, padx=5)
        self.btn_delete.hide = lambda: self.btn_delete.pack_forget()
        self.btn_delete.show = lambda: self.btn_delete.pack(side=RIGHT, padx=5)
        self.btn_delete.hide() # Oculto por defecto
        
        self.btn_cancel = ttk.Button(actions_frame, text="Cancelar Edición", command=self.clear_form, bootstyle="secondary")
        self.btn_cancel.pack(side=RIGHT, padx=5)
        self.btn_cancel.hide = lambda: self.btn_cancel.pack_forget()
        self.btn_cancel.show = lambda: self.btn_cancel.pack(side=RIGHT, padx=5)
        self.btn_cancel.hide()

        # --- PARTE D: BARRA DE ACCIONES SUPERIOR O INFERIOR ---
        # Reemplazamos el "list_frame" gigante por una barra de herramientas de gestión
        
        tools_frame = ttk.Frame(main_content, padding=10)
        tools_frame.pack(fill=X, side=BOTTOM) # Lo ponemos al final
        
        ttk.Label(tools_frame, text="Gestión de Contratos:", font=("Segoe UI", 10, "bold")).pack(side=LEFT, padx=5)
        
        # BOTÓN NUEVO: BUSCAR HISTÓRICO
        ttk.Button(
            tools_frame, 
            text="📂 Buscar Contrato Existente", 
            command=self.open_contract_search, 
            bootstyle="info-outline"
        ).pack(side=LEFT, padx=10)
        
        # El botón limpiar ahora es explícito para "Nuevo"
        ttk.Button(
            tools_frame,
            text="✨ Nuevo Contrato (Limpiar)",
            command=self.clear_form,
            bootstyle="secondary"
        ).pack(side=LEFT)

        # self.toggle_fecha_fin()

    # --- LÓGICA ---
    def _load_catalogs(self):
        # Carga igual que antes ...
        self.puestos_data = self.cat_dao.get_puestos()
        self.deptos_data = self.cat_dao.get_departamentos()
        self.tipos_data = self.cat_dao.get_tipos_contrato()
        self.unidades_data = self.cat_dao.get_unidades_produccion()
        self.jornadas_data = self.cat_dao.get_jornadas()

        self.cb_puesto['values'] = [x[1] for x in self.puestos_data]
        self.cb_depto['values'] = [x[1] for x in self.deptos_data]
        self.cb_tipo['values'] = [x[1] for x in self.tipos_data]
        self.cb_unidad['values'] = [x[1] for x in self.unidades_data]
        self.cb_jornada['values'] = [x[1] for x in self.jornadas_data]

    def open_contract_search(self):
        # Abrir el modal y pasarle el método que maneja la selección
        ContractSelector(self, self.on_contract_selected_from_modal)

    def on_contract_selected_from_modal(self, id_contrato):
        # Este método reemplaza al on_contract_double_click antiguo
        self._load_contract_to_form(id_contrato)


    def open_search_modal(self):
        # Bloquea búsqueda si estamos editando (para no cambiar el empleado de un contrato ya hecho)
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

    # --- LÓGICA DE COSTOS (ADD / REMOVE) ---
    def add_cost_line(self):
        unidad_nombre = self.cb_unidad.get()
        try:
            pct = float(self.entry_pct.get())
        except ValueError: return

        if not unidad_nombre: return
        
        # Buscar ID
        unidad_id = next((x[0] for x in self.unidades_data if x[1] == unidad_nombre), None)
        
        if unidad_id:
            # Validar que no esté duplicada
            for u_id, _ in self.cost_distribution_list:
                if u_id == unidad_id:
                    Messagebox.show_warning("Esta unidad ya está agregada.")
                    return

            self.cost_distribution_list.append((unidad_id, pct))
            self._refresh_cost_tree()
            self.cb_unidad.set("")
            self.entry_pct.delete(0, END)
            self.entry_pct.insert(0, "0") # O dejar lo que falta para llegar a 100

    def remove_cost_line(self):
        """Elimina la línea seleccionada"""
        sel = self.tree_costos.selection()
        if not sel: return
        
        # Obtener valores de la fila
        item = self.tree_costos.item(sel[0])
        unidad_id_to_remove = item['values'][0]
        
        # Filtrar lista interna
        self.cost_distribution_list = [
            (uid, pct) for uid, pct in self.cost_distribution_list 
            if uid != unidad_id_to_remove
        ]
        self._refresh_cost_tree()

    def _refresh_cost_tree(self):
        """Sincroniza la tabla visual con la lista interna"""
        for i in self.tree_costos.get_children(): self.tree_costos.delete(i)
        
        for uid, pct in self.cost_distribution_list:
            # Buscar nombre para mostrar
            u_name = next((x[1] for x in self.unidades_data if x[0] == uid), "Desconocido")
            self.tree_costos.insert("", END, values=(uid, u_name, pct))

    # --- LÓGICA DE EDICIÓN ---

    def _load_contract_to_form(self, id_contrato):
        contrato, empleado, costos = self.dao.get_contract_details(id_contrato)
        
        # 1. Configuración Visual
        self.selected_contract_id = id_contrato
        self.btn_save.config(text="Actualizar Contrato", bootstyle="warning")
        self.btn_cancel.show()
        self.btn_delete.show()
        
        # 2. Empleado
        self.current_employee_id = empleado[0]
        self.lbl_employee_name.config(text=f"{empleado[1]} - {empleado[2]} {empleado[3]}", bootstyle="warning")
        
        # 3. Comboboxes (Puesto, Depto, Tipo)
        puesto_txt = next((x[1] for x in self.puestos_data if x[0] == contrato[2]), "")
        depto_txt = next((x[1] for x in self.deptos_data if x[0] == contrato[3]), "")
        tipo_txt = next((x[1] for x in self.tipos_data if x[0] == contrato[4]), "")
        
        self.cb_puesto.set(puesto_txt)
        self.cb_depto.set(depto_txt)
        self.cb_tipo.set(tipo_txt)

        # 4. Salario
        self.entry_salario.delete(0, END)
        self.entry_salario.insert(0, contrato[7] if contrato[7] else 0)

        # --- AQUÍ ESTÁ LA MAGIA DE LOS NUEVOS CAMPOS ---
        try:
            # Índice 9: Jornada
            id_jornada_val = contrato[9]
            jornada_txt = next((x[1] for x in self.jornadas_data if x[0] == id_jornada_val), "")
            self.cb_jornada.set(jornada_txt)

            # Índice 10: Saldo Inicial
            saldo_val = contrato[10]
            self.entry_saldo_ini.delete(0, END)
            # Si es None, ponemos 0.0
            self.entry_saldo_ini.insert(0, saldo_val if saldo_val is not None else "0.0")

            # Índice 11: Fecha Inicio Kardex
            fecha_k_val = contrato[11]
            self.date_kardex.entry.delete(0, END) # Limpiamos el entry interno
            if fecha_k_val:
                self.date_kardex.entry.insert(0, fecha_k_val)
            
        except IndexError:
            print("Advertencia: La tupla del contrato es más corta de lo esperado (BD desactualizada en memoria).")
        # ------------------------------------------------

        # 5. Fechas Contrato (Inicio / Fin)
        self.date_inicio.entry.delete(0, END)
        self.date_inicio.entry.insert(0, contrato[5])
        
        self.date_fin.entry.delete(0, END)
        if contrato[6]:
            self.var_indefinido.set(False)
            self.date_fin.entry.configure(state="normal")
            self.date_fin.entry.insert(0, contrato[6])
        else:
            self.var_indefinido.set(True)
            self.toggle_fecha_fin()
            
        # 6. Costos
        self.cost_distribution_list = [(c[0], c[2]) for c in costos]
        self._refresh_cost_tree()

    def clear_form(self):
        self.selected_contract_id = None
        self.current_employee_id = None
        self.lbl_employee_name.config(text="Seleccione un colaborador...", bootstyle="inverse")
        self.cb_puesto.set("")
        self.cb_depto.set("")
        self.cb_tipo.set("")
        self.entry_salario.delete(0, END)
        self.cost_distribution_list = []
        self._refresh_cost_tree()
        self.btn_save.config(text="Guardar Contrato", bootstyle="success")
        self.btn_cancel.hide()
        self.btn_delete.hide()


    def delete_current_contract(self):
            if not self.selected_contract_id: return
            
            # Usamos el método nativo 'yesno'. 
            # Es robusto y devuelve 'Yes' o 'No' sin fallos.
            confirm = Messagebox.yesno(
                message="¿Está seguro de eliminar este contrato?\nSe borrarán también los costos asociados.",
                title="Confirmar Eliminación",
                parent=self
            )
            
            print(f"DEBUG: Respuesta estándar recibida: '{confirm}'") # Para que veas en consola

            # En ttkbootstrap, yesno retorna el string 'Yes' si confirmas.
            if confirm == 'Yes': 
                ok, msg = self.dao.delete_contract(self.selected_contract_id)
                if ok:
                    Messagebox.show_info(msg, "Eliminado")
                    self.clear_form()
                    # self._load_contract_list()
                else:
                    Messagebox.show_error(msg, "Error")

    def save_contract(self):
            # 1. Validaciones de Integridad (Guard Clauses)
            if not self.current_employee_id: 
                return Messagebox.show_warning("Falta seleccionar un empleado", "Advertencia")
            if not self.cb_puesto.get(): 
                return Messagebox.show_warning("Falta seleccionar el puesto", "Advertencia")
            if not self.cb_jornada.get():
                return Messagebox.show_warning("Falta seleccionar la jornada laboral", "Advertencia")
            
            # Validación de Costos 100%
            total = sum(x[1] for x in self.cost_distribution_list)
            if abs(total - 100) > 0.1:
                return Messagebox.show_error(f"La distribución suma {total}%. Debe ser exactamente 100%", "Error Distribución")

            try:
                # 2. OBTENCIÓN DE IDs (Esto debe ocurrir ANTES de crear la variable 'data')
                # -----------------------------------------------------------------------
                id_puesto = next(x[0] for x in self.puestos_data if x[1] == self.cb_puesto.get())
                id_depto = next(x[0] for x in self.deptos_data if x[1] == self.cb_depto.get())
                id_tipo = next(x[0] for x in self.tipos_data if x[1] == self.cb_tipo.get())
                id_jornada = next(x[0] for x in self.jornadas_data if x[1] == self.cb_jornada.get())

                # 3. OBTENCIÓN DE VALORES DEL FORMULARIO
                # -----------------------------------------------------------------------
                fecha_fin = None if self.var_indefinido.get() else self.date_fin.entry.get()
                
                salario_txt = self.entry_salario.get()
                salario = float(salario_txt) if salario_txt else 0.0

                # Valores de Vacaciones (Nuevos)
                f_kardex = self.date_kardex.entry.get()
                if not f_kardex: f_kardex = None
                
                saldo_txt = self.entry_saldo_ini.get()
                s_inicial = float(saldo_txt) if saldo_txt else 0.0

                # 4. ARMADO DE LA TUPLA DE DATOS
                # -----------------------------------------------------------------------
                if self.selected_contract_id is None:
                    # MODO CREAR (INSERT)
                    # Orden DAO: id_emp, id_puesto, id_depto, id_tipo, id_jornada, 
                    #            f_kardex, s_inicial, f_ini, f_fin, salario
                    data = (
                        self.current_employee_id, 
                        id_puesto,   # Aquí se usaba la variable que daba error
                        id_depto, 
                        id_tipo, 
                        id_jornada, 
                        f_kardex, 
                        s_inicial,
                        self.date_inicio.entry.get(), 
                        fecha_fin, 
                        salario
                    )
                    ok, msg = self.dao.create_contract(data, self.cost_distribution_list)
                else:
                    # MODO EDITAR (UPDATE)
                    # Orden DAO: id_puesto, id_depto, id_tipo, id_jornada, 
                    #            f_kardex, s_inicial, f_ini, f_fin, salario, WHERE id_contrato
                    data = (
                        id_puesto,   # Aquí se usaba la variable que daba error
                        id_depto, 
                        id_tipo, 
                        id_jornada,
                        f_kardex, 
                        s_inicial,
                        self.date_inicio.entry.get(), 
                        fecha_fin, 
                        salario, 
                        self.selected_contract_id
                    )
                    ok, msg = self.dao.update_contract(self.selected_contract_id, data, self.cost_distribution_list)

                # 5. RESPUESTA
                if ok:
                    Messagebox.show_info(msg, "Éxito")
                    self.clear_form()
                    # self._load_contract_list()
                else:
                    Messagebox.show_error(msg, "Error de Base de Datos")

            except StopIteration:
                # Esto ocurre si el next() no encuentra el valor en la lista (Combobox con texto inválido)
                Messagebox.show_error("Error interno: No se pudo validar el ID de un catálogo seleccionado.", "Error de Datos")
            except ValueError:
                Messagebox.show_error("Verifique que los campos numéricos (Salario, Saldo) sean correctos.", "Error de Formato")
            except Exception as e:
                Messagebox.show_error(f"Error inesperado: {e}", "Error Crítico")