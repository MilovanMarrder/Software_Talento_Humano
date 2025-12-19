import sqlite3
from config.db_connection import DatabaseConnection

class KardexDAO:
    def __init__(self):
        self.db = DatabaseConnection()

    def get_kardex_report(self, id_contrato, fecha_inicio=None, fecha_fin=None):
            conn = self.db.get_connection()
            cursor = conn.cursor()

            # 1. Calcular SALDO INICIAL
            # CORRECCIÓN CRÍTICA: Solo calculamos saldo inicial si hay una fecha de corte.
            # Si fecha_inicio es None, queremos ver toda la historia, por ende el saldo inicial es 0.
            saldo_inicial = 0.0
            
            if fecha_inicio:
                query_saldo = """
                    SELECT COALESCE(SUM(dias), 0) FROM kardex_vacaciones 
                    WHERE id_contrato = ? 
                    AND (cuenta_tipo = 'ORDINARIA' OR cuenta_tipo IS NULL)
                    AND fecha_movimiento < ?
                """
                cursor.execute(query_saldo, (id_contrato, fecha_inicio))
                result = cursor.fetchone()
                if result:
                    saldo_inicial = result[0]

            # 2. Obtener MOVIMIENTOS
            query_movs = """
                SELECT 
                    k.id_movimiento,
                    k.fecha_movimiento,
                    k.tipo_movimiento,
                    k.observacion,
                    k.dias,
                    i.fecha_inicio_real,
                    i.fecha_fin_real
                FROM kardex_vacaciones k
                LEFT JOIN inasistencias i ON k.id_referencia = i.id_inasistencia
                WHERE k.id_contrato = ?
                AND (k.cuenta_tipo = 'ORDINARIA' OR k.cuenta_tipo IS NULL)
            """
            params = [id_contrato]

            if fecha_inicio:
                query_movs += " AND k.fecha_movimiento >= ?"
                params.append(fecha_inicio)
            
            if fecha_fin:
                query_movs += " AND k.fecha_movimiento <= ?"
                params.append(fecha_fin)

            query_movs += " ORDER BY k.fecha_movimiento ASC, k.id_movimiento ASC"

            cursor.execute(query_movs, params)
            movimientos = cursor.fetchall()
            
            conn.close()
            return saldo_inicial, movimientos

    def add_manual_movement(self, id_contrato, tipo, dias, obs):
        """Permite agregar saldo inicial o ajustes manuales desde la vista de saldos"""
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO kardex_vacaciones (id_contrato, fecha_movimiento, tipo_movimiento, dias, observacion)
                VALUES (?, CURRENT_DATE, ?, ?, ?)
            """, (id_contrato, tipo, dias, obs))
            conn.commit()
            return True, "Ajuste registrado."
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()