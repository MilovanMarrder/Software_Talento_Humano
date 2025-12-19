import os

# --- CONFIGURACIÓN ---
# --- ARCHIVOS QUE SIEMPRE DEBEN IR ---
CORE_FILES = [
    "main.py",
    "config/settings.py",
    "config/db_connection.py",  # Vital para pandas
    "migrations_perc.py",       # Vital: Contiene el esquema nuevo (dni_perc, grupos, etc.)
    "migrations_puestos.py",
    # Vital: Contiene el esquema de puestos (departamento, jefe)
]

# --- FOCO ACTIVO (Para generar el Reporte PERC) ---
ACTIVE_FOCUS = [
    # 1. Modelos de Datos (Para entender de dónde sacar la info)
    "models/contract_dao.py", 
    "models/catalogs_dao.py",
    "models/attendace_dao.py",
    "models/employee_dao.py",
    "models/kardex_dao.py", 

    # 2. Vistas (Donde pondremos el botón y el selector de fecha)
    "views/modules/reports_view.py",
    "views/modules/attendace_view.py",
    "views/modules/configuration_view.py",
    "views/modules/contract_view.py",
    "views/modules/employee_view.py",
    "views/modules/vacation_balance_view.py",
    
    # 3. Lógica (Aquí crearemos el nuevo servicio)
    "logics/perc_export_service.py",
    "logics/report_service.py",
    "logics/time_calculator.py",
    "logics/vacation_service.py"
]
def read_file(filepath):
    """Lee un archivo y retorna su contenido formateado para LLM"""
    if not os.path.exists(filepath):
        return f"[MISSING FILE: {filepath}]\n"
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Formato Markdown para ahorrar tokens vs LaTeX
    return f"\n## Archivo: {filepath}\n```python\n{content}\n```\n"

def get_project_structure(startpath='.'):
    """Genera el árbol de directorios ignorando carpetas basura"""
    structure = "## Estructura del Proyecto\n```\n"
    exclude = {'.git', '__pycache__', '.vscode', 'venv', 'build', 'dist'}
    
    for root, dirs, files in os.walk(startpath):
        dirs[:] = [d for d in dirs if d not in exclude]
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * (level)
        structure += f"{indent}{os.path.basename(root)}/\n"
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            if f.endswith('.py') or f.endswith('.sql'):
                structure += f"{subindent}{f}\n"
    structure += "```\n"
    return structure

def main():
    output = "ESTE ES EL CONTEXTO ACTUAL DEL PROYECTO RRHH HMEP.\n"
    output += "Stack: Python 3.13 + Tkinter (ttkbootstrap) + SQLite.\n"
    output += "Patrón: MVC Modular + Lógica de Negocio separada.\n\n"
    
    # 1. Estructura
    output += get_project_structure()
    
    # 2. Core Files
    output += "\n# --- ARCHIVOS CORE (Estructura/Config) ---\n"
    for f in CORE_FILES:
        output += read_file(f)

    # 3. Active Focus
    output += "\n# --- ARCHIVOS DE TRABAJO ACTUAL (Foco) ---\n"
    for f in ACTIVE_FOCUS:
        output += read_file(f)
        
    # Guardar
    with open("prompt_context.txt", "w", encoding="utf-8") as f:
        f.write(output)
    
    print(f"✅ Contexto generado en 'prompt_context.txt'.")
    print(f"   Archivos enfocados: {len(ACTIVE_FOCUS)}")

if __name__ == "__main__":
    main()