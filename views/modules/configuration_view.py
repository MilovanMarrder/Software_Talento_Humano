import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from models.catalogs_dao import CatalogsDAO

class ConfigurationView(ttk.Frame):
    def __init__(self, parent, controller=None):
        super().__init__(parent)
        self.controller = controller
        
        ttk.Label(self, text="Configuración de Catálogos del Sistema", font=("Segoe UI", 18, "bold")).pack(pady=10)
        
        self.cat_dao = CatalogsDAO()
        self.dao = self.cat_dao # Alias para simplificar llamadas

        self.notebook = ttk.Notebook(self, bootstyle="primary")
        self.notebook.pack(fill=BOTH, expand=True, padx=10, pady=10)
        self.pack(fill=BOTH, expand=True)
        
        # 1. Pestañas Básicas
        self._init_basic_tabs()
        
        # 2. Pestañas de Asistencia
        self._init_attendance_tabs()

    def _init_basic_tabs(self):
        # DEPARTAMENTOS
        self.notebook.add(CatalogTab(
            self.notebook, "Departamentos", ("ID", "Nombre", "Cód. Interno"),
            self.dao.get_departamentos, self.dao.crud_departamento,
            fields=[("Nombre Área:", "text"), ("Cód. Reporte:", "text")]
        ), text="Departamentos")

        # --- PUESTOS (FIX: COMBOS DINÁMICOS) ---
        # Pasamos las FUNCIONES (sin paréntesis) en lugar de las listas estáticas
        # Esto permite que CatalogTab las ejecute cuando necesite refrescar datos.
        
        self.notebook.add(CatalogTab(
            self.notebook, "Cargos / Puestos", 
            ("ID", "Nombre Cargo", "Departamento", "¿Es Jefe?", "Jefe Inmediato", "Grupo PERC"),
            self.dao.get_puestos, 
            self.dao.crud_puesto,
            fields=[
                ("Nombre del Cargo:", "text"),
                ("Departamento:", "combo", self.dao.get_departamentos), # <--- Dinámico
                ("¿Tiene Personal a Cargo?:", "checkbox"),
                ("Jefe Inmediato:", "combo", self.dao.get_puestos_jefatura_combo), # <--- FIX PRINCIPAL AQUÍ
                ("Grupo PERC:", "combo", self.dao.get_grupos_perc_combo)           # <--- Dinámico
            ]
        ), text="Puestos")

        # UNIDADES
        self.notebook.add(CatalogTab(
            self.notebook, "Unidades Producción", ("ID", "Nombre Unidad", "Cód. Contable"),
            self.dao.get_unidades_produccion, self.dao.crud_unidad,
            fields=[("Nombre Descriptivo:", "text"), ("Cód. Contable:", "text")]
        ), text="Unidades Producción")

        # TIPOS DE CONTRATO
        self.notebook.add(CatalogTab(
            self.notebook, "Modalidades de Contratación", ("ID", "Modalidad Legal"),
            self.dao.get_tipos_contrato, self.dao.crud_tipo_contrato,
            fields=[("Nombre Modalidad:", "text")]
        ), text="Tipos de Contrato")

        # JORNADAS
        self.notebook.add(CatalogTab(
            self.notebook, "Jornadas Laborales", 
            ("ID", "Descripción", "Horas Diarias", "Descansa Feriados"),
            self.dao.get_jornadas, self.dao.crud_jornada,
            fields=[("Nombre (ej: Turno A):", "text"), ("Horas (ej: 8.0):", "text"), ("¿Aplica Feriados?:", "checkbox")]
        ), text="Jornadas")

        # DÍAS FESTIVOS
        self.notebook.add(CatalogTab(
            self.notebook, "Días Feriados", 
            ("ID", "Fecha (YYYY-MM-DD)", "Descripción"),
            self.dao.get_dias_festivos, self.dao.crud_dias_festivos,
            fields=[("Fecha (YYYY-MM-DD):", "text"), ("Descripción:", "text")]
        ), text="Calendario Feriados")

    def _init_attendance_tabs(self):
            # REGLAS VACACIONES
            self.notebook.add(CatalogTab(
                self.notebook, "Reglas de Antigüedad",
                ("ID", "Años Antigüedad", "Días a Otorgar"),
                self.cat_dao.get_reglas_vacaciones, self.cat_dao.crud_regla_vacacion,
                fields=[("Años Cumplidos:", "text"), ("Días Vacaciones:", "text")]
            ), text="Reglas Vacaciones")

            # CATEGORÍAS
            self.notebook.add(CatalogTab(
                self.notebook, "Categorías de Inasistencia", ("ID", "Nombre Categoría"),
                self.cat_dao.get_categorias_inasistencia, self.cat_dao.crud_categoria_inasistencia,
                fields=[("Nombre Categoría:", "text")]
            ), text="Categorías Inasistencia")

            # TIPOS INASISTENCIA
            impacto_source = [("NINGUNA", "NO Descuenta Saldo"), ("ORDINARIA", "SÍ Descuenta (Vacaciones)")]
            
            self.notebook.add(CatalogTab(
                self.notebook, "Tipos de Inasistencia",
                ("ID", "Descripción", "Categoría", "¿Descuenta?"),
                self.cat_dao.get_tipos_inasistencia, self.cat_dao.crud_tipo_inasistencia,
                fields=[
                    ("Nombre Tipo:", "text"),
                    ("Categoría:", "combo", self.cat_dao.get_categorias_combo), # Dinámico
                    ("Impacto en Saldo:", "combo", impacto_source), # Estático
                    ("¿Con Goce de Sueldo?:", "checkbox")
                ]
            ), text="Tipos de Inasistencia")

