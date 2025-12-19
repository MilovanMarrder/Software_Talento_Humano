import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from models.employee_dao import EmployeeDAO

class EmployeesView(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.dao = EmployeeDAO()
        self.selected_id = None # ESTADO: None = Creando, Numero = Editando
        
        self.pack(fill=BOTH, expand=True)
        
        # Variables
        self.var_codigo = ttk.StringVar()
        self.var_dni = ttk.StringVar()
        self.var_nombres = ttk.StringVar()
        self.var_apellidos = ttk.StringVar()
        self.var_fecha = ttk.StringVar()

        self._create_ui()
        self.load_table_data()

    def _create_ui(self):
        # --- Formulario ---
        form_frame = ttk.Labelframe(self, text="Gestión de Colaborador", padding=10, bootstyle="primary")
        form_frame.pack(fill=X, padx=10, pady=5)

        # Fila 0
        ttk.Label(form_frame, text="Código/Reloj:").grid(row=0, column=0, sticky=W, padx=5)
        ttk.Entry(form_frame, textvariable=self.var_codigo, width=15).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(form_frame, text="DNI:").grid(row=0, column=2, sticky=W, padx=5)
        ttk.Entry(form_frame, textvariable=self.var_dni, width=20).grid(row=0, column=3, padx=5, pady=5)

        # Fila 1
        ttk.Label(form_frame, text="Nombres:").grid(row=1, column=0, sticky=W, padx=5)
        ttk.Entry(form_frame, textvariable=self.var_nombres, width=30).grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(form_frame, text="Apellidos:").grid(row=1, column=2, sticky=W, padx=5)
        ttk.Entry(form_frame, textvariable=self.var_apellidos, width=30).grid(row=1, column=3, padx=5, pady=5)

        # Fila 2
        ttk.Label(form_frame, text="Fecha Nacimiento:").grid(row=2, column=0, sticky=W, padx=5)
        self.date_entry = ttk.DateEntry(form_frame, dateformat='%Y-%m-%d', startdate=None)
        self.date_entry.entry.configure(textvariable=self.var_fecha)
        self.date_entry.grid(row=2, column=1, padx=5, pady=5, sticky=W)

        # Botones de Acción
        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=2, column=3, sticky=E)

        # Referencia al botón para cambiarle el texto luego
        self.btn_save = ttk.Button(btn_frame, text="Guardar Empleado", bootstyle="success", command=self.save_employee)
        self.btn_save.pack(side=LEFT, padx=5)

        self.btn_cancel = ttk.Button(btn_frame, text="Cancelar", bootstyle="secondary", command=self.clear_form)
        self.btn_cancel.pack(side=LEFT)
        self.btn_cancel.hide = lambda: self.btn_cancel.pack_forget() # Helper
        self.btn_cancel.show = lambda: self.btn_cancel.pack(side=LEFT) # Helper
        self.btn_cancel.hide() # Oculto al inicio

        # --- Tabla ---
        table_frame = ttk.Frame(self, padding=10)
        table_frame.pack(fill=BOTH, expand=True)

        columns = ("id", "codigo", "dni", "nombres", "apellidos", "nacimiento")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", bootstyle="info")
        
        # Configurar columnas
        self.tree.heading("id", text="ID")
        self.tree.column("id", width=0, stretch=False) # Oculto visualmente pero accesible
        self.tree.heading("codigo", text="Cód.")
        self.tree.column("codigo", width=80)
        self.tree.heading("dni", text="DNI")
        self.tree.column("dni", width=120)
        self.tree.heading("nombres", text="Nombres")
        self.tree.heading("apellidos", text="Apellidos")
        self.tree.heading("nacimiento", text="F. Nacimiento")
        
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        
        # Scrollbar
        sb = ttk.Scrollbar(table_frame, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=sb.set)
        sb.pack(side=RIGHT, fill=Y)

        # EVENTO DE SELECCIÓN
        self.tree.bind("<Double-1>", self.on_row_double_click)

    def load_table_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        rows = self.dao.get_all()
        for row in rows:
            self.tree.insert("", END, values=row)

    def on_row_double_click(self, event):
        """Carga los datos de la fila en el formulario para editar"""
        selection = self.tree.selection()
        if not selection: return

        # Obtener datos de la fila
        item = self.tree.item(selection[0])
        values = item['values']
        
        # values = [id, codigo, dni, nombres, apellidos, fecha]
        self.selected_id = values[0]
        self.var_codigo.set(values[1])
        self.var_dni.set(values[2])
        self.var_nombres.set(values[3])
        self.var_apellidos.set(values[4])
        self.var_fecha.set(values[5])
        
        # Cambiar estado visual
        self.btn_save.configure(text="Actualizar Empleado", bootstyle="warning")
        self.btn_cancel.show()

    def clear_form(self):
        """Reinicia el formulario al estado 'Crear'"""
        self.selected_id = None
        self.var_codigo.set("")
        self.var_dni.set("")
        self.var_nombres.set("")
        self.var_apellidos.set("")
        # Limpiar fecha (opcional, depende de DateEntry)
        
        self.btn_save.configure(text="Guardar Empleado", bootstyle="success")
        self.btn_cancel.hide()
        self.tree.selection_remove(self.tree.selection()) # Deseleccionar tabla

    def save_employee(self):
            # 1. Validaciones
            if not self.var_codigo.get() or not self.var_nombres.get():
                Messagebox.show_error("Código y Nombres son obligatorios.", "Error")
                return
            
            # Conversión a Mayúsculas
            nombres = self.var_nombres.get().upper().strip()
            apellidos = self.var_apellidos.get().upper().strip()
            
            # Reflejar en UI
            self.var_nombres.set(nombres)
            self.var_apellidos.set(apellidos)

            # 2. Decidir si es Insert o Update
            # (AQUÍ YA ELIMINAMOS EL BLOQUE DUPLICADO QUE TENÍAS ANTES)
            
            if self.selected_id is None:
                # MODO CREAR
                success, msg = self.dao.insert(
                    self.var_codigo.get().strip(),
                    self.var_dni.get().strip(),
                    nombres,
                    apellidos,
                    self.var_fecha.get()
                )
            else:
                # MODO EDITAR
                success, msg = self.dao.update(
                    self.selected_id,
                    self.var_codigo.get().strip(),
                    self.var_dni.get().strip(),
                    nombres,
                    apellidos,
                    self.var_fecha.get()
                )

            # 3. Respuesta
            if success:
                Messagebox.show_info(msg, "Éxito")
                self.clear_form()
                self.load_table_data()
            else:
                Messagebox.show_error(msg, "Error")