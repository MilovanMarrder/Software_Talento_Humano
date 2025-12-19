import sqlite3

def migrate_puestos_structure():
    conn = sqlite3.connect('rrhh.db')
    cursor = conn.cursor()
    print("--- MIGRANDO ESTRUCTURA DE PUESTOS ---")
    try:
        cursor.execute("PRAGMA table_info(cat_puestos)")
        cols = [c[1] for c in cursor.fetchall()]

        # 1. Booleano: ¿Este puesto tiene personal a cargo? (Es jefe)
        if 'tiene_personal_cargo' not in cols:
            print("-> Agregando tiene_personal_cargo...")
            cursor.execute("ALTER TABLE cat_puestos ADD COLUMN tiene_personal_cargo INTEGER DEFAULT 0")

        # 2. FK: ¿A quién reporta este puesto? (Id del puesto jefe)
        if 'id_puesto_jefe' not in cols:
            print("-> Agregando id_puesto_jefe...")
            cursor.execute("ALTER TABLE cat_puestos ADD COLUMN id_puesto_jefe INTEGER REFERENCES cat_puestos(id_puesto)")
            
        conn.commit()
        print("--- COMPLETADO ---")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_puestos_structure()