class CatalogTab(ttk.Frame):
    """
    Componente CRUD Genérico v3.0 
    - Soporte Dinámico de Combos
    - Barra de Búsqueda y Filtrado en Vivo
    - Ordenamiento estable
    """
    def __init__(self, parent, title, columns, dao_fetch, dao_crud, fields):
        super().__init__(parent, padding=10)
        self.title = title
        self.columns = columns
        self.dao_fetch = dao_fetch
        self.dao_crud = dao_crud
        self.fields_config = fields 
        
        self.selected_id = None
        self.widgets = [] 
        
        # --- NUEVO: Cache para filtrado ---
        self.all_rows = [] 
        self.var_search = ttk.StringVar()
        self.var_search.trace("w", self._filter_data) # Trigger al escribir

        self._setup_ui()
        # Cargamos los datos iniciales
        self.refresh_table()

    def _get_data_from_source(self, source):
        if callable(source):
            return source()
        return source

    def _setup_ui(self):
            # 1. FRAME DEL FORMULARIO
            form_frame = ttk.Labelframe(self, text=f"Gestión de {self.title}", padding=15, bootstyle="info")
            form_frame.pack(fill=X, pady=5, padx=5)
            
            inputs_container = ttk.Frame(form_frame)
            inputs_container.pack(fill=X, expand=True)
            
            current_row = ttk.Frame(inputs_container)
            current_row.pack(fill=X, pady=5)

            # Generación dinámica de inputs
            for field_conf in self.fields_config:
                lbl_text = field_conf[0]
                w_type = field_conf[1]
                
                f_item = ttk.Frame(current_row)
                f_item.pack(side=LEFT, padx=10, anchor=N)
                
                if w_type == "text":
                    ttk.Label(f_item, text=lbl_text, font=("Segoe UI", 9)).pack(anchor=W)
                    w = ttk.Entry(f_item, width=25)
                    w.pack(pady=2)
                    self.widgets.append({'type': 'text', 'widget': w})
                    
                elif w_type == "combo":
                    ttk.Label(f_item, text=lbl_text, font=("Segoe UI", 9)).pack(anchor=W)
                    raw_source = field_conf[2]
                    current_data = self._get_data_from_source(raw_source)
                    sorted_source = sorted(current_data, key=lambda x: x[1]) if current_data else []
                    values = [x[1] for x in sorted_source]
                    
                    w = ttk.Combobox(f_item, values=values, state="readonly", width=25)
                    w.pack(pady=2)
                    self.widgets.append({
                        'type': 'combo', 
                        'widget': w, 
                        'source': sorted_source, 
                        'raw_source_ref': raw_source 
                    })

                elif w_type == "checkbox":
                    ttk.Label(f_item, text="").pack()
                    var = ttk.IntVar(value=0)
                    w = ttk.Checkbutton(f_item, text=lbl_text, variable=var, bootstyle="round-toggle")
                    w.pack(pady=5)
                    self.widgets.append({'type': 'check', 'widget': w, 'var': var})

            # BOTONES DEL FORMULARIO
            btn_frame = ttk.Frame(form_frame)
            btn_frame.pack(fill=X, pady=(15, 0))
            center_btns = ttk.Frame(btn_frame)
            center_btns.pack(anchor=CENTER)

            self.btn_save = ttk.Button(center_btns, text="💾 Guardar", command=self.save, bootstyle="success", width=15)
            self.btn_save.pack(side=LEFT, padx=5)
            self.btn_cancel = ttk.Button(center_btns, text="🧹 Limpiar", command=self.clear_form, bootstyle="secondary", width=15)
            self.btn_cancel.pack(side=LEFT, padx=5)
            self.btn_delete = ttk.Button(center_btns, text="🗑 Eliminar", command=self.delete, bootstyle="danger", width=15)
            self.btn_delete.pack(side=LEFT, padx=5)

            # ---------------------------------------------------------
            # 2. BARRA DE BÚSQUEDA (NUEVO)
            # ---------------------------------------------------------
            search_frame = ttk.Frame(self, padding=(5, 10))
            search_frame.pack(fill=X, padx=5)
            
            ttk.Label(search_frame, text="🔍 Buscar:", bootstyle="secondary").pack(side=LEFT, padx=(5, 5))
            entry_search = ttk.Entry(search_frame, textvariable=self.var_search)
            entry_search.pack(side=LEFT, fill=X, expand=True, padx=5)
            
            # Botón 'X' para limpiar búsqueda
            ttk.Button(search_frame, text="✕", command=lambda: self.var_search.set(""), 
                       bootstyle="link-secondary", width=3).pack(side=LEFT)

            # ---------------------------------------------------------
            # 3. TABLA
            # ---------------------------------------------------------
            self.tree = ttk.Treeview(self, columns=[str(i) for i in range(len(self.columns))], show="headings", bootstyle="info")
            for i, col_name in enumerate(self.columns):
                self.tree.heading(str(i), text=col_name)
                # Ajuste de ancho inteligente
                width = 250 if "Nombre" in col_name or "Descripción" in col_name else 100
                self.tree.column(str(i), width=width)
            
            self.tree.pack(fill=BOTH, expand=True, pady=0, padx=5)
            sb = ttk.Scrollbar(self.tree, orient=VERTICAL, command=self.tree.yview)
            self.tree.configure(yscroll=sb.set)
            sb.pack(side=RIGHT, fill=Y)
            self.tree.bind("<Double-1>", self.on_double_click)

    # --- LÓGICA DE DATOS Y FILTRADO (NUEVO) ---

    def refresh_table(self):
        """Obtiene datos frescos de BD y aplica el filtro actual"""
        # 1. Cargar todo a memoria
        self.all_rows = self.dao_fetch()
        # 2. Renderizar aplicando filtro
        self._filter_data()

    def _filter_data(self, *args):
        """Filtra la lista en memoria y actualiza el Treeview"""
        term = self.var_search.get().lower().strip()
        
        # Limpiar tabla
        for item in self.tree.get_children():
            self.tree.delete(item)

        filtered_rows = []
        if not term:
            filtered_rows = self.all_rows
        else:
            # Lógica de búsqueda genérica: 
            # Busca el término en CUALQUIER columna visible de la fila
            for row in self.all_rows:
                # Tomamos solo las columnas visibles (según self.columns)
                visual_data = row[:len(self.columns)]
                # Convertimos todo a string y buscamos coincidencia
                row_str = " ".join([str(val).lower() for val in visual_data if val is not None])
                
                if term in row_str:
                    filtered_rows.append(row)
        
        # Llenar tabla
        for row in filtered_rows:
            visual_row = row[:len(self.columns)]
            # Guardamos la fila COMPLETA (raw data) en los tags o hidden values para recuperarla al editar
            self.tree.insert("", END, values=visual_row, tags=(row,)) 

    # --- (El resto de métodos se mantienen casi igual, solo ajustes menores) ---

    def _reload_combos(self):
        for w_conf in self.widgets:
            if w_conf['type'] == 'combo':
                raw_source = w_conf['raw_source_ref']
                current_data = self._get_data_from_source(raw_source)
                sorted_source = sorted(current_data, key=lambda x: x[1]) if current_data else []
                w_conf['source'] = sorted_source
                w_conf['widget']['values'] = [x[1] for x in sorted_source]

    def on_double_click(self, event):
            self._reload_combos()
            sel = self.tree.selection()
            if not sel: return
            item = self.tree.item(sel[0])
            
            # Recuperamos ID visualmente
            row_id = item['values'][0] 

            # Recuperamos DATA REAL desde self.all_rows usando el ID
            # Esto es más seguro que confiar en los tags si filtramos
            full_data_row = next((r for r in self.all_rows if str(r[0]) == str(row_id)), None)
            
            if not full_data_row: return

            self.selected_id = full_data_row[0]
            self.btn_save.config(text="Actualizar", bootstyle="warning")

            visual_idx = 1 
            raw_idx = len(self.columns) 

            for w_conf in self.widgets:
                if w_conf['type'] == 'text':
                    val = full_data_row[visual_idx]
                    w_conf['widget'].delete(0, END)
                    w_conf['widget'].insert(0, str(val) if val is not None else "")
                    visual_idx += 1

                elif w_conf['type'] in ['combo', 'check']:
                    # Lógica para determinar si el dato viene de columnas visibles o ocultas (raw)
                    if len(full_data_row) > len(self.columns):
                        val_raw = full_data_row[raw_idx]
                        raw_idx += 1
                    else:
                        val_raw = full_data_row[visual_idx]
                        visual_idx += 1

                    if w_conf['type'] == 'combo':
                        if val_raw is None:
                            w_conf['widget'].set('')
                        else:
                            # Buscamos el texto correspondiente al ID
                            txt = next((x[1] for x in w_conf['source'] if str(x[0]) == str(val_raw)), "")
                            w_conf['widget'].set(txt)
                    
                    elif w_conf['type'] == 'check':
                        is_checked = 1 if val_raw and int(val_raw) == 1 else 0
                        w_conf['var'].set(is_checked)

    def clear_form(self):
        self.selected_id = None
        for w in self.widgets:
            if w['type'] == 'text': w['widget'].delete(0, END)
            elif w['type'] == 'combo': w['widget'].set('')
            elif w['type'] == 'check': w['var'].set(0)
        self.btn_save.config(text="💾 Guardar", bootstyle="success")
        self.tree.selection_remove(self.tree.selection())
        # Opcional: Limpiar búsqueda al limpiar formulario
        # self.var_search.set("") 

    def save(self):
            params = []
            for w in self.widgets:
                if w['type'] == 'text':
                    val = w['widget'].get().strip()
                    if not val: 
                        Messagebox.show_error("Campos de texto obligatorios", "Error")
                        return
                    params.append(val)
                elif w['type'] == 'combo':
                    txt = w['widget'].get()
                    if not txt:
                        params.append(None)
                    else:
                        id_val = next((x[0] for x in w['source'] if x[1] == txt), None)
                        if id_val is None:
                            Messagebox.show_error(f"Valor '{txt}' no válido.", "Error")
                            return
                        params.append(id_val)
                elif w['type'] == 'check':
                    params.append(w['var'].get())

            if self.selected_id:
                ok, msg = self.dao_crud("UPDATE", self.selected_id, *params)
            else:
                ok, msg = self.dao_crud("INSERT", None, *params)
                
            if ok:
                Messagebox.show_info(msg, "Éxito")
                self.clear_form()
                self.refresh_table() # Esto recarga datos Y aplica el filtro existente
                self._reload_combos() 
            else:
                Messagebox.show_error(msg, "Error")

    def delete(self):
        if not self.selected_id: return
        if Messagebox.yesno("¿Eliminar registro?", "Confirmar") == 'Yes':
            ok, msg = self.dao_crud("DELETE", self.selected_id)
            if ok: 
                self.clear_form()
                self.refresh_table()
                self._reload_combos()
            else:
                Messagebox.show_error(msg, "Error")