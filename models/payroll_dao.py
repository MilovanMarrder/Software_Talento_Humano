import sqlite3
from config.db_connection import DatabaseConnection

class PayrollDAO:
    def __init__(self):
        self.db = DatabaseConnection()

    def insert_payroll_record(self, id_contrato, anio, mes, salario, bonos, beneficios, deducciones, observaciones=""):
        """
        Inserta un registro de nómina mensual.
        Retorna: (True, mensaje) o (False, error)
        """
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            
            query = """
                INSERT INTO nominas_mensuales 
                (id_contrato, anio, mes, salario_base, bonificaciones, beneficios_laborales, deducciones, observaciones)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            cursor.execute(query, (id_contrato, anio, mes, salario, bonos, beneficios, deducciones, observaciones))
            conn.commit()
            return True, "Registro de nómina guardado correctamente."
            
        except sqlite3.IntegrityError:
            conn.rollback()
            return False, f"Ya existe una nómina registrada para este contrato en {mes}/{anio}."
        except Exception as e:
            conn.rollback()
            return False, f"Error al guardar nómina: {e}"
        finally:
            conn.close()

    def update_payroll_record(self, id_nomina, salario, bonos, beneficios, deducciones, observaciones):
        """Actualiza montos de un registro existente"""
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            query = """
                UPDATE nominas_mensuales
                SET salario_base=?, bonificaciones=?, beneficios_laborales=?, deducciones=?, observaciones=?
                WHERE id_nomina=?
            """
            cursor.execute(query, (salario, bonos, beneficios, deducciones, observaciones, id_nomina))
            conn.commit()
            return True, "Nómina actualizada."
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()

    def get_payrolls_by_contract(self, id_contrato, anio=None):
        """
        Obtiene el histórico para la vista de detalle.
        Si se pasa anio, filtra por ese año.
        """
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            
            base_query = """
                SELECT 
                    id_nomina, anio, mes, 
                    salario_base, bonificaciones, beneficios_laborales, deducciones, 
                    total_pagado, observaciones
                FROM nominas_mensuales
                WHERE id_contrato = ?
            """
            
            params = [id_contrato]
            
            if anio:
                base_query += " AND anio = ?"
                params.append(anio)
                
            base_query += " ORDER BY anio DESC, mes DESC"
            
            cursor.execute(base_query, params)
            rows = cursor.fetchall()
            return rows
        finally:
            conn.close()

    def exists_payroll(self, id_contrato, anio, mes):
        """Helper rápido para validar antes de cargar Excel"""
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id_nomina FROM nominas_mensuales WHERE id_contrato=? AND anio=? AND mes=?", 
                (id_contrato, anio, mes)
            )
            return cursor.fetchone() is not None
        finally:
            conn.close()

    def delete_payroll(self, id_nomina):
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM nominas_mensuales WHERE id_nomina = ?", (id_nomina,))
            conn.commit()
            return True, "Registro eliminado."
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()
            
    # --- MÉTODO ESPECIAL PARA REPORTE/CONSULTA MASIVA ---
    def get_payroll_summary_by_period(self, anio, mes):
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            query = """
                SELECT 
                    nm.id_nomina,  -- <--- CAMBIO CRÍTICO: Necesitamos el ID para editar
                    e.codigo, 
                    e.nombres || ' ' || e.apellidos as empleado,
                    p.nombre_puesto,
                    nm.salario_base, nm.bonificaciones, nm.beneficios_laborales, nm.deducciones, nm.total_pagado,
                    nm.observaciones
                FROM nominas_mensuales nm
                JOIN contratos c ON nm.id_contrato = c.id_contrato
                JOIN empleados e ON c.id_empleado = e.id_empleado
                JOIN cat_puestos p ON c.id_puesto = p.id_puesto
                WHERE nm.anio = ? AND nm.mes = ?
                ORDER BY e.apellidos
            """
            cursor.execute(query, (anio, mes))
            return cursor.fetchall()
        finally:
            conn.close()

    def delete_period(self, anio, mes):
        """Elimina TODOS los registros de nómina de un mes y año específicos."""
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            # Primero contamos cuántos hay para devolver el dato informativo
            cursor.execute("SELECT COUNT(*) FROM nominas_mensuales WHERE anio=? AND mes=?", (anio, mes))
            count = cursor.fetchone()[0]
            
            if count == 0:
                return False, "No hay registros para borrar en este periodo."

            # Ejecutamos borrado
            cursor.execute("DELETE FROM nominas_mensuales WHERE anio=? AND mes=?", (anio, mes))
            conn.commit()
            return True, f"Se eliminaron {count} registros del periodo {mes}/{anio}."
        except Exception as e:
            conn.rollback()
            return False, f"Error al eliminar periodo: {e}"
        finally:
            conn.close()