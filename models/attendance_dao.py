from config.db_connection import DatabaseConnection
from logics.time_calculator import TimeCalculator

class AttendanceDAO:
    def __init__(self):
        self.db = DatabaseConnection()

    def get_active_contracts_by_employee(self, id_empleado):
        """
        Recupera los contratos activos para llenar el Combobox.
        Retorna: [(id_contrato, descripcion_visual), ...]
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()
        # Concatenamos Puesto + Departamento para que el usuario sepa cuál elegir
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
        """Obtiene el historial de faltas de un empleado"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        query = """
            SELECT 
                i.id_inasistencia,
                i.fecha_inicio_real,
                i.fecha_fin_real,
                ti.nombre_tipo,
                p.nombre_puesto,
                i.estado
            FROM inasistencias i
            JOIN cat_tipos_inasistencia ti ON i.id_tipo_inasistencia = ti.id_tipo
            JOIN contratos c ON i.id_contrato = c.id_contrato
            JOIN cat_puestos p ON c.id_puesto = p.id_puesto
            WHERE i.id_empleado = ?
            ORDER BY i.fecha_inicio_real DESC
        """
        cursor.execute(query, (id_empleado,))
        rows = cursor.fetchall()
        conn.close()
        return rows



    def insert_kardex_manual(self, id_contrato, tipo, dias, obs):
        """Para Saldo Inicial o Ajustes manuales"""
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
        """Ahora devolvemos también la cuenta afectada para usarla en la UI si queremos"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        query = """
            SELECT t.id_tipo, c.nombre_categoria || ': ' || t.nombre_tipo, t.cuenta_afectada
            FROM cat_tipos_inasistencia t
            JOIN cat_categorias_inasistencia c ON t.id_categoria = c.id_categoria
            ORDER BY c.nombre_categoria, t.nombre_tipo
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        return rows
    

    def get_kardex_balance(self, id_contrato):
        """Calcula SOLO el saldo de Vacaciones Ordinarias"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        # Filtramos por ORDINARIA para ignorar cualquier basura que haya quedado de pruebas
        # Si la columna cuenta_tipo es NULL (datos viejos), asumimos que es ORDINARIA.
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

    def insert_inasistencia(self, id_emp, id_con, id_tipo, f_ini, f_fin, es_horas, h_ini, h_fin, detalle):
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            
            # 1. Insertar Inasistencia (Registro histórico)
            query_main = """
                INSERT INTO inasistencias 
                (id_empleado, id_contrato, id_tipo_inasistencia, fecha_inicio_real, fecha_fin_real, 
                 es_por_horas, hora_inicio, hora_fin, motivo_detalle)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(query_main, (id_emp, id_con, id_tipo, f_ini, f_fin, int(es_horas), h_ini, h_fin, detalle))
            id_inasistencia = cursor.lastrowid
            
            # 2. VERIFICAR SI DESCUENTA SALDO
            # Buscamos el flag 'cuenta_afectada'
            cursor.execute("SELECT cuenta_afectada FROM cat_tipos_inasistencia WHERE id_tipo = ?", (id_tipo,))
            res = cursor.fetchone()
            cuenta_afectada = res[0] if res else 'NINGUNA'
            
            # LÓGICA DE NEGOCIO:
            # Solo si es 'ORDINARIA', tocamos el dinero (días).
            # Si es 'PROFILACTICA' o 'NINGUNA', solo guardamos el registro histórico (arriba), y NO tocamos el Kardex.
            
            if cuenta_afectada == 'ORDINARIA':
                # A. Calcular Días
                cursor.execute("""
                    SELECT j.horas_diarias FROM contratos c 
                    JOIN cat_jornadas j ON c.id_jornada = j.id_jornada 
                    WHERE c.id_contrato = ?
                """, (id_con,))
                res_jornada = cursor.fetchone()
                horas_jornada = res_jornada[0] if res_jornada else 8
                
                dias_a_descontar = TimeCalculator.calculate_duration(
                    f_ini, f_fin, es_horas, h_ini, h_fin, horas_jornada
                )
                
                # B. Insertar en KARDEX (Solo Ordinaria)
                query_kardex = """
                    INSERT INTO kardex_vacaciones 
                    (id_contrato, fecha_movimiento, tipo_movimiento, dias, id_referencia, observacion, cuenta_tipo)
                    VALUES (?, CURRENT_DATE, 'GOCE', ?, ?, ?, 'ORDINARIA')
                """
                # Negativo porque es GOCE
                dias_kardex = -1 * abs(dias_a_descontar) 
                
                obs = f"Goce Vacaciones: {detalle}"
                cursor.execute(query_kardex, (id_con, dias_kardex, id_inasistencia, obs))

            conn.commit()
            return True, "Registro guardado correctamente."
        except Exception as e:
            conn.rollback()
            return False, f"Error: {e}"
        finally:
            conn.close()

    def delete_inasistencia(self, id_inasistencia):
        """Elimina la falta y revierte el descuento en Kardex si existía"""
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            
            # 1. Eliminar movimiento del Kardex vinculado (Si existe)
            # Esto "devuelve" los días automáticamente al desaparecer el cargo negativo.
            cursor.execute("DELETE FROM kardex_vacaciones WHERE id_referencia = ? AND tipo_movimiento = 'GOCE'", (id_inasistencia,))
            
            # 2. Eliminar el registro histórico
            cursor.execute("DELETE FROM inasistencias WHERE id_inasistencia = ?", (id_inasistencia,))
            
            conn.commit()
            return True, "Registro eliminado y saldo restaurado."
        except Exception as e:
            conn.rollback()
            return False, f"Error: {e}"
        finally:
            conn.close()
            
