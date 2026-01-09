import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from models.employee_dao import EmployeeDAO
from tkinter import filedialog, messagebox 
import csv
import random
import datetime # <--- 1. IMPORT NECESARIO
from collections import defaultdict 

class OrgChartView(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.pack(fill=BOTH, expand=True)
        self.dao = EmployeeDAO()
        
        self.nodes_data = [] 
        self.tree_map = {} 
        
        self._setup_ui()
        self.load_data()


    def _setup_ui(self):
        toolbar = ttk.Frame(self, padding=5)
        toolbar.pack(fill=X)
        
        ttk.Button(toolbar, text="🔄 Actualizar", command=self.load_data, bootstyle="secondary-outline").pack(side=RIGHT, padx=5)
        
        # Botón 1: Full
        ttk.Button(toolbar, text="🧬 Organigrama Completo", command=self.generate_viz_code, bootstyle="info").pack(side=RIGHT, padx=5)
        
        # Botón 2: Resumido (NUEVO)
        ttk.Button(toolbar, text="📊 Organigrama Resumido", command=self.generate_condensed_viz_code, bootstyle="success").pack(side=RIGHT, padx=5)

        # ... (Resto del setup del Treeview igual que antes) ...
        tree_frame = ttk.Frame(self, padding=5)
        tree_frame.pack(fill=BOTH, expand=True)
        
        cols = ("empleado", "departamento", "jefe", "estado")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="tree headings")
        
        self.tree.heading("#0", text="Estructura (Puesto)")
        self.tree.column("#0", width=350, anchor=W)
        
        self.tree.heading("empleado", text="Ocupante")
        self.tree.column("empleado", width=250, anchor=W)

        self.tree.heading("departamento", text="Departamento")
        self.tree.column("departamento", width=200, anchor=W)

        self.tree.heading("jefe", text="Reporta A (Puesto)")
        self.tree.column("jefe", width=250, anchor=W)
        
        self.tree.heading("estado", text="Estado")
        self.tree.column("estado", width=80, anchor=CENTER)
        
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        vsb.pack(side=RIGHT, fill=Y)
        hsb.pack(side=BOTTOM, fill=X)
        self.tree.pack(fill=BOTH, expand=True)

        self.tree.tag_configure('vacante', foreground='#d9534f') 
        self.tree.tag_configure('ocupado', foreground='#2c3e50') 

    def load_data(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        self.tree_map = {}
        
        self.nodes_data = self.dao.get_org_chart_data()
        if not self.nodes_data: return

        all_ids = {n['id'] for n in self.nodes_data}
        roots = []
        
        for node in self.nodes_data:
            pid = node['parent_id']
            if pid not in self.tree_map: self.tree_map[pid] = []
            self.tree_map[pid].append(node)
            
            if pid is None or pid not in all_ids:
                roots.append(node)

        processed_roots = set()
        for root in roots:
            self._insert_node("", root)

    def _insert_node(self, parent_uuid, node_data):
        tag = 'vacante' if node_data['vacante'] else 'ocupado'
        icon = "👤" if not node_data['vacante'] else "⚠️"
        
        text_label = f"{node_data['puesto']}"
        
        item_id = self.tree.insert(
            parent_uuid, 
            END, 
            text=text_label, 
            values=(
                f"{icon} {node_data['empleado']}", 
                node_data['departamento'],
                node_data['puesto_jefe'], 
                "VACANTE" if node_data['vacante'] else "ACTIVO"
            ),
            tags=(tag,),
            open=True 
        )
        
        children = self.tree_map.get(node_data['id'], [])
        for child in children:
            self._insert_node(item_id, child)

    def expand_all(self):
        def recursive_expand(item):
            self.tree.item(item, open=True)
            for child in self.tree.get_children(item): recursive_expand(child)
        for item in self.tree.get_children(): recursive_expand(item)

    # -------------------------------------------------------------------------
    # CORRECCIÓN EN EL GENERADOR DE CÓDIGO
    # -------------------------------------------------------------------------
    def generate_viz_code(self):
        """Genera un archivo .txt con el código Python para crear el organigrama"""
        if not self.nodes_data:
            messagebox.showwarning("Sin datos", "No hay datos para generar el organigrama.")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text File", "*.txt"), ("Python File", "*.py")],
            title="Guardar Código Fuente del Organigrama"
        )
        if not filename: return

        try:
            # 1. Preparar listas
            l_ids = []
            l_nombres = []
            l_puestos = []
            l_deptos = []
            l_jefes = []

            deptos_unicos = set()

            for node in self.nodes_data:
                my_id = node['id']
                pid = node['parent_id'] if node['parent_id'] else "None"
                
                name = node['empleado']
                if node['vacante']: name = f"[VACANTE] {node['puesto']}"
                
                # Sanitizar strings para evitar errores de sintaxis en el archivo generado
                name = str(name).replace("'", "").replace('"', "")
                puesto = str(node['puesto']).replace("'", "")
                depto = str(node['departamento']).replace("'", "")

                l_ids.append(my_id)
                l_nombres.append(name)
                l_puestos.append(puesto)
                l_deptos.append(depto)
                l_jefes.append(pid)
                
                deptos_unicos.add(depto)

            # 2. Generar paleta de colores
            dict_colores_str = "colores = {\n"
            colores_pastel = ['#FFD700', '#ADD8E6', '#FFB6C1', '#98FB98', '#FFA07A', '#E0FFFF', '#D8BFD8', '#F0E68C']
            # Convertimos el set a lista para poder indexar
            lista_deptos = list(deptos_unicos)
            
            for i, d in enumerate(lista_deptos):
                color = colores_pastel[i % len(colores_pastel)]
                dict_colores_str += f"    '{d}': '{color}',\n"
            dict_colores_str += "}"

            # 3. Calcular la fecha HOY (CORRECCIÓN AQUÍ)
            fecha_hoy = datetime.datetime.now().strftime('%Y-%m-%d') # <--- CALCULADO FUERA

            # 4. CONSTRUIR EL SCRIPT
            script_content = f"""
import pandas as pd
import graphviz
import os

# ==========================================
# SCRIPT GENERADO POR SISTEMA HMEP
# FECHA: {fecha_hoy} 
# ==========================================

# 1. DATOS (Extraídos de la Base de Datos)
data = {{
    'ID_Empleado': {l_ids},
    'Nombre': {l_nombres},
    'Puesto': {l_puestos},
    'Departamento': {l_deptos},
    'ID_Jefe': {l_jefes}
}}

df = pd.DataFrame(data)

# 2. CONFIGURACIÓN GRAPHVIZ
dot = graphviz.Digraph(comment='Organigrama HMEP')
dot.attr(rankdir='TB')     # Top to Bottom
dot.attr(splines='ortho')  # Líneas ortogonales (rectas)
dot.attr('node', shape='box', style='filled', fontname='Segoe UI', margin='0.2')

# --- ENCABEZADO ---
url_logo = "https://cdn-icons-png.flaticon.com/512/2855/2855324.png" 
titulo = "Estructura Organizacional HMEP"

html_header = f'''<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0">
  <TR>
    <TD ALIGN="LEFT">
        <FONT POINT-SIZE="20" COLOR="BLACK"><B>{{titulo}}</B></FONT><BR/>
        <FONT POINT-SIZE="12" COLOR="GRAY">Generado Automáticamente</FONT>
    </TD>
    <TD WIDTH="60"></TD>
    <TD ALIGN="RIGHT">
        <IMG SRC="{{url_logo}}" SCALE="TRUE" HEIGHT="50"/>
    </TD>
  </TR>
</TABLE>>'''

# Nodo invisible para el título
dot.node('Header', label=html_header, shape='plaintext', style='')

# 3. COLORES POR DEPARTAMENTO
{dict_colores_str}

# 4. GENERAR NODOS
root_ids = [] # Lista para conectar encabezado

for index, row in df.iterrows():
    node_id = str(row['ID_Empleado'])
    
    # Si ID_Jefe es NaN o None, es raíz
    if pd.isna(row['ID_Jefe']) or row['ID_Jefe'] == 'None':
        root_ids.append(node_id)
    
    # Formato HTML del nodo
    label_html = f"<{{row['Nombre']}}<br/><i><font point-size='10'>{{row['Puesto']}}</font></i>>"
    
    color = colores.get(row['Departamento'], '#FFFFFF')
    
    dot.node(node_id, label=label_html, fillcolor=color)

# 5. GENERAR CONEXIONES (ARISTAS)
for index, row in df.iterrows():
    jefe_id = row['ID_Jefe']
    
    if pd.notna(jefe_id) and jefe_id != 'None':
        jefe_id_str = str(int(float(jefe_id))) if isinstance(jefe_id, (int, float)) else str(jefe_id)
        node_id_str = str(row['ID_Empleado'])
        
        if jefe_id_str != node_id_str:
            dot.edge(jefe_id_str, node_id_str)

# 6. CONECTAR ENCABEZADO A LAS RAÍCES (CEOs)
for rid in root_ids:
    dot.edge('Header', rid, style='invis', minlen='2')

# 7. GUARDAR Y RENDERIZAR
output_name = "organigrama_render"
try:
    dot.render(output_name, view=True, format='pdf', cleanup=False)
    print(f"✅ Éxito: Se generó {{output_name}}.pdf")
except Exception as e:
    print(f"⚠ Aviso: No se pudo compilar el PDF localmente (¿Tienes Graphviz instalado?).")
    print("Copia el contenido de 'dot.source' en: https://dreampuf.github.io/GraphvizOnline/")
    
    # Guardar el source para web
    with open("codigo_web.txt", "w", encoding="utf-8") as f:
        f.write(dot.source)

"""
            # 5. GUARDAR EL ARCHIVO FÍSICO
            with open(filename, "w", encoding="utf-8") as f:
                f.write(script_content)

            messagebox.showinfo("Éxito", f"Script generado en:\n{filename}\n\nPuedes ejecutar este archivo con Python para crear el PDF.")

        except Exception as e:
            messagebox.showerror("Error", f"Error generando script: {e}")


