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

        # Loading
        self.progress = ttk.Progressbar(row_actions, mode='indeterminate', bootstyle="success-striped")
        # (Se empaca solo cuando se usa)

        # --- TABLA DE DATOS (TREEVIEW) ---
        # Columnas para ver el resumen
        cols = ("empleado", "puesto", "base", "bonos", "beneficios", "deducciones", "total", "obs")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=15)
        
        # Configuración de Cabeceras
        self.tree.heading("empleado", text="Colaborador")
        self.tree.heading("puesto", text="Puesto")
        self.tree.heading("base", text="Salario Base")
        self.tree.heading("bonos", text="Bonificaciones")
        self.tree.heading("beneficios", text="Beneficios")
        self.tree.heading("deducciones", text="Deducciones")
        self.tree.heading("total", text="TOTAL PAGADO")
        self.tree.heading("obs", text="Observaciones")

        # Configuración de Columnas
        self.tree.column("empleado", width=250)
        self.tree.column("puesto", width=150)
        self.tree.column("base", width=100, anchor="e")
        self.tree.column("bonos", width=100, anchor="e")
        self.tree.column("beneficios", width=100, anchor="e")
        self.tree.column("deducciones", width=100, anchor="e")
        self.tree.column("total", width=120, anchor="e")
        self.tree.column("obs", width=200)

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
            
            # Formateo de moneda
            salario = f"L. {row[3]:,.2f}"
            bonos = f"L. {row[4]:,.2f}"
            beneficios = f"L. {row[5]:,.2f}"
            deducciones = f"L. {row[6]:,.2f}"
            total = f"L. {row[7]:,.2f}"
            
            total_acumulado += row[7] # Sumar el raw value del total
            
            values = (row[1], row[2], salario, bonos, beneficios, deducciones, total, row[8])
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