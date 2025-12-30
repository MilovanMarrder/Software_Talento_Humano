from config.db_connection import DatabaseConnection
from logics.time_calculator import TimeCalculator

class AttendanceDAO:
    def __init__(self):
        self.db = DatabaseConnection()

    def get_active_contracts_by_employee(self, id_empleado):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        query = """
            SELECT 
                c.id_contrato,
                p.nombre_puesto || ' - ' || d.nombre || ' (' || tc.nombre || ')' as descripcion
            FROM contratos c
            JOIN cat_puestos p ON c.id_puesto = p.id_puesto
            JOIN cat_departamentos d ON c.id_departamento = d.id_departamento
            JOIN cat_tipos_contrato tc ON c.id_tipo_contrato = tc.id_tipo_contrato
            WHERE c.id_empleado = ? AND c.activo = 1
        """
        cursor.execute(query, (id_empleado,))
        rows = cursor.fetchall()
        conn.close()
        return rows

    def get_history_by_employee(self, id_empleado):
            conn = self.db.get_connection()
            cursor = conn.cursor()
            query = """
                SELECT 
                    i.id_inasistencia,
                    i.fecha_inicio_real,
                    i.fecha_fin_real,
                    ti.nombre_tipo,
                    p.nombre_puesto,
                    i.comentario
                FROM inasistencias i
                JOIN contratos c ON i.id_contrato = c.id_contrato
                JOIN cat_tipos_inasistencia ti ON i.id_tipo = ti.id_tipo
                JOIN cat_puestos p ON c.id_puesto = p.id_puesto
                WHERE c.id_empleado = ?
                ORDER BY i.fecha_inicio_real DESC
            """
            cursor.execute(query, (id_empleado,))
            rows = cursor.fetchall()
            conn.close()
            return rows

    def insert_kardex_manual(self, id_contrato, tipo, dias, obs):
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO kardex_vacaciones 
                (id_contrato, fecha_movimiento, tipo_movimiento, dias, observacion)
                VALUES (?, CURRENT_DATE, ?, ?, ?)
            """, (id_contrato, tipo, dias, obs))
            conn.commit()
            return True, "Movimiento registrado."
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    def get_tipos_inasistencia_combo(self):
        """
        ### CORRECCIÓN: Eliminado JOIN con cat_categorias_inasistencia.
        Solo consulta la tabla cat_tipos_inasistencia.
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Como no hay categorías, mostramos solo el nombre del tipo
        query = """
            SELECT t.id_tipo, t.nombre_tipo, t.cuenta_afectada
            FROM cat_tipos_inasistencia t
            ORDER BY t.nombre_tipo
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        return rows
    
    def get_kardex_balance(self, id_contrato):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        query = """
            SELECT COALESCE(SUM(dias), 0.0) 
            FROM kardex_vacaciones 
            WHERE id_contrato = ? 
            AND (cuenta_tipo = 'ORDINARIA' OR cuenta_tipo IS NULL)
        """
        cursor.execute(query, (id_contrato,))
        saldo = cursor.fetchone()[0]
        conn.close()
        return round(saldo, 2)

    def insert_inasistencia(self, id_con, id_tipo, f_ini, f_fin, es_horas, h_ini, h_fin, detalle, dias_manual=None):
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            
            # 1. Obtener jornada
            cursor.execute("""
                SELECT j.horas_diarias FROM contratos c 
                JOIN cat_jornadas j ON c.id_jornada = j.id_jornada 
                WHERE c.id_contrato = ?
            """, (id_con,))
            res_jornada = cursor.fetchone()
            horas_jornada = res_jornada[0] if res_jornada else 8
            
            # 2. CÁLCULO DE DÍAS
            dias_calculados = TimeCalculator.calculate_duration(
                f_ini, f_fin, es_horas, h_ini, h_fin, horas_jornada
            )

            # Usar manual si existe
            if dias_manual is not None and dias_manual != "":
                try:
                    dias_finales = float(dias_manual)
                except ValueError:
                    dias_finales = dias_calculados 
            else:
                dias_finales = dias_calculados

            # 3. HORAS
            horas_totales = dias_finales * horas_jornada if es_horas else 0

            # 4. INSERTAR
            query_main = """
                INSERT INTO inasistencias 
                (id_contrato, id_tipo, fecha_inicio_real, fecha_fin_real, 
                horas_totales, dias_descontar, comentario)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(query_main, (
                id_con, id_tipo, f_ini, f_fin, 
                horas_totales, dias_finales, detalle
            ))
            id_inasistencia = cursor.lastrowid
            
            # 5. KARDEX
            cursor.execute("SELECT cuenta_afectada FROM cat_tipos_inasistencia WHERE id_tipo = ?", (id_tipo,))
            res = cursor.fetchone()
            cuenta_afectada = res[0] if res else 'NINGUNA'
            
            if cuenta_afectada == 'ORDINARIA':
                query_kardex = """
                    INSERT INTO kardex_vacaciones 
                    (id_contrato, fecha_movimiento, tipo_movimiento, dias, id_referencia, observacion, cuenta_tipo)
                    VALUES (?, CURRENT_DATE, 'GOCE', ?, ?, ?, 'ORDINARIA')
                """
                dias_kardex = -1 * abs(dias_finales) 
                obs = f"Inasistencia #{id_inasistencia}: {detalle}"
                cursor.execute(query_kardex, (id_con, dias_kardex, id_inasistencia, obs))

            conn.commit()
            return True, "Registro guardado y saldo actualizado."
        except Exception as e:
            conn.rollback()
            print(f"DEBUG ERROR INASISTENCIA: {e}") 
            return False, f"Error al guardar: {e}"
        finally:
            conn.close()

    def delete_inasistencia(self, id_inasistencia):
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM kardex_vacaciones WHERE id_referencia = ? AND tipo_movimiento = 'GOCE'", (id_inasistencia,))
            cursor.execute("DELETE FROM inasistencias WHERE id_inasistencia = ?", (id_inasistencia,))
            conn.commit()
            return True, "Registro eliminado y saldo restaurado."
        except Exception as e:
            conn.rollback()
            return False, f"Error: {e}"
        finally:
            conn.close()