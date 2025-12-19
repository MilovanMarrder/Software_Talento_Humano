import sqlite3
from config.db_connection import DatabaseConnection

class EmployeeDAO:
    def __init__(self):
        self.db = DatabaseConnection()

    def insert(self, codigo, dni, nombres, apellidos, fecha_nac, activo=1):
            conn = self.db.get_connection()
            try:
                # 1. SANITIZACIÓN (Limpieza de datos)
                # Convertimos cadenas vacías "" a None (NULL en SQL)
                # Esto es vital porque para SQLite "" es un valor y puede duplicarse, 
                # pero si tu restricción UNIQUE choca, mejor manejarlo como NULL.
                dni_final = dni.strip() if dni and dni.strip() else None
                codigo_final = codigo.strip()
                
                # 2. INTENTO DE GUARDADO
                query = """
                    INSERT INTO empleados (codigo, dni, nombres, apellidos, fecha_nacimiento, activo)
                    VALUES (?, ?, ?, ?, ?, ?)
                """
                cursor = conn.cursor()
                cursor.execute(query, (codigo_final, dni_final, nombres, apellidos, fecha_nac, activo))
                conn.commit()
                
                # Si llegamos aquí, se guardó.
                print(f"DEBUG: Empleado {codigo_final} guardado exitosamente en BD.")
                return True, "Empleado guardado exitosamente."
                
            except sqlite3.IntegrityError as e:
                # Esto solo salta si NO se pudo guardar
                err_msg = str(e)
                print(f"DEBUG SQL ERROR: {err_msg}")
                
                if "UNIQUE constraint failed" in err_msg:
                    if "empleados.codigo" in err_msg:
                        return False, f"El Código '{codigo}' ya existe."
                    elif "empleados.dni" in err_msg:
                        return False, f"El DNI '{dni}' ya existe."
                    return False, "El registro ya existe (Código o DNI duplicado)."
                
                return False, f"Error de integridad: {err_msg}"
                
            except Exception as e:
                print(f"DEBUG EXCEPTION: {e}")
                return False, f"Error desconocido: {e}"
            finally:
                conn.close()

    def update(self, id_empleado, codigo, dni, nombres, apellidos, fecha_nac):
        """Actualiza un registro existente"""
        conn = self.db.get_connection()
        try:
            query = """
                UPDATE empleados 
                SET codigo=?, dni=?, nombres=?, apellidos=?, fecha_nacimiento=?
                WHERE id_empleado=?
            """
            cursor = conn.cursor()
            cursor.execute(query, (codigo, dni, nombres, apellidos, fecha_nac, id_empleado))
            conn.commit()
            return True, "Empleado actualizado correctamente."
        except sqlite3.IntegrityError:
            return False, "No se puede actualizar: El Código o DNI pertenecen a otro empleado."
        except Exception as e:
            return False, f"Error al actualizar: {e}"
        finally:
            conn.close()

    def get_all(self):

        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id_empleado, codigo, dni, nombres, apellidos, fecha_nacimiento FROM empleados WHERE activo = 1")
        rows = cursor.fetchall()
        conn.close()
        return rows