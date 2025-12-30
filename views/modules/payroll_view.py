import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox
from datetime import datetime
import threading

# Importamos lógica y modelos
from logics.payroll_import_service import PayrollImportService
from models.payroll_dao import PayrollDAO

class PayrollView(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        # Servicios
        self.service = PayrollImportService()
        self.dao = PayrollDAO()
        
        self.pack(fill=BOTH, expand=True, padx=20, pady=20)

        # --- HEADER ---
        lbl_title = ttk.Label(self, text="Gestión de Planillas Mensuales", font=("Helvetica", 16, "bold"))
        lbl_title.pack(pady=(0, 20), anchor="w")

        # --- CONTROLES SUPERIORES (FILTROS Y ACCIONES) ---
        controls_frame = ttk.Labelframe(self, text="Acciones y Filtros", padding=10)
        controls_frame.pack(fill=X, pady=(0, 10))
        
        # Fila 1: Selección de Periodo
        row_filter = ttk.Frame(controls_frame)
        row_filter.pack(fill=X, pady=(0, 10))

        ttk.Label(row_filter, text="Mes:").pack(side=LEFT, padx=(0, 5))
        self.combo_mes = ttk.Combobox(row_filter, values=[
            "01", "02", "03", "04", "05", "06", 
            "07", "08", "09", "10", "11", "12"
        ], state="readonly", width=5)
        current_month = datetime.now().month
        self.combo_mes.current(current_month - 1)
        self.combo_mes.pack(side=LEFT, padx=(0, 15))

        ttk.Label(row_filter, text="Año:").pack(side=LEFT, padx=(0, 5))
        self.spin_anio = ttk.Spinbox(row_filter, from_=2020, to=2030, width=8)
        self.spin_anio.set(datetime.now().year)
        self.spin_anio.pack(side=LEFT, padx=(0, 15))

        btn_refresh = ttk.Button(row_filter, text="🔍 Consultar Planilla", bootstyle="primary-outline", command=self.load_data)
        btn_refresh.pack(side=LEFT)

        # Fila 2: Botones de Operación (Derecha)
        row_actions = ttk.Frame(controls_frame)
        row_actions.pack(fill=X, pady=(10, 0))

        # Botón 1: Descargar Plantilla
        btn_template = ttk.Button(
            row_actions, 
            text="⬇ 1. Descargar Plantilla", 
            bootstyle="info", 
            command=self.download_template
        )
        btn_template.pack(side=LEFT, padx=(0, 10))

        # Botón 2: Subir Excel
        btn_upload = ttk.Button(
            row_actions, 
            text="⬆ 2. Cargar Excel Completado", 
            bootstyle="success", 
            command=self.upload_payroll
        )
        btn_upload.pack(side=LEFT)

        # --- Botón Eliminar Periodo ---
        btn_delete_period = ttk.Button(
            row_actions,
            text="🗑 Eliminar Periodo",
            bootstyle="danger-outline", # Rojo delineado para precaución
            command=self.delete_current_period
        )
        btn_delete_period.pack(side=LEFT, padx=(10, 0))

        # Loading
        self.progress = ttk.Progressbar(row_actions, mode='indeterminate', bootstyle="success-striped")
        # (Se empaca solo cuando se usa)

        # --- TABLA DE DATOS (TREEVIEW) ---
        # Columnas para ver el resumen
        cols = ("id","empleado", "puesto", "base", "bonos", "beneficios", "deducciones", "total", "obs")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=15)
        
        # Configuración de Cabeceras
        self.tree.heading("id", text="ID") # Necesario aunque no se vea
        self.tree.heading("empleado", text="Colaborador")
        self.tree.heading("puesto", text="Puesto")
        self.tree.heading("base", text="Salario Base")
        self.tree.heading("bonos", text="Bonificaciones")
        self.tree.heading("beneficios", text="Beneficios")
        self.tree.heading("deducciones", text="Deducciones")
        self.tree.heading("total", text="TOTAL PAGADO")
        self.tree.heading("obs", text="Observaciones")

        # Configuración de Columnas
        self.tree.column("id", width=0, stretch=NO)
        self.tree.column("empleado", width=250)
        self.tree.column("puesto", width=150)
        self.tree.column("base", width=100, anchor="e")
        self.tree.column("bonos", width=100, anchor="e")
        self.tree.column("beneficios", width=100, anchor="e")
        self.tree.column("deducciones", width=100, anchor="e")
        self.tree.column("total", width=120, anchor="e")
        self.tree.column("obs", width=200)

        # 3. BINDING PARA DOBLE CLIC (EDICIÓN)
        self.tree.bind("<Double-1>", self.on_double_click)

        # Scrollbar
        scrolly = ttk.Scrollbar(self, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrolly.set)
        
        self.tree.pack(side=LEFT, fill=BOTH, expand=True, pady=10)
        scrolly.pack(side=RIGHT, fill=Y, pady=10)

        # --- FOOTER (TOTALES) ---
        self.lbl_total_general = ttk.Label(self, text="Total Planilla Mes: L. 0.00", font=("Helvetica", 12, "bold"), bootstyle="inverse-primary")
        self.lbl_total_general.pack(fill=X, pady=10, ipady=5)

    # ---------------- LÓGICA DE INTERFAZ ----------------

    def load_data(self):
        """Consulta la BD y llena la tabla"""
        # Limpiar tabla
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        anio = int(self.spin_anio.get())
        mes = int(self.combo_mes.get())
        
        # Usamos el método especial del DAO que hace los JOINs
        rows = self.dao.get_payroll_summary_by_period(anio, mes)
        
        total_acumulado = 0.0

        for row in rows:
            # row estructura según el DAO: 
            # (codigo, empleado, puesto, salario, bonos, beneficios, deducciones, total, obs)
            # Mapeamos a las columnas del Treeview
            id_nomina = row[0] # Capturamos el ID
            
            # Formateos
            salario = f"L. {row[4]:,.2f}"
            bonos = f"L. {row[5]:,.2f}"
            beneficios = f"L. {row[6]:,.2f}"
            deducciones = f"L. {row[7]:,.2f}"
            total = f"L. {row[8]:,.2f}"
            
            total_acumulado += row[8]
            
            # Insertamos ID en la primera posición (aunque esté oculta)
            values = (id_nomina, row[2], row[3], salario, bonos, beneficios, deducciones, total, row[9])
            self.tree.insert("", END, values=values)
            
        self.lbl_total_general.config(text=f"  Total Planilla Mes {mes}/{anio}: L. {total_acumulado:,.2f}  ")
    def download_template(self):
        """Manejador para descargar plantilla"""
        anio = self.spin_anio.get()
        mes = self.combo_mes.get()
        
        filename = f"Plantilla_Nomina_{anio}_{mes}.xlsx"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")],
            initialfile=filename,
            title="Guardar Plantilla de Nómina"
        )
        
        if not filepath: return

        # Ejecutar en hilo para no congelar
        self._set_loading(True)
        threading.Thread(target=self._run_template_generation, args=(filepath, int(anio), int(mes))).start()

    def _run_template_generation(self, filepath, anio, mes):
        success, msg = self.service.generate_payroll_template(filepath, anio, mes)
        self.after(0, lambda: self._on_process_finished(success, msg))

    def upload_payroll(self):
        """Manejador para subir Excel"""
        filepath = filedialog.askopenfilename(
            filetypes=[("Excel Files", "*.xlsx")],
            title="Seleccionar Plantilla Completada"
        )
        
        if not filepath: return
        
        confirm = messagebox.askyesno("Confirmar Carga", 
                                      "¿Está seguro de cargar esta planilla?\n\n"
                                      "Si ya existen datos para este mes/año y contrato,\n"
                                      "se actualizarán los valores.")
        if not confirm: return

        self._set_loading(True)
        threading.Thread(target=self._run_upload, args=(filepath,)).start()

    def _run_upload(self, filepath):
        success, msg = self.service.process_payroll_import(filepath)
        self.after(0, lambda: self._on_process_finished(success, msg, refresh=True))

    def _on_process_finished(self, success, msg, refresh=False):
        self._set_loading(False)
        if success:
            messagebox.showinfo("Éxito", msg)
            if refresh:
                self.load_data()
        else:
            messagebox.showerror("Error", msg)

    def _set_loading(self, loading):
        if loading:
            self.progress.pack(side=LEFT, padx=10)
            self.progress.start(10)
        else:
            self.progress.stop()
            self.progress.pack_forget()
