import sqlite3
import pandas as pd
from pathlib import Path



def export_sqlite_to_excel(db_path: str, output_excel: str):
    """
    Exporta todas las tablas de una base de datos SQLite
    a un archivo Excel, una tabla por hoja.
    """

    db_path = Path(db_path)

    if not db_path.exists():
        raise FileNotFoundError(f"No se encontró la base de datos: {db_path}")

    # Conexión a SQLite
    conn = sqlite3.connect(db_path)

    try:
        # Obtener lista de tablas
        query_tables = """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        AND name NOT LIKE 'sqlite_%';
        """

        tables = pd.read_sql(query_tables, conn)

        if tables.empty:
            raise ValueError("La base de datos no contiene tablas.")

        # Crear Excel
        with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
            for table_name in tables["name"]:
                df = pd.read_sql(f"SELECT * FROM {table_name}", conn)

                # Excel limita el nombre de hojas a 31 caracteres
                sheet_name = table_name[:31]

                df.to_excel(
                    writer,
                    sheet_name=sheet_name,
                    index=False
                )

        print(f"Archivo Excel generado correctamente: {output_excel}")

    finally:
        conn.close()


if __name__ == "__main__":
    # === CONFIGURACIÓN ===
    SQLITE_DB_PATH = "rrhh.db"
    OUTPUT_EXCEL_PATH = f"base_rrhh.xlsx"

    export_sqlite_to_excel(SQLITE_DB_PATH, OUTPUT_EXCEL_PATH)
