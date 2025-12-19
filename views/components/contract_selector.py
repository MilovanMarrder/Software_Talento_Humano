import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from models.contract_dao import ContractDAO

class ContractSelector(ttk.Toplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title("Búsqueda de Contrato")
        self.geometry("800x500")
        self.callback = callback # Función a ejecutar al seleccionar (id_contrato)
        self.dao = ContractDAO()
        
        self._setup_ui()
        # Cargar inicial (opcional, o dejar vacío)
        self.search()

    def _setup_ui(self):
        # --- Barra de Búsqueda ---
        search_frame = ttk.Frame(self, padding=10)
        search_frame.pack(fill=X)
        
        ttk.Label(search_frame, text="Buscar (Nombre, DNI, Puesto):").pack(side=LEFT, padx=5)
        self.entry_search = ttk.Entry(search_frame, width=40)
        self.entry_search.pack(side=LEFT, padx=5, fill=X, expand=True)
        self.entry_search.bind("<Return>", lambda e: self.search())
        
        ttk.Button(search_frame, text="🔍 Buscar", command=self.search, bootstyle="primary").pack(side=LEFT, padx=5)

        # --- Tabla Resultados ---
        columns = ("id", "empleado", "puesto", "tipo", "inicio", "estado")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", bootstyle="info")
        
        self.tree.heading("id", text="ID")
        self.tree.column("id", width=40, stretch=False)
        
        self.tree.heading("empleado", text="Colaborador")
        self.tree.column("empleado", width=250)
        
        self.tree.heading("puesto", text="Puesto")
        self.tree.column("puesto", width=150)

        self.tree.heading("tipo", text="Modalidad")
        self.tree.column("tipo", width=100)
        
        self.tree.heading("inicio", text="Fecha Inicio")
        self.tree.column("inicio", width=90)
        
        self.tree.heading("estado", text="Estado")
        self.tree.column("estado", width=70)
        
        self.tree.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        # Doble clic selecciona
        self.tree.bind("<Double-1>", self.on_double_click)
        
        ttk.Button(self, text="Cancelar", command=self.destroy, bootstyle="secondary-outline").pack(pady=5)

    def search(self):
        term = self.entry_search.get().strip()
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        rows = self.dao.search_contracts(term)
        for r in rows:
            # r = (id, emp, puesto, tipo, inicio, estado)
            self.tree.insert("", END, values=r)

    def on_double_click(self, event):
        selection = self.tree.selection()
        if not selection: return
        
        item = self.tree.item(selection[0])
        id_contrato = item['values'][0]
        
        if self.callback:
            self.callback(id_contrato)
            
        self.destroy()