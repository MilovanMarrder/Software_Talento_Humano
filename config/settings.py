import os
from pathlib import Path

# Definimos la raíz del proyecto (basado en la ubicación de este archivo)
# Subimos un nivel desde 'config' para llegar a la raíz
BASE_DIR = Path(__file__).resolve().parent.parent

# Ruta absoluta a los assets
ASSETS_DIR = BASE_DIR / "assets"

# Nombre de base de datos
DB_NAME = "rrhh.db"

# ruta de base de datos
DB_PATH = BASE_DIR / DB_NAME

# Ruta centralizada del Icono
ICON_PATH = ASSETS_DIR / "blowfish_icon.ico"

# Constantes de la App
APP_TITLE = "Sistema de Talento Humano HMEP"
APP_SIZE = "1250x620" # Un poco más grande para comodidad
