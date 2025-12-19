import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from views import styles
from views.modules.employees_view import EmployeesView
from views.modules.contracts_view import ContractsView
from views.modules.configuration_view import ConfigurationView
from views.modules.attendance_view import AttendanceView
from views.modules.vacation_balance_view import VacationBalanceView
from views.modules.reports_view import ReportsView

class MainWindow(ttk.Frame):
    """
    Frame principal que contiene:
    1. Sidebar (Menú lateral)
    2. Content Area (Donde se cargan las vistas de módulos)
    """
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller # Referencia al orquestador (futuro)
        self.pack(fill=BOTH, expand=True)
        
        # Estructura: 2 Columnas
        # Columna 0: Menú | Columna 1: Contenido
        self._setup_layout()
        
    def _setup_layout(self):
        # --- 1. Sidebar (Izquierda) ---
        self.sidebar_frame = ttk.Frame(self, bootstyle="secondary", width=styles.SIDEBAR_WIDTH)
        self.sidebar_frame.pack(side=LEFT, fill=Y)
        self.sidebar_frame.pack_propagate(False) # Evita que se encoja si está vacío

        self._create_sidebar_menu()

        # --- 2. Content Area (Derecha) ---
        self.content_frame = ttk.Frame(self, padding=styles.PAD_DEFAULT)
        self.content_frame.pack(side=RIGHT, fill=BOTH, expand=True)

        # Mensaje de bienvenida temporal
        lbl_welcome = ttk.Label(
            self.content_frame, 
            text="Sistema de Información para Talento Humano\nHospital María Especialidades Pediátricas", 
            font=styles.FONT_H1,
            bootstyle="primary",
            justify='center'
        )
        lbl_welcome.pack(pady=50)

    def _create_sidebar_menu(self):
        """Crea los botones de navegación"""
        
        # Título del Menú
        lbl_brand = ttk.Label(
            self.sidebar_frame, 
            text="Hospital María\nEspecialidades Pediátricas", 
            font=("Segoe UI", 14, "bold"),
            bootstyle="inverse-secondary",
            justify='center'
        )
        lbl_brand.pack(pady=20)

        # Botones de Navegación 
        menu_items = [
            ("Empleados", "primary"),
            ("Contratos", "primary"),
            ("Inasistencias", "primary"),
            ("Saldo Vacaciones", "primary"),
            ("Reportes", "primary"),
            ("Configuración", "secondary") 
        ]

        for text, style in menu_items:
            btn = ttk.Button(
                self.sidebar_frame, 
                text=text, 
                bootstyle=style,
                command=lambda t=text: self.navegar_a(t) # Callback temporal
            )
            btn.pack(fill=X, pady=5, padx=10)
            
        # Info versión al pie
        lbl_version = ttk.Label(
            self.sidebar_frame,
            text="v1.0.0\ndev. M. Marrder",
            font=styles.FONT_SMALL,
            bootstyle="inverse-secondary",
            justify='center'
        )
        lbl_version.pack(side=BOTTOM, pady=10)

    def navegar_a(self, modulo):
        """Gestor de navegación"""
        print(f"Navegando a: {modulo}")
        
        # 1. Limpiar el contenido actual (Eliminar widgets previos)
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # 2. Cargar la vista solicitada
        if modulo == "Empleados":
            EmployeesView(self.content_frame) # Instancia y se auto-empaqueta
        # elif modulo == "Inicio":
        #      ttk.Label(self.content_frame, text="Bienvenido al sistema de Gestión\ndel Talento Humano HMEP", font=("Segoe UI", 24), justify='center').pack(pady=50)
        elif modulo == "Contratos":
            ContractsView(self.content_frame) # Instancia y se auto-empaqueta
        elif modulo == "Configuración":
            ConfigurationView(self.content_frame)
        elif modulo == "Inasistencias":
            AttendanceView(self.content_frame)
        elif modulo == "Saldo Vacaciones":
            VacationBalanceView(self.content_frame)
        elif modulo == "Reportes":
            ReportsView(self.content_frame, self.controller)
        else:
            # Placeholder para módulos no hechos aún
            ttk.Label(self.content_frame, text=f"Módulo {modulo} en construcción...", bootstyle="warning").pack(pady=50)