# ---------------- LÓGICA DE ELIMINACIÓN MASIVA ----------------
    def delete_current_period(self):
        anio = self.spin_anio.get()
        mes = self.combo_mes.get()
        
        confirm = messagebox.askyesno(
            "Eliminar Periodo Completo",
            f"⚠ ADVERTENCIA CRÍTICA ⚠\n\n"
            f"Está a punto de eliminar TODOS los registros de nómina del mes {mes}/{anio}.\n"
            f"Esta acción no se puede deshacer.\n\n"
            f"¿Está absolutamente seguro de proceder?",
        )
        
        if confirm:
            success, msg = self.dao.delete_period(anio, mes)
            if success:
                messagebox.showinfo("Periodo Eliminado", msg)
                self.load_data() # Recargar tabla (quedará vacía)
            else:
                messagebox.showerror("Error", msg)

    # ---------------- LÓGICA DE EDICIÓN INDIVIDUAL ----------------
    def on_double_click(self, event):
        """Abre modal para editar una fila"""
        item = self.tree.selection()
        if not item: return
        
        # Obtener valores de la fila seleccionada
        values = self.tree.item(item, "values")
        # values[0] es el ID oculto
        # values[1] es el Nombre
        # values[3] es Salario Base (texto formateado "L. 1,000.00")
        
        id_nomina = values[0]
        nombre_emp = values[1]
        
        self._open_edit_modal(id_nomina, nombre_emp)

    def _open_edit_modal(self, id_nomina, nombre_emp):
        """Crea una ventana emergente (Toplevel) para editar montos"""
        
        # 1. Recuperar datos CRUDOS (sin formato moneda) de la BD para editar bien
        #    Podríamos parsear el texto de la tabla, pero es mejor pedir el dato limpio al DAO
        #    (Ojo: Usamos un pequeño truco: reutilizamos la query general o hacemos una especifica.
        #     Para rapidez, parsearemos el texto quitando "L." y ",").
        
        # Helper para limpiar moneda
        def clean_money(val_str):
            return val_str.replace("L.", "").replace(",", "").strip()

        # Obtenemos los valores visuales actuales
        item = self.tree.selection()[0]
        vals = self.tree.item(item, "values")
        
        current_base = clean_money(vals[3])
        current_bonos = clean_money(vals[4])
        current_beneficios = clean_money(vals[5])
        current_deducciones = clean_money(vals[6])
        current_obs = vals[8]

        # 2. Crear Ventana Modal
        top = ttk.Toplevel(title=f"Editar: {nombre_emp}")
        top.geometry("400x450")
        top.resizable(False, False)
        
        # UI del Modal
        ttk.Label(top, text="Editar Montos Mensuales", font=("Helvetica", 12, "bold")).pack(pady=10)
        
        frm = ttk.Frame(top, padding=10)
        frm.pack(fill=BOTH, expand=True)
        
        # Inputs
        ttk.Label(frm, text="Salario Base:").pack(anchor=W)
        entry_base = ttk.Entry(frm)
        entry_base.insert(0, current_base)
        entry_base.pack(fill=X, pady=(0, 10))

        ttk.Label(frm, text="Bonificaciones:").pack(anchor=W)
        entry_bonos = ttk.Entry(frm)
        entry_bonos.insert(0, current_bonos)
        entry_bonos.pack(fill=X, pady=(0, 10))

        ttk.Label(frm, text="Beneficios Laborales:").pack(anchor=W)
        entry_ben = ttk.Entry(frm)
        entry_ben.insert(0, current_beneficios)
        entry_ben.pack(fill=X, pady=(0, 10))
        
        ttk.Label(frm, text="Deducciones:").pack(anchor=W)
        entry_ded = ttk.Entry(frm)
        entry_ded.insert(0, current_deducciones)
        entry_ded.pack(fill=X, pady=(0, 10))

        ttk.Label(frm, text="Observaciones:").pack(anchor=W)
        entry_obs = ttk.Entry(frm)
        entry_obs.insert(0, current_obs)
        entry_obs.pack(fill=X, pady=(0, 20))

        # Botón Guardar
        def save_changes():
            try:
                # Validar números
                n_base = float(entry_base.get())
                n_bonos = float(entry_bonos.get())
                n_ben = float(entry_ben.get())
                n_ded = float(entry_ded.get())
                s_obs = entry_obs.get()
                
                # Llamar al DAO
                success, msg = self.dao.update_payroll_record(id_nomina, n_base, n_bonos, n_ben, n_ded, s_obs)
                
                if success:
                    messagebox.showinfo("Éxito", "Registro actualizado correctamente.", parent=top)
                    top.destroy()
                    self.load_data() # Refrescar tabla principal
                else:
                    messagebox.showerror("Error", msg, parent=top)
                    
            except ValueError:
                messagebox.showerror("Error", "Por favor ingrese valores numéricos válidos.", parent=top)

        ttk.Button(frm, text="💾 Guardar Cambios", bootstyle="success", command=save_changes).pack(fill=X, pady=10)