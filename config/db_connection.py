import sqlite3
import os
from pathlib import Path
from config import settings 

class DatabaseConnection:
    """
    Manejador de conexión a la base de datos SQLite.
    Implementa el patrón Context Manager (with statement) si se desea,
    o métodos directos.
    """
    
    def __init__(self, db_name=settings.DB_NAME):
        # Obtiene la ruta absoluta del directorio raíz del proyecto
        # Asume que este archivo está en /config/ y subimos un nivel
        self.root_dir = Path(__file__).parent.parent
        self.db_path = self.root_dir / db_name

    def get_connection(self):
        """Retorna una conexión activa con FKs habilitadas."""
        try:
            conn = sqlite3.connect(self.db_path)
            # CRÍTICO: SQLite por defecto tiene las FK desactivadas. 
            # Esto evita que insertes inasistencias sin contrato.
            conn.execute("PRAGMA foreign_keys = ON") 
            return conn
        except sqlite3.Error as e:
            print(f"Error conectando a la BD en {self.db_path}: {e}")
            return None

    def test_connection(self):
        """Método helper para probar si la DB existe y responde."""
        conn = self.get_connection()
        if conn:
            print(f"✅ Conexión exitosa a: {self.db_path}")
            conn.close()
            return True
        else:
            print("❌ Fallo en la conexión.")
            return False