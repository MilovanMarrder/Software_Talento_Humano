import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from tkinter import filedialog 
from views.components.employee_selector import EmployeeSelector
from models.attendance_dao import AttendanceDAO 
from models.kardex_dao import KardexDAO
from logics.report_service import ReportService
from datetime import date


class VacationBalanceView(ttk.Frame):
    def __init__(self, parent, controller=None):
        super().__init__(parent)
        self.controller = controller
        self.pack(fill=BOTH, expand=True)

        self.report_service = ReportService()         
        self.att_dao = AttendanceDAO()
        self.kardex_dao = KardexDAO()
        
        self.current_emp_id = None
        self.contracts_map = []

        self.current_emp_name = "Empleado" 
        
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
        row1.pack(fill=X, pady=(0, 5)) 

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
        self.cb_contrato.pack(side=LEFT, padx=5, fill=X, expand=True) 
        self.cb_contrato.bind("<<ComboboxSelected>>", self.run_report)

        # === FILA 2: FECHAS Y BOTONES DE ACCIÓN ===
        row2 = ttk.Frame(filter_frame)
        row2.pack(fill=X, pady=5)

        # 3. Fechas (Lado Izquierdo)
        f_date = ttk.Frame(row2)
        f_date.pack(side=LEFT, padx=5)
        
        ttk.Label(f_date, text="Desde:").pack(side=LEFT)
        self.date_ini = ttk.DateEntry(f_date, dateformat='%Y-%m-%d', width=12)
        self.date_ini.pack(side=LEFT, padx=5)
        self.date_ini.entry.delete(0, END) 

        ttk.Label(f_date, text="Hasta:").pack(side=LEFT, padx=(15, 0)) 
        self.date_fin = ttk.DateEntry(f_date, dateformat='%Y-%m-%d', width=12)
        self.date_fin.pack(side=LEFT, padx=5)
        self.date_fin.entry.delete(0, END)

        # 4. Botones (Lado Derecho)
        
        # [NUEVO] Botón Exportar Equipo
        ttk.Button(row2, text="Descargar Equipo", command=self.export_team_excel, bootstyle="info-outline").pack(side=RIGHT, padx=5)

        # [MODIFICADO] Cambiar texto para claridad
        ttk.Button(row2, text="Descargar Individual", command=self.export_excel, bootstyle="success-outline").pack(side=RIGHT, padx=5)
        # Botón Filtrar
        ttk.Button(row2, text="Filtrar Pantalla", command=self.run_report, bootstyle="secondary").pack(side=RIGHT, padx=5)
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
        self.current_emp_name = emp_name
        
        self.contracts_map = self.att_dao.get_active_contracts_by_employee(emp_id)
        vals = [c[1] for c in self.contracts_map]
        self.cb_contrato['values'] = vals
        
        if vals:
            self.cb_contrato.current(0)
            self.run_report()
        else:
            self.cb_contrato.set('')
            self.clear_table()

    def _get_filter_data(self):
        """Helper para extraer datos del formulario"""
        txt_contrato = self.cb_contrato.get()
        if not txt_contrato: return None, None, None

        id_con = None
        for cid, cname in self.contracts_map:
            if cname == txt_contrato:
                id_con = cid
                break
        
        if id_con is None: return None, None, None

        f_ini = self.date_ini.entry.get()
        if not f_ini: f_ini = None
        f_fin = self.date_fin.entry.get()
        if not f_fin: f_fin = None
        
        return id_con, f_ini, f_fin

    def run_report(self, event=None):
        id_con, f_ini, f_fin = self._get_filter_data()
        if not id_con: return

        self.clear_table()
        self.master.config(cursor="watch")
        self.master.update()

        try:
            # === LLAMADA AL SERVICIO ===
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

            # D. Totales
            tot = data["totales"]
            self.tree.insert("", END, values=(
                "", "TOTALES", "", 
                f"{tot['debe']:.2f}", f"{tot['haber']:.2f}", f"{tot['saldo_final']:.2f}"
            ), tags=('total',))

            # Estilos visuales del Treeview
            self.tree.tag_configure('bold', font=('Segoe UI', 9, 'bold'))
            self.tree.tag_configure('total', font=('Segoe UI', 9, 'bold'), background='#e1e1e1')
            self.tree.tag_configure('projection', foreground='#555555')

        except Exception as e:
            print(f"Error UI: {e}")
            Messagebox.show_error(f"Error generando reporte: {e}")
        finally:
            self.master.config(cursor="")

    def export_excel(self):
        """Manejador para exportar reporte INDIVIDUAL con nombre detallado"""
        # 1. Validar selección
        id_con, f_ini, f_fin = self._get_filter_data()
        
        if not id_con:
            Messagebox.show_warning("Seleccione un colaborador y contrato primero.")
            return

        # 2. Construir nombre del empleado
        # Extraemos el nombre limpio del label (Ej: "100475 - JUAN PEREZ" -> "JUAN PEREZ")
        raw_name = self.lbl_emp.cget("text")
        if "-" in raw_name:
            employee_name = raw_name.split("-", 1)[1].strip()
        else:
            employee_name = raw_name

        safe_name = self._clean_filename(employee_name)

        # 3. Construir fechas para el nombre del archivo
        # Si no hay fecha fin, asumimos que es al corte de "HOY"
        fecha_corte = f_fin if f_fin else date.today().strftime('%Y-%m-%d')

        # Formato: "Vacaciones JUAN PEREZ (hasta 2025-10-20).xlsx"
        filename = f"Vacaciones {safe_name} (hasta {fecha_corte}).xlsx"

        # 4. Diálogo de Guardado
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")],
            initialfile=filename,
            title="Guardar Kardex Individual"
        )

        if not filepath: return

        self.master.config(cursor="watch")
        try:
            # IMPORTANTE: Pasamos 'employee_name=safe_name' para que la HOJA de Excel se llame así
            success, msg = self.report_service.export_kardex_excel(
                id_con, f_ini, f_fin, filepath, employee_name=safe_name
            )
            if success:
                Messagebox.show_info(msg, "Exportación Exitosa")
            else:
                Messagebox.show_error(msg, "Error")
        except Exception as e:
            Messagebox.show_error(f"Error inesperado: {e}", "Error")
        finally:
            self.master.config(cursor="")

    def clear_table(self):
        for i in self.tree.get_children(): self.tree.delete(i)

    def export_team_excel(self):
        """Manejador para exportar reporte de EQUIPO con nombre de Departamento"""
        id_con, f_ini, f_fin = self._get_filter_data()
        
        if not id_con:
            Messagebox.show_warning("Seleccione el contrato del JEFE del equipo a descargar.")
            return

        # 1. Instanciar ContractDAO para obtener el nombre del departamento
        #    (Como ya importamos ContractDAO indirectamente o podemos usar self.att_dao.db si fuera necesario,
        #     pero lo ideal es instanciarlo limpio)
        from models.contract_dao import ContractDAO
        dao = ContractDAO()
        
        # Obtener nombre del departamento del jefe seleccionado
        dept_name = dao.get_department_name_by_contract(id_con)
        safe_dept = self._clean_filename(dept_name)

        # 2. Definir fecha de corte para el nombre
        fecha_corte = f_fin if f_fin else date.today().strftime('%Y-%m-%d')

        # 3. Formato Solicitado: "Vacaciones - {Departamento} hasta el {Fecha}.xlsx"
        filename = f"Vacaciones {safe_dept} hasta {fecha_corte}.xlsx"

        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")],
            initialfile=filename,
            title="Guardar Reporte de Equipo"
        )

        if not filepath: return

        self.master.config(cursor="watch")
        self.master.update()
        
        try:
            success, msg = self.report_service.export_team_kardex_excel(
                id_con, f_ini, f_fin, filepath
            )
            
            if success:
                Messagebox.show_info(msg, "Exportación Exitosa")
            else:
                Messagebox.show_error(msg, "Error")
                
        except Exception as e:
            Messagebox.show_error(f"Error crítico: {e}", "Error")
        finally:
            self.master.config(cursor="")

    def _clean_filename(self, text):
        """Helper para limpiar caracteres prohibidos en nombres de archivo"""
        if not text: return "Archivo"
        # Caracteres prohibidos en Windows/Linux
        invalid = '<>:"/\|?*'
        for char in invalid:
            text = text.replace(char, '')
        return text.strip()