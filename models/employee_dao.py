import sqlite3
from config.db_connection import DatabaseConnection
import re

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
                # dni_final = dni.strip() if dni and dni.strip() else None
                dni_limpio = re.sub(r'\D', '', dni) if dni else None
                codigo_final = codigo.strip()
                
                # 2. INTENTO DE GUARDADO
                query = """
                    INSERT INTO empleados (codigo, dni, nombres, apellidos, fecha_nacimiento, activo)
                    VALUES (?, ?, ?, ?, ?, ?)
                """
                cursor = conn.cursor()
                cursor.execute(query, (codigo_final, dni_limpio, nombres, apellidos, fecha_nac, activo))
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
    
    
    def delete_employee(self, employee_id):
            """
            Elimina un empleado SOLO si no tiene contratos vinculados.
            Retorna: (True/False, Mensaje)
            """
            conn = self.db.get_connection()
            try:
                cursor = conn.cursor()
                
                # 1. VERIFICACIÓN DE SEGURIDAD
                # Contamos si tiene contratos (activos o inactivos)
                cursor.execute("SELECT COUNT(*) FROM contratos WHERE id_empleado = ?", (employee_id,))
                count = cursor.fetchone()[0]
                
                if count > 0:
                    return False, f"No se puede eliminar: El empleado tiene {count} contrato(s) registrado(s). Debe eliminar los contratos primero o marcarlo como inactivo."

                # 2. EJECUTAR BORRADO
                cursor.execute("DELETE FROM empleados WHERE id_empleado = ?", (employee_id,))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    return True, "Empleado eliminado correctamente del sistema."
                else:
                    return False, "No se encontró el empleado con ese ID."
                    
            except Exception as e:
                conn.rollback()
                return False, f"Error de base de datos: {str(e)}"
            finally:
                conn.close()