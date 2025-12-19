import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from views.components.employee_selector import EmployeeSelector
from models.attendance_dao import AttendanceDAO 
from models.kardex_dao import KardexDAO
from logics.vacation_service import VacationService
from logics.report_service import ReportService

class VacationBalanceView(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.pack(fill=BOTH, expand=True)

        self.report_service = ReportService()         
        self.att_dao = AttendanceDAO()
        self.kardex_dao = KardexDAO()
        
        self.current_emp_id = None
        self.contracts_map = []
        
        self._setup_ui()

    def _setup_ui(self):
        # Header
        header = ttk.Frame(self, padding=10)
        header.pack(fill=X)
        ttk.Label(header, text="Kardex de Vacaciones", font=("Segoe UI", 18, "bold"), justify='center').pack(side=LEFT)
        
        # --- FILTROS ---
        filter_frame = ttk.Labelframe(self, text="Filtros de Consulta", padding=10, bootstyle="info")
        filter_frame.pack(fill=X, padx=10, pady=5)
        
        # === FILA 1: DATOS DEL EMPLEADO Y CONTRATO ===
        row1 = ttk.Frame(filter_frame)
        row1.pack(fill=X, pady=(0, 5)) # Un poco de espacio abajo para separar de la fila 2

        # 1. Selector Empleado
        f_emp = ttk.Frame(row1)
        f_emp.pack(side=LEFT, padx=5)
        ttk.Button(f_emp, text="🔍 Empleado", command=self.open_search, bootstyle="info-outline").pack(side=LEFT)
        self.lbl_emp = ttk.Label(f_emp, text="Seleccione un colaborador...", font=("Segoe UI", 10, "bold"))
        self.lbl_emp.pack(side=LEFT, padx=10)

        # 2. Selector Contrato
        f_con = ttk.Frame(row1)
        f_con.pack(side=LEFT, padx=15, fill=X, expand=True)
        ttk.Label(f_con, text="Contrato:").pack(side=LEFT)
        self.cb_contrato = ttk.Combobox(f_con, state="readonly")
        self.cb_contrato.pack(side=LEFT, padx=5, fill=X, expand=True) # Que ocupe el espacio restante
        self.cb_contrato.bind("<<ComboboxSelected>>", self.run_report)

        # === FILA 2: FECHAS Y BOTÓN DE ACCIÓN ===
        row2 = ttk.Frame(filter_frame)
        row2.pack(fill=X, pady=5)

        # 3. Fechas (Lado Izquierdo)
        f_date = ttk.Frame(row2)
        f_date.pack(side=LEFT, padx=5)
        
        ttk.Label(f_date, text="Desde:").pack(side=LEFT)
        self.date_ini = ttk.DateEntry(f_date, dateformat='%Y-%m-%d', width=12)
        self.date_ini.pack(side=LEFT, padx=5)
        self.date_ini.entry.delete(0, END) 

        ttk.Label(f_date, text="Hasta:").pack(side=LEFT, padx=(15, 0)) # Margen extra a la izquierda
        self.date_fin = ttk.DateEntry(f_date, dateformat='%Y-%m-%d', width=12)
        self.date_fin.pack(side=LEFT, padx=5)
        self.date_fin.entry.delete(0, END)

        # 4. Botón Filtrar (Lado Derecho - Destacado)
        ttk.Button(row2, text="Filtrar Reporte", command=self.run_report, bootstyle="secondary").pack(side=RIGHT, padx=10)


        # --- TABLA DE RESULTADOS ---
        result_frame = ttk.Frame(self, padding=10)
        result_frame.pack(fill=BOTH, expand=True)

        cols = ("fecha", "tipo", "detalle", "debe", "haber", "saldo")
        self.tree = ttk.Treeview(result_frame, columns=cols, show="headings")
        
        # Encabezados
        self.tree.heading("fecha", text="Fecha")
        self.tree.column("fecha", width=70, stretch=False)
        
        self.tree.heading("tipo", text="Movimiento")
        self.tree.column("tipo", width=200, stretch=False)
        
        self.tree.heading("detalle", text="Detalle / Observación")
        self.tree.column("detalle", width=300, anchor=W)
        
        self.tree.heading("debe", text="Devengado") 
        self.tree.column("debe", width=70, anchor=E)
        
        self.tree.heading("haber", text="Ganado") 
        self.tree.column("haber", width=70, anchor=E)
        
        self.tree.heading("saldo", text="Saldo")
        self.tree.column("saldo", width=70, anchor=E)

        self.tree.pack(fill=BOTH, expand=True, side=LEFT)
        
        sb = ttk.Scrollbar(result_frame, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=sb.set)
        sb.pack(side=RIGHT, fill=Y)

        # Footer
        footer = ttk.Frame(self, padding=5)
        footer.pack(fill=X)
        ttk.Label(footer, text="* Devengado (Debe) = Días tomados | Ganado (Haber) = Días acumulados", bootstyle="secondary").pack(side=LEFT)

    # --- LÓGICA ---
    def open_search(self):
        EmployeeSelector(self, self.on_employee_selected)

    def on_employee_selected(self, emp_id, emp_code, emp_name):
        self.current_emp_id = emp_id
        self.lbl_emp.config(text=f"{emp_name}", bootstyle="primary")
        
        self.contracts_map = self.att_dao.get_active_contracts_by_employee(emp_id)
        vals = [c[1] for c in self.contracts_map]
        self.cb_contrato['values'] = vals
        
        if vals:
            self.cb_contrato.current(0)
            self.run_report()
        else:
            self.cb_contrato.set('')
            self.clear_table()

    def run_report(self, event=None):
        txt_contrato = self.cb_contrato.get()
        if not txt_contrato: return

        id_con = None
        for cid, cname in self.contracts_map:
            if cname == txt_contrato:
                id_con = cid
                break
        if id_con is None: return

        f_ini = self.date_ini.entry.get()
        if not f_ini: f_ini = None
        f_fin = self.date_fin.entry.get()
        if not f_fin: f_fin = None

        self.clear_table()



        self.clear_table()
        self.master.config(cursor="watch")
        self.master.update()

        try:
            # === LLAMADA AL SERVICIO (Una sola línea limpia) ===
            data = self.report_service.get_kardex_report_data(id_con, f_ini, f_fin)
            
            # === RENDERIZADO ===
            
            # A. Saldo Anterior
            if data["saldo_anterior"] != 0 or f_ini:
                 self.tree.insert("", END, values=(
                    f_ini if f_ini else "---",
                    "SALDO ANTERIOR",
                    "Arrastre de periodo previo",
                    "", "", 
                    f"{data['saldo_anterior']:.2f}"
                ), tags=('bold',))
            
            # B. Filas
            for row in data["movimientos"]:
                tag = 'projection' if row['es_proyeccion'] else ''
                
                debe_str = f"{row['debe']:.2f}" if row['debe'] > 0 else ""
                haber_str = f"{row['haber']:.2f}" if row['haber'] > 0 else ""
                
                self.tree.insert("", END, values=(
                    row['fecha'],
                    row['tipo'],
                    row['detalle'],
                    debe_str,
                    haber_str,
                    f"{row['saldo']:.2f}"
                ), tags=(tag,))

            # C. Separador Proyecciones (Opcional, si detectamos cambio de tipo)
            # (Simplificado aquí, pero podrías insertar una fila vacía antes de la primera proyección)

            # D. Totales
            tot = data["totales"]
            self.tree.insert("", END, values=(
                "", "TOTALES", "", 
                f"{tot['debe']:.2f}", f"{tot['haber']:.2f}", f"{tot['saldo_final']:.2f}"
            ), tags=('total',))

        except Exception as e:
            print(f"Error UI: {e}")
            Messagebox.show_error(f"Error generando reporte: {e}")
        finally:
            self.master.config(cursor="")
    def clear_table(self):
        for i in self.tree.get_children(): self.tree.delete(i)