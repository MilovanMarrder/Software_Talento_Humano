from config.db_connection import DatabaseConnection
from logics.time_calculator import TimeCalculator
from datetime import datetime, timedelta 

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

    def get_history_by_employee(self, id_empleado, fecha_ini=None, fecha_fin=None):
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Consulta base
            query = """
                SELECT 
                    i.id_inasistencia,      -- 0
                    i.fecha_inicio_real,    -- 1
                    i.fecha_fin_real,       -- 2
                    ti.nombre_tipo,         -- 3
                    p.nombre_puesto,        -- 4
                    i.comentario,           -- 5
                    i.es_por_horas,         -- 6
                    i.hora_inicio,          -- 7
                    i.hora_fin,             -- 8
                    i.horas_totales,        -- 9
                    i.dias_descontar        -- 10
                FROM inasistencias i
                JOIN contratos c ON i.id_contrato = c.id_contrato
                JOIN cat_tipos_inasistencia ti ON i.id_tipo = ti.id_tipo
                JOIN cat_puestos p ON c.id_puesto = p.id_puesto
                WHERE c.id_empleado = ?
            """
            
            params = [id_empleado]

            # Aplicar filtros si existen
            if fecha_ini and fecha_fin:
                query += " AND i.fecha_inicio_real BETWEEN ? AND ?"
                params.extend([fecha_ini, fecha_fin])
                
            query += " ORDER BY i.fecha_inicio_real DESC"
            
            cursor.execute(query, params)
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
                
                # 1. Obtener jornada actual del contrato para cálculos
                cursor.execute("""
                    SELECT COALESCE(j.horas_diarias, 8) 
                    FROM contratos c 
                    LEFT JOIN cat_jornadas j ON c.id_jornada = j.id_jornada 
                    WHERE c.id_contrato = ?
                """, (id_con,))
                res_jornada = cursor.fetchone()
                horas_jornada = float(res_jornada[0]) if res_jornada else 8.0
                
                # 2. CÁLCULO DE DÍAS (Lógica de TimeCalculator)
                dias_calculados = TimeCalculator.calculate_duration(
                    f_ini, f_fin, es_horas, h_ini, h_fin, horas_jornada
                )

                # Usar valor manual si el usuario lo editó en la UI
                if dias_manual is not None and str(dias_manual).strip() != "":
                    try:
                        dias_finales = float(dias_manual)
                    except ValueError:
                        dias_finales = dias_calculados 
                else:
                    dias_finales = dias_calculados

                # 3. CÁLCULO DE HORAS Y DEFINICIÓN DE CAMPOS DE TIEMPO
                horas_totales = 0.0
                db_h_ini = None
                db_h_fin = None

                if es_horas:
                    # Caso: Permiso por Horas
                    # Guardamos los rangos exactos y calculamos la duración
                    db_h_ini = h_ini
                    db_h_fin = h_fin
                    
                    t_ini = datetime.strptime(h_ini, '%H:%M')
                    t_fin = datetime.strptime(h_fin, '%H:%M')
                    
                    # Manejo de turno nocturno (ej: 23:00 a 01:00 implica día siguiente)
                    if t_fin < t_ini:
                        t_fin += timedelta(days=1)
                    
                    delta = t_fin - t_ini
                    horas_totales = delta.total_seconds() / 3600.0
                else:
                    # Caso: Permiso por Días
                    # Horas inicio/fin van nulas, horas totales = días * jornada
                    db_h_ini = None 
                    db_h_fin = None
                    horas_totales = dias_finales * horas_jornada

                # 4. INSERTAR (CORREGIDO: Ahora incluye hora_inicio y hora_fin)
                query_main = """
                    INSERT INTO inasistencias 
                    (id_contrato, id_tipo, fecha_inicio_real, fecha_fin_real, 
                    horas_totales, dias_descontar, hora_inicio, hora_fin, 
                    comentario, es_por_horas) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                flag_horas = 1 if es_horas else 0
                
                cursor.execute(query_main, (
                    id_con, id_tipo, f_ini, f_fin, 
                    horas_totales, dias_finales, db_h_ini, db_h_fin, 
                    detalle, flag_horas
                ))
                
                # Recuperar ID para referencia en Kardex
                id_inasistencia = cursor.lastrowid
                
                # 5. ACTUALIZACIÓN DE KARDEX (Si aplica)
                cursor.execute("SELECT cuenta_afectada FROM cat_tipos_inasistencia WHERE id_tipo = ?", (id_tipo,))
                res = cursor.fetchone()
                cuenta_afectada = res[0] if res else 'NINGUNA'
                
                if cuenta_afectada == 'ORDINARIA':
                    query_kardex = """
                        INSERT INTO kardex_vacaciones 
                        (id_contrato, fecha_movimiento, tipo_movimiento, dias, id_referencia, observacion, cuenta_tipo)
                        VALUES (?, CURRENT_DATE, 'GOCE', ?, ?, ?, 'ORDINARIA')
                    """
                    # Se descuenta en negativo
                    dias_kardex = -1 * abs(dias_finales) 
                    obs = f"Inasistencia #{id_inasistencia}: {detalle} ({horas_totales:.2f} hrs)"
                    cursor.execute(query_kardex, (id_con, dias_kardex, id_inasistencia, obs))

                conn.commit()
                return True, "Registro guardado exitosamente."
                
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