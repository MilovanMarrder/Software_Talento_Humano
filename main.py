import ttkbootstrap as ttk
from config.db_connection import DatabaseConnection
from views.main_window import MainWindow
from config import settings 

class App(ttk.Window):
    def __init__(self):
        # Configuración inicial de la ventana
        # Themes claros recomendados: 'flatly', 'litera', 'yeti'
        # Themes oscuros recomendados: 'darkly', 'superhero'
        super().__init__(themename="flatly")
        
        
        # Usamos las variables centralizadas están en settings dentro de config
        self.title(settings.APP_TITLE)
        self.geometry(settings.APP_SIZE)
        
        # Configuración del Icono Principal
        if settings.ICON_PATH.exists():
            self.iconbitmap(settings.ICON_PATH)
        else:
            print(f"⚠ No se encontró el icono en: {settings.ICON_PATH}")


        # 1. Validar Base de Datos al inicio
        self.db = DatabaseConnection()
        if not self.db.test_connection():
            print("⚠ ADVERTENCIA: No se pudo conectar a la base de datos.")
            # Aquí podrías lanzar un popup de error antes de cerrar
        
        # 2. Inicializar Vista Principal
        # Pasamos 'self' como controller temporalmente
        self.main_window = MainWindow(self, controller=self)
        
    def run(self):
        self.mainloop()

if __name__ == "__main__":
    app = App()
    app.run()