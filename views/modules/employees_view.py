import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from models.employee_dao import EmployeeDAO

class EmployeesView(ttk.Frame):
    def __init__(self, parent, controller=None):  
        super().__init__(parent)
        self.controller = controller  
        self.dao = EmployeeDAO()
        self.selected_id = None 
        
        # --- NUEVO: Cache de datos para búsqueda rápida ---
        self.all_rows = [] 
        
        self.pack(fill=BOTH, expand=True)
        
        # Variables Formulario
        self.var_codigo = ttk.StringVar()
        self.var_dni = ttk.StringVar()
        self.var_nombres = ttk.StringVar()
        self.var_apellidos = ttk.StringVar()
        self.var_fecha = ttk.StringVar()
        
        # --- NUEVO: Variable Búsqueda ---
        self.var_search = ttk.StringVar()
        self.var_search.trace("w", self._filter_data) # Activa filtro al escribir

        self._create_ui()
        self.load_table_data()

    def _create_ui(self):
        # 1. Formulario (Igual que antes)
        form_frame = ttk.Labelframe(self, text="Gestión de Colaborador", padding=10, bootstyle="primary")
        form_frame.pack(fill=X, padx=10, pady=5)

        ttk.Label(form_frame, text="Código/Reloj:").grid(row=0, column=0, sticky=W, padx=5)
        ttk.Entry(form_frame, textvariable=self.var_codigo, width=15).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(form_frame, text="DNI:").grid(row=0, column=2, sticky=W, padx=5)
        ttk.Entry(form_frame, textvariable=self.var_dni, width=20).grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(form_frame, text="Nombres:").grid(row=1, column=0, sticky=W, padx=5)
        ttk.Entry(form_frame, textvariable=self.var_nombres, width=30).grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(form_frame, text="Apellidos:").grid(row=1, column=2, sticky=W, padx=5)
        ttk.Entry(form_frame, textvariable=self.var_apellidos, width=30).grid(row=1, column=3, padx=5, pady=5)

        ttk.Label(form_frame, text="Fecha Nacimiento:").grid(row=2, column=0, sticky=W, padx=5)
        self.date_entry = ttk.DateEntry(form_frame, dateformat='%Y-%m-%d', startdate=None)
        self.date_entry.entry.configure(textvariable=self.var_fecha)
        self.date_entry.grid(row=2, column=1, padx=5, pady=5, sticky=W)

        # Botones de Acción
        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=2, column=3, sticky=E)
        
        self.btn_save = ttk.Button(btn_frame, text="Guardar Empleado", bootstyle="success", command=self.save_employee)
        self.btn_save.pack(side=LEFT, padx=5)

        self.btn_delete = ttk.Button(btn_frame, text="Eliminar", bootstyle="danger", command=self.delete_current_employee)
        self.btn_cancel = ttk.Button(btn_frame, text="Cancelar", bootstyle="secondary", command=self.clear_form)
        # Se hacen pack dinámicamente

        # ---------------------------------------------------------
        # 2. BARRA DE BÚSQUEDA (NUEVO BLOQUE)
        # ---------------------------------------------------------
        search_frame = ttk.Frame(self, padding=10)
        search_frame.pack(fill=X, padx=5) # Entre el formulario y la tabla
        
        ttk.Label(search_frame, text="🔍 Buscar (Nombre, DNI o Código):", bootstyle="info").pack(side=LEFT, padx=5)
        
        entry_search = ttk.Entry(search_frame, textvariable=self.var_search, width=50)
        entry_search.pack(side=LEFT, fill=X, expand=True, padx=5)
        
        # Botón para limpiar búsqueda rápidamente
        ttk.Button(search_frame, text="x", command=lambda: self.var_search.set(""), bootstyle="secondary-outline").pack(side=LEFT)

        # ---------------------------------------------------------
        # 3. TABLA (Treeview)
        # ---------------------------------------------------------
        table_frame = ttk.Frame(self, padding=10)
        table_frame.pack(fill=BOTH, expand=True)

        columns = ("id", "codigo", "dni", "nombres", "apellidos", "nacimiento")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", bootstyle="info")
        
        self.tree.heading("id", text="ID")
        self.tree.column("id", width=0, stretch=False)
        self.tree.heading("codigo", text="Cód.")
        self.tree.column("codigo", width=80)
        self.tree.heading("dni", text="DNI")
        self.tree.column("dni", width=120)
        self.tree.heading("nombres", text="Nombres")
        self.tree.heading("apellidos", text="Apellidos")
        self.tree.heading("nacimiento", text="F. Nacimiento")
        
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        
        sb = ttk.Scrollbar(table_frame, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=sb.set)
        sb.pack(side=RIGHT, fill=Y)

        self.tree.bind("<Double-1>", self.on_row_double_click)

    # --- LÓGICA DE DATOS Y FILTRADO (NUEVO) ---

    def load_table_data(self):
        """Carga datos de la BD a memoria y refresca la tabla"""
        # 1. Traer todo de la BD
        self.all_rows = self.dao.get_all()
        # 2. Aplicar el filtro actual (por si el usuario escribió algo y luego guardó un cambio)
        self._filter_data()

    def _filter_data(self, *args):
        """Filtra la lista en memoria según lo que escriba el usuario"""
        term = self.var_search.get().lower().strip()
        
        # Si está vacío, mostramos todo
        if not term:
            self._populate_tree(self.all_rows)
            return

        filtered_rows = []
        for row in self.all_rows:
            # row = (id, codigo, dni, nombres, apellidos, nacimiento)
            # Buscamos en Código(1), DNI(2), Nombres(3), Apellidos(4)
            full_text = f"{row[1]} {row[2]} {row[3]} {row[4]}".lower()
            
            if term in full_text:
                filtered_rows.append(row)
        
        self._populate_tree(filtered_rows)

    def _populate_tree(self, rows):
        """Limpia y rellena el Treeview"""
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        for row in rows:
            self.tree.insert("", END, values=row)

    # --- Lógica de Interacción (Existente, ligeramente ajustada) ---

    def on_row_double_click(self, event):
            selection = self.tree.selection()
            if not selection: return

            # 1. Obtenemos lo único que no cambia: el ID
            item = self.tree.item(selection[0])
            # Tkinter a veces devuelve el ID como int o str, aseguramos int para comparar
            selected_id = int(item['values'][0]) 
            
            # 2. Buscamos el registro ORIGINAL en nuestra caché de memoria (self.all_rows)
            # Esto garantiza que obtenemos "0801" (str) y no 801 (int)
            original_data = next((row for row in self.all_rows if row[0] == selected_id), None)

            if not original_data:
                return # Seguridad por si algo raro pasa

            # original_data es tupla: (id, codigo, dni, nombres, apellidos, nacimiento)
            
            self.selected_id = original_data[0]
            self.var_codigo.set(original_data[1])
            
            # AQUÍ ESTÁ LA MAGIA: Forzamos string explícitamente desde la fuente pura
            # Si original_data[2] es None, ponemos ""
            dni_real = str(original_data[2]) if original_data[2] is not None else ""
            self.var_dni.set(dni_real) 
            
            self.var_nombres.set(original_data[3])
            self.var_apellidos.set(original_data[4])
            self.var_fecha.set(original_data[5])
            
            # Configuración visual (igual que antes)
            self.btn_save.configure(text="Actualizar Empleado", bootstyle="warning")
            self.btn_cancel.pack(side=LEFT, padx=5)
            self.btn_delete.pack(side=LEFT, padx=5)

    def clear_form(self):
        self.selected_id = None
        self.var_codigo.set("")
        self.var_dni.set("")
        self.var_nombres.set("")
        self.var_apellidos.set("")
        
        # Opcional: ¿Quieres limpiar el buscador al cancelar? 
        # self.var_search.set("") 
        
        self.btn_save.configure(text="Guardar Empleado", bootstyle="success")
        self.btn_cancel.pack_forget()
        self.btn_delete.pack_forget()
        
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection())

    def save_employee(self):
        # Validaciones
        if not self.var_codigo.get() or not self.var_nombres.get():
            Messagebox.show_error("Código y Nombres son obligatorios.", "Error")
            return
        
        nombres = self.var_nombres.get().upper().strip()
        apellidos = self.var_apellidos.get().upper().strip()
        self.var_nombres.set(nombres)
        self.var_apellidos.set(apellidos)

        if self.selected_id is None:
            success, msg = self.dao.insert(
                self.var_codigo.get().strip(),
                self.var_dni.get().strip(),
                nombres,
                apellidos,
                self.var_fecha.get()
            )
        else:
            success, msg = self.dao.update(
                self.selected_id,
                self.var_codigo.get().strip(),
                self.var_dni.get().strip(),
                nombres,
                apellidos,
                self.var_fecha.get()
            )

        if success:
            Messagebox.show_info(msg, "Éxito")
            self.clear_form()
            self.load_table_data() # Esto refrescará la tabla manteniendo el filtro si lo deseas
        else:
            Messagebox.show_error(msg, "Error")

    def delete_current_employee(self):
        if not self.selected_id: return

        confirm = Messagebox.yesno(
            message="¿Está seguro que desea eliminar este empleado permanentemente?\nEsta acción es irreversible.",
            title="Confirmar Eliminación",
            alert=True
        )
        
        if confirm == 'Yes':
            success, message = self.dao.delete_employee(self.selected_id)
            if success:
                Messagebox.show_info(message, "Eliminado")
                self.clear_form()
                self.load_table_data()
            else:
                Messagebox.show_error(message, "No se pudo eliminar")