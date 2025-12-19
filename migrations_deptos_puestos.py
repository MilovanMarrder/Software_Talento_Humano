import sqlite3

def run():
    print("--- MIGRANDO: DEPARTAMENTO EN PUESTOS ---")
    conn = sqlite3.connect('rrhh.db')
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(cat_puestos)")
        cols = [c[1] for c in cursor.fetchall()]
        
        if 'id_departamento' not in cols:
            print("-> Agregando id_departamento a cat_puestos...")
            cursor.execute("ALTER TABLE cat_puestos ADD COLUMN id_departamento INTEGER REFERENCES cat_departamentos(id_departamento)")
            
        conn.commit()
        print("--- ÉXITO ---")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    run()