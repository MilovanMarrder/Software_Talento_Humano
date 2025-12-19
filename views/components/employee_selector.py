import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from models.employee_dao import EmployeeDAO

class EmployeeSelector(ttk.Toplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title("Buscar Colaborador")
        self.geometry("600x400")
        self.callback = callback # Función a ejecutar al seleccionar
        self.dao = EmployeeDAO()
        
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        # Barra de búsqueda
        search_frame = ttk.Frame(self, padding=10)
        search_frame.pack(fill=X)
        
        ttk.Label(search_frame, text="Filtrar:").pack(side=LEFT)
        self.var_search = ttk.StringVar()
        self.var_search.trace("w", self._filter_data) # Filtrado en tiempo real
        entry = ttk.Entry(search_frame, textvariable=self.var_search)
        entry.pack(side=LEFT, fill=X, expand=True, padx=5)
        entry.focus() # Poner cursor aquí automáticamente

        # Tabla
        cols = ("id", "codigo", "nombre", "dni")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", bootstyle="primary")
        self.tree.heading("id", text="ID")
        self.tree.heading("codigo", text="Código")
        self.tree.heading("nombre", text="Nombre Completo")
        self.tree.heading("dni", text="DNI")
        
        self.tree.column("id", width=0, stretch=False) # Oculto
        self.tree.column("codigo", width=80)
        self.tree.column("dni", width=100)
        self.tree.column("nombre", width=250)
        
        self.tree.pack(fill=BOTH, expand=True, padx=10, pady=5)
        
        # Doble clic selecciona
        self.tree.bind("<Double-1>", self._on_select)
        
        ttk.Button(self, text="Seleccionar", command=self._on_select, bootstyle="success").pack(pady=10)

    def _load_data(self):
        # Traemos todos los empleados (optimización: si son miles, limitar query)
        self.all_data = self.dao.get_all() 
        # get_all retorna tuplas: (id, codigo, dni, nombres, apellidos, nac)
        # Procesamos para tener "Nombre Completo"
        self.processed_data = []
        for r in self.all_data:
            nombre_completo = f"{r[3]} {r[4]}"
            self.processed_data.append((r[0], r[1], nombre_completo, r[2]))
            
        self._populate_tree(self.processed_data)

    def _populate_tree(self, data):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in data:
            self.tree.insert("", END, values=row)

    def _filter_data(self, *args):
        query = self.var_search.get().lower()
        filtered = [
            row for row in self.processed_data 
            if query in row[1].lower() or query in row[2].lower() or query in row[3].lower()
        ]
        self._populate_tree(filtered)

    def _on_select(self, event=None):
        selected = self.tree.focus()
        if selected:
            values = self.tree.item(selected, 'values')
            # Retornamos ID, Código y Nombre a la ventana padre
            self.callback(values[0], values[1], values[2]) 
            self.destroy()