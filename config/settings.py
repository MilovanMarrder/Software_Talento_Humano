import os
import sys
from pathlib import Path

# --- GESTIÓN DE RUTAS HÍBRIDA (DEV vs EXE) ---
if getattr(sys, 'frozen', False):
    # Si estamos ejecutando como .exe (PyInstaller)
    # BASE_DIR será la carpeta donde está el .exe (no la temporal interna)
    BASE_DIR = Path(sys.executable).parent
else:
    # Si estamos en desarrollo (Python normal)
    BASE_DIR = Path(__file__).resolve().parent.parent

# --- RUTAS DE RECURSOS ---
ASSETS_DIR = BASE_DIR / "assets"

# Nombre de base de datos
DB_NAME = "rrhh.db"

# Ruta de base de datos (Siempre al lado del ejecutable)
DB_PATH = BASE_DIR / DB_NAME

# Ruta del Icono
ICON_PATH = ASSETS_DIR / "blowfish_icon.ico"

# Constantes de la App
APP_TITLE = "Sistema de Talento Humano HMEP"
APP_SIZE = "1250x620"

print("="*30)
print(f"Ruta Base detectada: {BASE_DIR}")
print(f"Buscando DB en:      {DB_PATH}")
print(f"¿Existe el archivo?: {DB_PATH.exists()}")
print("="*30)