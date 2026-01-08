import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from models.contract_dao import ContractDAO

class ContractSelector(ttk.Toplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title("Búsqueda de Contrato")
        self.geometry("900x550")
        self.callback = callback 
        self.dao = ContractDAO()
        
        # Lista en memoria para filtrado rápido
        self.all_data = []      # Datos crudos de BD
        self.view_data = []     # Datos formateados para visualización
        
        self._setup_ui()
        self._load_data() # Carga inicial automática

    def _setup_ui(self):
        # --- Barra de Búsqueda ---
        search_frame = ttk.Frame(self, padding=10)
        search_frame.pack(fill=X)
        
        ttk.Label(search_frame, text="Filtrar (Nombre, DNI, Puesto, Código):").pack(side=LEFT, padx=5)
        
        # Variable de control para "search-as-you-type"
        self.var_search = ttk.StringVar()
        self.var_search.trace("w", self._filter_data) 
        
        self.entry_search = ttk.Entry(search_frame, textvariable=self.var_search, width=40)
        self.entry_search.pack(side=LEFT, padx=5, fill=X, expand=True)
        self.entry_search.focus() # Foco automático al abrir

        # --- Tabla Resultados ---
        # Definimos las columnas lógicas
        columns = ("id", "codigo", "empleado", "dni", "puesto", "tipo", "inicio", "estado")
        
        self.tree = ttk.Treeview(self, columns=columns, show="headings", bootstyle="info")
        
        # 1. Configurar ID para que esté oculto
        self.tree.column("id", width=0, stretch=False) 
        self.tree.heading("id", text="") # Sin texto en cabecera

        # 2. Configurar resto de columnas
        self.tree.heading("codigo", text="Cód.")
        self.tree.column("codigo", width=60)

        self.tree.heading("empleado", text="Colaborador")
        self.tree.column("empleado", width=220)
        
        self.tree.heading("dni", text="DNI")
        self.tree.column("dni", width=100)
        
        self.tree.heading("puesto", text="Puesto")
        self.tree.column("puesto", width=150)

        self.tree.heading("tipo", text="Modalidad")
        self.tree.column("tipo", width=100)
        
        self.tree.heading("inicio", text="Inicio")
        self.tree.column("inicio", width=80)
        
        self.tree.heading("estado", text="Est.")
        self.tree.column("estado", width=60)
        
        self.tree.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        # Scrollbar vertical
        sb = ttk.Scrollbar(self, orient=VERTICAL, command=self.tree.yview)
        sb.place(relx=1, rely=0, relheight=1, anchor=NE)
        self.tree.configure(yscroll=sb.set)

        # Bindings
        self.tree.bind("<Double-1>", self.on_double_click)
        # Permitir seleccionar con Enter también
        self.tree.bind("<Return>", self.on_double_click)
        
        # Botón cerrar inferior
        ttk.Button(self, text="Cancelar", command=self.destroy, bootstyle="secondary-outline").pack(pady=5)

        self.tree.tag_configure('gray', foreground='#999999')

    def _load_data(self):
        """Carga todos los contratos en memoria una sola vez"""
        raw_rows = self.dao.get_all_contracts_summary()
        
        # Procesamos si es necesario (ej: formatear fechas), aquí pasan directo
        # raw_row = (id, codigo, nombre_completo, dni, puesto, tipo, inicio, estado)
        self.all_data = raw_rows
        
        # Llenamos la tabla inicialmente con todo
        self._populate_tree(self.all_data)

    def _filter_data(self, *args):
        """Filtra la lista en memoria basándose en lo que escribe el usuario"""
        term = self.var_search.get().lower().strip()
        
        if not term:
            self._populate_tree(self.all_data)
            return

        filtered = []
        for row in self.all_data:
            # Buscamos coincidencias en: Código, Nombre, DNI o Puesto
            # row[1]=cod, row[2]=nombre, row[3]=dni, row[4]=puesto
            match_str = f"{row[1]} {row[2]} {row[3]} {row[4]}".lower()
            
            if term in match_str:
                filtered.append(row)
        
        self._populate_tree(filtered)

    def _populate_tree(self, data_list):
        # Limpieza rápida
        self.tree.delete(*self.tree.get_children())
        
        # Inserción masiva (Tkinter es rápido insertando si no son millones)
        for item in data_list:
            # item = (id, codigo, nombre, dni, puesto, tipo, inicio, estado)
            
            # Colorear filas según estado (Opcional, mejora visual)
            # tags = ('activo',) if item[7] == 'Activo' else ('inactivo',)
            tag = 'gray' if item[7] == 'Inactivo' else 'normal'
            self.tree.insert("", END, values=item, tags=(tag,))


    def on_double_click(self, event):
        selection = self.tree.selection()
        if not selection: return
        
        item = self.tree.item(selection[0])
        # values[0] sigue siendo el ID aunque esté oculto visualmente
        id_contrato = item['values'][0]
        
        if self.callback:
            self.callback(id_contrato)
            
        self.destroy()