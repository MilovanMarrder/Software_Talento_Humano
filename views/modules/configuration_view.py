import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from models.catalogs_dao import CatalogsDAO

class ConfigurationView(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.pack(fill=BOTH, expand=True)
        
        ttk.Label(self, text="Configuración de Catálogos del Sistema", font=("Segoe UI", 18, "bold")).pack(pady=10)
        
        self.notebook = ttk.Notebook(self, bootstyle="primary")
        self.notebook.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        self.dao = CatalogsDAO()
        
        # 1. Pestañas Básicas (Texto simple)
        self._init_basic_tabs()
        
        # 2. Pestañas de Asistencia (Avanzadas)
        self._init_attendance_tabs()

    def _init_basic_tabs(self):
        # DEPARTAMENTOS
        self.notebook.add(CatalogTab(
            self.notebook, "Departamentos", ("ID", "Nombre", "Cód. Interno"),
            self.dao.get_departamentos, self.dao.crud_departamento,
            fields=[("Nombre Área:", "text"), ("Cód. Reporte:", "text")]
        ), text="Departamentos")


        # PUESTOS (ACTUALIZADO CON DEPARTAMENTO)
        jefes_source = self.dao.get_puestos_jefatura_combo()
        perc_source = self.dao.get_grupos_perc_combo()
        # Reutilizamos el método existente para obtener departamentos
        # Nota: get_departamentos retorna (id, nombre, cod), transformamos a (id, nombre)
        raw_deptos = self.dao.get_departamentos()
        deptos_source = [(d[0], d[1]) for d in raw_deptos]

        self.notebook.add(CatalogTab(
            self.notebook, "Cargos / Puestos", 
            # Columnas Visuales de la Tabla:
            ("ID", "Nombre Cargo", "Departamento", "¿Tiene Personal?", "Jefe Inmediato", "Categoría PERC"),
            self.dao.get_puestos, 
            self.dao.crud_puesto,
            fields=[
                # Orden Visual de Inputs:
                ("Nombre del Cargo:", "text"),
                ("Departamento:", "combo", deptos_source), # <-- NUEVO CAMPO
                ("¿Tiene Personal a Cargo?:", "checkbox"),
                ("Jefe Inmediato:", "combo", jefes_source),
                ("Grupo PERC:", "combo", perc_source)
            ]
        ), text="Puestos")

        # UNIDADES
        self.notebook.add(CatalogTab(
            self.notebook, "Unidades Producción", ("ID", "Nombre Unidad", "Cód. Contable"),
            self.dao.get_unidades_produccion, self.dao.crud_unidad,
            fields=[("Nombre Descriptivo:", "text"), ("Cód. Contable:", "text")]
        ), text="Unidades Producción")

            # --- TIPOS DE CONTRATO ---
        self.notebook.add(CatalogTab(
            self.notebook, 
            title="Modalidades de Contratación", 
            columns=("ID", "Modalidad Legal"),
            dao_fetch=self.dao.get_tipos_contrato, 
            dao_crud=self.dao.crud_tipo_contrato,
            fields=[("Nombre Modalidad:", "text")]
        ), text="Tipos de Contrato")

        # JORNADAS LABORALES
        self.notebook.add(CatalogTab(
            self.notebook, "Jornadas Laborales", ("ID", "Descripción", "Horas Diarias"),
            self.dao.get_jornadas, self.dao.crud_jornada,
            fields=[("Nombre (ej: Turno A):", "text"), ("Horas (ej: 8.0):", "text")]
        ), text="Jornadas")

    def _init_attendance_tabs(self):
        # A. CATEGORÍAS MACRO
        self.notebook.add(CatalogTab(
            self.notebook, "Categorías Inasistencia", ("ID", "Categoría Macro"),
            self.dao.get_categorias_inasistencia, self.dao.crud_categoria_inasistencia,
            fields=[("Nombre Categoría:", "text")]
        ), text="Inasistencias (Categorías)")

        # B. TIPOS ESPECÍFICOS
        # Obtenemos la lista de categorías para llenar el Combo: [(id, nombre), ...]
        cats_raw = self.dao.get_categorias_inasistencia()
        # ORDINARIA = Descuenta | NINGUNA = No Descuenta
        opciones_descuento = [("NINGUNA", "NO Descuenta Saldo"), ("ORDINARIA", "SÍ Descuenta Saldo (Ord)")]
        
        self.notebook.add(CatalogTab(
            self.notebook, "Tipos de Inasistencia", 
            ("ID", "Descripción", "Categoría", "¿Descuenta?", "¿Goce Sueldo?"),
            self.dao.get_tipos_inasistencia, self.dao.crud_tipo_inasistencia,
            fields=[
                ("Descripción:", "text"),
                ("Categoría:", "combo", cats_raw),
                ("Afecta Vacaciones:", "combo", opciones_descuento), # Usamos lista simple
                ("Con Goce de Sueldo:", "checkbox")
            ]
        ), text="Inasistencias (Tipos)")
        
        # C. REGLAS DE VACACIONES (Matriz)
        vacation_types = self.dao.get_only_vacation_types_combo()
        
        self.notebook.add(CatalogTab(
            self.notebook, "Reglas de Antigüedad", 
            ("ID", "Tipo Vacación", "Año Antigüedad", "Días a Otorgar", "ID Tipo Raw"),
            self.dao.get_reglas_vacaciones, self.dao.crud_regla_vacacion,
            fields=[
                ("Tipo de Vacación:", "combo", vacation_types),
                ("Año de Antigüedad (1, 2...):", "text"),
                ("Días a Otorgar:", "text")
            ]
        ), text="Reglas Vacaciones")


class CatalogTab(ttk.Frame):
    """
    Componente CRUD Genérico v2.0
    Soporta: Entry, Combobox (con mapeo ID) y Checkbox.
    """
    def __init__(self, parent, title, columns, dao_fetch, dao_crud, fields):
        super().__init__(parent, padding=10)
        self.title = title
        self.columns = columns
        self.dao_fetch = dao_fetch
        self.dao_crud = dao_crud
        self.fields_config = fields 
        
        self.selected_id = None
        self.widgets = [] # Lista de diccionarios {'type': 'text/combo', 'widget': w, 'data': ...}
        
        self._setup_ui()
        self.refresh_table()


    def _setup_ui(self):
            # --- Formulario Dinámico ---
            # Usamos bootstyle info para destacar el área de edición
            form_frame = ttk.Labelframe(self, text=f"Gestión de {self.title}", padding=15, bootstyle="info")
            form_frame.pack(fill=X, pady=5, padx=5)
            
            # CONTENEDOR DE INPUTS (Arriba)
            inputs_container = ttk.Frame(form_frame)
            inputs_container.pack(fill=X, expand=True)
            
            # Lógica de Grid Responsivo (2 columnas si hay muchos campos, o flujo natural)
            # Para mantenerlo simple y genérico, usaremos pack con side=LEFT y wrap visual si fuera necesario.
            # Pero dado que pediste "botones abajo", asumiremos un flujo vertical u horizontal limpio.
            
            current_row = ttk.Frame(inputs_container)
            current_row.pack(fill=X, pady=5)

            for field_conf in self.fields_config:
                lbl_text = field_conf[0]
                w_type = field_conf[1]
                
                # Contenedor individual campo
                f_item = ttk.Frame(current_row)
                f_item.pack(side=LEFT, padx=10, anchor=N)
                
                if w_type == "text":
                    ttk.Label(f_item, text=lbl_text, font=("Segoe UI", 9)).pack(anchor=W)
                    w = ttk.Entry(f_item, width=25)
                    w.pack(pady=2)
                    self.widgets.append({'type': 'text', 'widget': w})
                    
                elif w_type == "combo":
                    ttk.Label(f_item, text=lbl_text, font=("Segoe UI", 9)).pack(anchor=W)
                    source_data = field_conf[2] 
                    # Ordenamos alfabéticamente para facilitar búsqueda visual
                    sorted_source = sorted(source_data, key=lambda x: x[1]) if source_data else []
                    values = [x[1] for x in sorted_source]
                    
                    w = ttk.Combobox(f_item, values=values, state="readonly", width=25)
                    w.pack(pady=2)
                    self.widgets.append({'type': 'combo', 'widget': w, 'source': sorted_source}) # Usamos la lista ordenada

                elif w_type == "checkbox":
                    ttk.Label(f_item, text="").pack() # Spacer
                    var = ttk.IntVar(value=0)
                    w = ttk.Checkbutton(f_item, text=lbl_text, variable=var, bootstyle="round-toggle")
                    w.pack(pady=5)
                    self.widgets.append({'type': 'check', 'widget': w, 'var': var})

            # CONTENEDOR DE BOTONES (Abajo, centrado o expandido)
            btn_frame = ttk.Frame(form_frame)
            btn_frame.pack(fill=X, pady=(15, 0)) # Margen superior para separar de inputs
            
            # Centramos los botones usando un frame interno
            center_btns = ttk.Frame(btn_frame)
            center_btns.pack(anchor=CENTER)

            self.btn_save = ttk.Button(center_btns, text="💾 Guardar", command=self.save, bootstyle="success", width=15)
            self.btn_save.pack(side=LEFT, padx=5)
            
            self.btn_cancel = ttk.Button(center_btns, text="🧹 Limpiar", command=self.clear_form, bootstyle="secondary", width=15)
            self.btn_cancel.pack(side=LEFT, padx=5)
            
            self.btn_delete = ttk.Button(center_btns, text="🗑 Eliminar", command=self.delete, bootstyle="danger", width=15)
            self.btn_delete.pack(side=LEFT, padx=5)

            # --- Tabla ---
            self.tree = ttk.Treeview(self, columns=[str(i) for i in range(len(self.columns))], show="headings", bootstyle="info")
            
            for i, col_name in enumerate(self.columns):
                self.tree.heading(str(i), text=col_name)
                # Ajuste automático de ancho básico
                width = 200 if "Nombre" in col_name else 100
                self.tree.column(str(i), width=width)
                    
            self.tree.pack(fill=BOTH, expand=True, pady=10, padx=5)
            
            # Scrollbar
            sb = ttk.Scrollbar(self.tree, orient=VERTICAL, command=self.tree.yview)
            self.tree.configure(yscroll=sb.set)
            sb.pack(side=RIGHT, fill=Y)

            self.tree.bind("<Double-1>", self.on_double_click)

    def refresh_table(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        rows = self.dao_fetch()
        for row in rows:
            # Cortamos la fila visualmente según las columnas definidas
            # (El DAO de tipos devuelve datos extra al final que no mostramos en tabla pero usamos al editar)
            visual_row = row[:len(self.columns)]
            self.tree.insert("", END, values=visual_row, tags=(row,)) # Guardamos toda la data en tags
            
    def on_double_click(self, event):
            sel = self.tree.selection()
            if not sel: return
            
            item = self.tree.item(sel[0])
            row_id = item['values'][0]

            # 1. Recuperar Data Real de BD
            full_rows = self.dao_fetch()
            actual_data = next((r for r in full_rows if r[0] == row_id), None)
            
            if not actual_data: return

            self.selected_id = row_id
            self.btn_save.config(text="Actualizar", bootstyle="warning")

            # --- ESTRATEGIA DE CURSORES ---
            # visual_idx: Para campos de texto (saltamos el ID en pos 0)
            visual_idx = 1 
            
            # raw_idx: Para Combos y Checks. 
            # Empieza justo donde terminan las columnas visibles de la tabla.
            raw_idx = len(self.columns) 

            for w_conf in self.widgets:
                
                # CASO 1: Campo de Texto (Generalmente mapea a columnas visuales)
                if w_conf['type'] == 'text':
                    val = actual_data[visual_idx]
                    w_conf['widget'].delete(0, END)
                    # Convertimos a string por si acaso es número, y manejamos None
                    w_conf['widget'].insert(0, str(val) if val is not None else "")
                    
                    visual_idx += 1 # Avanzamos al siguiente dato visual

                # CASO 2: Combos y Checks (Buscan IDs o Booleanos en la zona RAW u Oculta)
                elif w_conf['type'] in ['combo', 'check']:
                    
                    # Determinamos de dónde sacar el dato
                    if len(actual_data) > len(self.columns):
                        # Si hay datos ocultos (RAW), tomamos de ahí secuencialmente
                        val_raw = actual_data[raw_idx]
                        raw_idx += 1
                    else:
                        # Fallback para tablas simples sin datos ocultos
                        val_raw = actual_data[visual_idx]
                        visual_idx += 1

                    # APLICAR VALOR AL WIDGET
                    if w_conf['type'] == 'combo':
                        if val_raw is None:
                            w_conf['widget'].set('')
                        else:
                            # Buscar el texto que corresponde a ese ID en la lista fuente
                            # Comparamos como strings por seguridad si los IDs vienen mezclados
                            txt = next((x[1] for x in w_conf['source'] if str(x[0]) == str(val_raw)), "")
                            w_conf['widget'].set(txt)
                    
                    elif w_conf['type'] == 'check':
                        # Asegurar 1 o 0
                        is_checked = 1 if val_raw and int(val_raw) == 1 else 0
                        w_conf['var'].set(is_checked)

    def clear_form(self):
        self.selected_id = None
        for w in self.widgets:
            if w['type'] == 'text': w['widget'].delete(0, END)
            elif w['type'] == 'combo': w['widget'].set('')
            elif w['type'] == 'check': w['var'].set(1)
        self.btn_save.config(text="Guardar", bootstyle="success")
        self.tree.selection_remove(self.tree.selection())

    def save(self):
            params = []
            for w in self.widgets:
                if w['type'] == 'text':
                    val = w['widget'].get().strip()
                    # Validación básica para textos: obligatorios
                    if not val: 
                        Messagebox.show_error("Los campos de texto son obligatorios", "Error")
                        return
                    params.append(val)
                    
                elif w['type'] == 'combo':
                    txt = w['widget'].get()
                    
                    # --- CAMBIO CRÍTICO: Permitir Combos Vacíos ---
                    if not txt:
                        # Si no seleccionó nada, enviamos None (NULL en BD)
                        params.append(None)
                    else:
                        # Si seleccionó algo, buscamos su ID
                        # Usamos next con default None por seguridad
                        id_val = next((x[0] for x in w['source'] if x[1] == txt), None)
                        
                        if id_val is None:
                            # Caso raro: Texto en combo que no coincide con la lista (Usuario escribió a mano)
                            Messagebox.show_error(f"El valor '{txt}' no es válido en la lista.", "Error")
                            return
                        params.append(id_val)
                        
                elif w['type'] == 'check':
                    params.append(w['var'].get())

            # Ejecución del CRUD
            if self.selected_id:
                ok, msg = self.dao_crud("UPDATE", self.selected_id, *params)
            else:
                ok, msg = self.dao_crud("INSERT", None, *params)
                
            if ok:
                Messagebox.show_info(msg, "Éxito")
                self.clear_form()
                self.refresh_table()
                
                # --- TRUCO PRO: Refrescar la fuente de datos si es necesario ---
                # Si acabamos de guardar un Puesto que es Jefe, deberíamos recargar 
                # los combos para que aparezca disponible de inmediato.
                # Por simplicidad en este framework genérico, la solución rápida es:
                # El usuario deberá reiniciar la app o cambiar de pestaña para ver 
                # al nuevo jefe en la lista, O implementamos un reload (más complejo).
            else:
                Messagebox.show_error(msg, "Error")

    def delete(self):
        if not self.selected_id: return
        if Messagebox.yesno("¿Eliminar?", "Confirmar") == 'Yes':
            ok, msg = self.dao_crud("DELETE", self.selected_id)
            if ok: 
                self.clear_form()
                self.refresh_table()
            else:
                Messagebox.show_error(msg, "Error")