# -------------------------------------------------------------------------
    # VERSIÓN FINAL: ORGANIGRAMA RESUMIDO CON DISTRIBUCIÓN HÍBRIDA
    # -------------------------------------------------------------------------
    def generate_condensed_viz_code(self):
        """
        Genera un archivo TXT con el código Graphviz para un organigrama resumido.
        Usa lógica de distribución híbrida (Horizontal para Jefes, Vertical para Staff).
        """
        if not self.nodes_data:
            messagebox.showwarning("Sin datos", "No hay datos para generar.")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text File", "*.txt")],
            title="Guardar Código Graphviz (.txt)"
        )
        if not filename: return

        # --- 1. PROCESAMIENTO DE DATOS (Igual que antes) ---
        # Identificar raíces y huérfanos
        all_ids_in_data = {n['id'] for n in self.nodes_data}
        roots = []
        for node in self.nodes_data:
            if node['parent_id'] is None or node['parent_id'] not in all_ids_in_data:
                roots.append(node)

        real_roots = []
        orphans = []
        
        for r in roots:
            if r['id'] in self.tree_map and len(self.tree_map[r['id']]) > 0:
                real_roots.append(r)
            else:
                orphans.append(r)

        # Preparar listas
        l_ids = []
        l_labels = []
        l_deptos = []
        l_parents = []

        # Recorrer árbol (BFS)
        queue = real_roots[:]
        processed = set()

        while queue:
            current_node = queue.pop(0)
            current_id = current_node['id']
            
            if current_id in processed: continue
            processed.add(current_id)

            self._add_node_to_lists(current_node, l_ids, l_labels, l_deptos, l_parents)
            
            children = self.tree_map.get(current_id, [])
            sub_jefes = []
            hojas = []
            
            for child in children:
                child_id = child['id']
                if child_id in self.tree_map and len(self.tree_map[child_id]) > 0:
                    sub_jefes.append(child)
                else:
                    hojas.append(child)
            
            queue.extend(sub_jefes)
            
            if hojas:
                groups = defaultdict(list)
                for h in hojas:
                    puesto_clean = h['puesto'].strip()
                    groups[puesto_clean].append(h)
                
                for puesto_nombre, lista_empleados in groups.items():
                    qty = len(lista_empleados)
                    fake_id = f"GRP_{current_id}_{puesto_nombre}".replace(" ", "_")
                    
                    if qty == 1:
                        emp_nombre = lista_empleados[0]['empleado']
                        if lista_empleados[0]['vacante']: emp_nombre = "[VACANTE]"
                        label_html = f"<b>{puesto_nombre}</b><br/>{emp_nombre}"
                    else:
                        label_html = f"<b>{puesto_nombre}</b><br/><i>({qty} Colaboradores)</i>"
                    
                    l_ids.append(fake_id)
                    l_labels.append(label_html)
                    l_deptos.append(lista_empleados[0]['departamento'])
                    l_parents.append(current_id)

        # Agregar bloque huérfanos si existen
        if orphans:
            qty_orphans = len(orphans)
            orphan_id = "BLOCK_NO_JEFE"
            l_ids.append(orphan_id)
            l_labels.append(f"⚠️ Sin Asignar ({qty_orphans})") # Etiqueta simple, se procesa en el script
            l_deptos.append("Sin Asignar")
            l_parents.append("None")

        # --- 2. GENERAR EL SCRIPT PYTHON ---
        # Aquí inyectamos el código que tú proporcionaste, pero con los datos reales.
        
        fecha_hoy = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # IMPORTANTE: Escapar las llaves { } del f-string duplicándolas {{ }}
        script_content = f"""import pandas as pd
import graphviz

# ==========================================
# ORGANIGRAMA RESUMIDO HMEP
# Fecha Generación: {fecha_hoy}
# ==========================================

def generar_organigrama():
    # 1. DATOS REALES DE LA BD
    data = {{
        'ID': {l_ids},
        'Label': {l_labels},
        'Departamento': {l_deptos},
        'Parent_ID': {l_parents}
    }}
    
    df = pd.DataFrame(data)
    titulo = "Organigrama Institucional HMEP"
    
    # 2. COLORES DINÁMICOS
    paleta_colores = [
        '#FFD700', '#ADD8E6', '#FFB6C1', '#98FB98', '#FFA07A', '#E0FFFF', 
        '#D8BFD8', '#F0E68C', '#FFDEAD', '#B0E0E6', '#F5DEB3', '#FFFACD'
    ]
    
    deptos_unicos = df['Departamento'].dropna().unique().tolist()
    mapa_colores = {{}}
    for i, depto in enumerate(deptos_unicos):
        color = paleta_colores[i % len(paleta_colores)]
        mapa_colores[depto] = color

    # 3. CONFIGURACIÓN
    dot = graphviz.Digraph(comment=titulo)
    dot.attr(rankdir='TB')
    dot.attr(splines='ortho')
    dot.attr(nodesep='0.6')
    dot.attr(ranksep='0.6')
    dot.attr('node', shape='box', style='filled', fontname='Segoe UI', margin='0.1', width='2.5')

    # 4. HEADER
    url_logo = "https://cdn-icons-png.flaticon.com/512/2855/2855324.png"
    html_header = f'''<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0">
      <TR>
        <TD ALIGN="LEFT">
            <FONT POINT-SIZE="20" COLOR="BLACK"><B>{{titulo}}</B></FONT><BR/>
            <FONT POINT-SIZE="12" COLOR="GRAY">Generado Automáticamente</FONT>
        </TD>
        <TD WIDTH="60"></TD>
        <TD ALIGN="RIGHT"><IMG SRC="{{url_logo}}" SCALE="TRUE" HEIGHT="50"/></TD>
      </TR>
    </TABLE>>'''
    
    dot.node('Header', label=html_header, shape='plaintext', style='', width='5')

    # 5. GENERAR NODOS
    created_nodes = set()
    root_ids = []

    for index, row in df.iterrows():
        nid = str(row['ID'])
        pid = str(row['Parent_ID'])
        
        # Detectar Raíces
        if (pid == 'None' or pid == 'nan' or pd.isna(row['Parent_ID'])) and nid != 'BLOCK_NO_JEFE':
            root_ids.append(nid)

        # Caso Huérfanos
        if nid == 'BLOCK_NO_JEFE':
            label_huerfano = "<<TABLE BORDER='0' CELLBORDER='1' CELLSPACING='0' BGCOLOR='#f2dede'><TR><TD><B>⚠️ Sin Asignar</B></TD></TR></TABLE>>"
            dot.node(nid, label=label_huerfano, shape='plaintext', style='')
            created_nodes.add(nid)
            continue
            
        label_html = f"<{{row['Label']}}>"
        bg_color = mapa_colores.get(row['Departamento'], '#FFFFFF') 
        
        estilo = 'filled'
        shape = 'box'
        
        if str(nid).startswith('GRP_'):
            estilo = 'filled,dashed'
            shape = 'note'
        
        dot.node(nid, label=label_html, fillcolor=bg_color, style=estilo, shape=shape)
        created_nodes.add(nid)

    # 6. CONEXIONES INTELIGENTES
    children_map = {{}}
    for index, row in df.iterrows():
        pid = str(row['Parent_ID'])
        nid = str(row['ID'])
        if pid != 'None' and pid != 'nan' and nid != 'BLOCK_NO_JEFE':
            if pid not in children_map: children_map[pid] = []
            children_map[pid].append(nid)

    for parent, children in children_map.items():
        if parent not in created_nodes: continue

        vertical_kids = [child for child in children if str(child).startswith('GRP_')]
        horizontal_kids = [child for child in children if not str(child).startswith('GRP_')]

        # A) Horizontales
        if horizontal_kids:
            with dot.subgraph() as s:
                s.attr(rank='same')
                for child in horizontal_kids:
                    dot.edge(parent, child)
                    s.node(child)

        # B) Verticales
        if vertical_kids:
            dot.edge(parent, vertical_kids[0])
            for i in range(1, len(vertical_kids)):
                dot.edge(parent, vertical_kids[i], constraint='false')
            for i in range(len(vertical_kids) - 1):
                dot.edge(vertical_kids[i], vertical_kids[i+1], style='invis')

    # 7. HEADER & SALIDA
    for rid in root_ids:
        dot.edge('Header', rid, style='invis', minlen='2')
        
    if 'BLOCK_NO_JEFE' in created_nodes:
        dot.edge('Header', 'BLOCK_NO_JEFE', style='invis')

    return dot.source

# --- EJECUCIÓN ---
if __name__ == "__main__":
    codigo = generar_organigrama()
    print("--------------------------------------------------")
    print("CÓDIGO GRAPHVIZ GENERADO EXITOSAMENTE")
    print("--------------------------------------------------")
    print(codigo)
    
    # Opcional: Guardar automáticamente si se ejecuta directo
    with open("organigrama_debug.txt", "w", encoding="utf-8") as f:
        f.write(codigo)
"""
        
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(script_content)
            messagebox.showinfo("Éxito", f"Script de generación guardado en:\n{filename}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _add_node_to_lists(self, node, l_ids, l_labels, l_deptos, l_parents, is_group=False):
        """Helper para agregar nodos normales (Jefes) a las listas"""
        # ID
        l_ids.append(node['id'])
        
        # Parent
        pid = node['parent_id'] if node['parent_id'] else "None"
        l_parents.append(pid)
        
        # Depto
        l_deptos.append(node['departamento'])
        
        # Label HTML
        nombre = node['empleado']
        if node['vacante']: nombre = f"<font color='red'>[VACANTE]</font>"
        puesto = node['puesto']
        
        label = f"<b>{nombre}</b><br/><i><font point-size='10'>{puesto}</font></i>"
        l_labels.append(label)