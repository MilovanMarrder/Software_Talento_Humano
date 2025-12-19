import sqlite3

def calculate_dni_perc(dni, tipo_contrato_nombre):
    """
    Regla de Negocio:
    - HMEP -> DNI Limpio
    - OTROS -> DNI + Primera Letra (S=SESAL, L=LACTANTE)
    """
    nombre_upper = tipo_contrato_nombre.upper().strip()
    
    if "HMEP" in nombre_upper:
        return dni
    else:
        # Toma la primera letra (S de SESAL, L de LACTANTE)
        suffix = nombre_upper[0]
        return f"{dni}{suffix}"

def run_backfill():
    conn = sqlite3.connect('rrhh.db')
    cursor = conn.cursor()
    
    try:
        # Obtener contratos activos + DNI + Nombre Tipo Contrato
        query = """
        SELECT c.id_contrato, e.dni, tc.nombre
        FROM contratos c
        JOIN empleados e ON c.id_empleado = e.id_empleado
        JOIN cat_tipos_contrato tc ON c.id_tipo_contrato = tc.id_tipo_contrato
        WHERE c.activo = 1
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        
        print(f"Procesando {len(rows)} contratos activos...")
        
        updates = []
        for row in rows:
            id_con, dni, tipo_nombre = row
            if not dni: continue # Skip si data sucia
            
            new_dni_perc = calculate_dni_perc(dni, tipo_nombre)
            updates.append((new_dni_perc, id_con))
            
            print(f"  ID {id_con}: {tipo_nombre} -> {dni} => {new_dni_perc}")
        
        # Ejecutar update masivo
        cursor.executemany("UPDATE contratos SET dni_perc = ? WHERE id_contrato = ?", updates)
        conn.commit()
        print("--- ACTUALIZACIÓN DNI PERC COMPLETADA ---")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    run_backfill()