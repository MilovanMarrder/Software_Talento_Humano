import os

# --- CONFIGURACIÓN ---
# --- ARCHIVOS QUE SIEMPRE DEBEN IR ---
CORE_FILES = [
    "main.py",                   # CRÍTICO: Aquí haremos el cambio de arquitectura (Launcher)
    "config/settings.py",
    # "config/db_connection.py",
    # "archivos de construccion/setup_full_db.py"
]


# --- FOCO ACTIVO (Para generar el Contexto) ---
ACTIVE_FOCUS = [
    #1 logics
    # "logics/db_connection.py",
    # "logics/payroll_import_service.py",
    # "logics/perc_export_service.py",
    # "logics/report_service.py",
    # "logics/time_balance_service.py",
    # "logics/time_calculator.py",
    # "logics/vacation_service.py",
    # 1. Donde vive la exportación actual (para corregirla)
    # "models/attendance_dao.py",
    # "models/catalogs_dao.py",
    "models/contract_dao.py",
    "models/employee_dao.py",
    # "models/kardex_dao.py",
    # "models/payroll_dao.py",
    "views/components/employee_selector.py",
    "views/components/contract_selector.py",
    # "views/modules/attendance_view.py",
    # "views/modules/configuration_view.py",
    "views/modules/contracts_view.py",
    "views/modules/employees_view.py",
    # "views/modules/payroll_view.py",
    # "views/modules/reports_view.py",
    # "views/modules/vacation_balance_view.py",
    # "views/main_window.py",
    "views/styles.py",

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