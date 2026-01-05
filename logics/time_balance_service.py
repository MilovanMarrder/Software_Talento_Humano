import pandas as pd
import calendar
from datetime import datetime
from config.db_connection import DatabaseConnection

class TimeBalanceService:
    def __init__(self):
        self.db = DatabaseConnection()

    def procesar_cierre_mensual(self, anio, mes):
            """
            Calcula horas y realiza un UPSERT (Insertar o Actualizar) en la BD.
            No genera duplicados y preserva datos futuros (biométrico).
            """
            conn = self.db.get_connection()
            try:
                # --- 1 al 7: CÁLCULOS (Se mantienen idénticos) ---
                start_date = f"{anio}-{int(mes):02d}-01"
                last_day = calendar.monthrange(int(anio), int(mes))[1]
                end_date = f"{anio}-{int(mes):02d}-{last_day}"

                dias_base = 0
                for d in range(1, last_day + 1):
                    if calendar.weekday(int(anio), int(mes), d) < 5: dias_base += 1

                feriados_df = pd.read_sql_query(
                    "SELECT fecha FROM dias_festivos WHERE fecha BETWEEN ? AND ?", 
                    conn, params=(start_date, end_date)
                )
                count_feriados = 0
                for f in feriados_df['fecha']:
                    if datetime.strptime(f, '%Y-%m-%d').weekday() < 5: count_feriados += 1

                query_contratos = """
                SELECT c.id_contrato, COALESCE(j.horas_diarias, 8) as horas_diarias, COALESCE(j.aplica_feriados, 1) as aplica_feriados
                FROM contratos c LEFT JOIN cat_jornadas j ON c.id_jornada = j.id_jornada
                WHERE c.activo = 1 
                """
                df_con = pd.read_sql_query(query_contratos, conn)

                if df_con.empty: return False, "No hay contratos activos."

                query_inasistencias = """
                SELECT c.id_contrato, SUM(CASE WHEN i.es_por_horas = 1 THEN COALESCE(i.horas_totales, 0) ELSE (i.dias_descontar * COALESCE(j.horas_diarias, 8)) END) as total_inasistencia
                FROM inasistencias i JOIN contratos c ON i.id_contrato = c.id_contrato LEFT JOIN cat_jornadas j ON c.id_jornada = j.id_jornada
                WHERE i.fecha_inicio_real BETWEEN ? AND ?
                GROUP BY c.id_contrato
                """
                df_aus = pd.read_sql_query(query_inasistencias, conn, params=(start_date, end_date))

                df_final = pd.merge(df_con, df_aus, on='id_contrato', how='left')
                df_final['total_inasistencia'] = df_final['total_inasistencia'].fillna(0)
                
                df_final['dias_calc'] = dias_base
                mask_feriado = df_final['aplica_feriados'] == 1
                df_final.loc[mask_feriado, 'dias_calc'] -= count_feriados
                
                df_final['horas_esperadas'] = df_final['dias_calc'] * df_final['horas_diarias']
                df_final['horas_netas'] = (df_final['horas_esperadas'] - df_final['total_inasistencia']).clip(lower=0)

                # --- 8. GUARDADO INTELIGENTE (UPSERT) ---
                cursor = conn.cursor()
                
                data_to_insert = []
                for _, row in df_final.iterrows():
                    data_to_insert.append((
                        row['id_contrato'], anio, int(mes),
                        float(row['dias_calc']), float(row['horas_diarias']),
                        float(row['horas_esperadas']), float(row['total_inasistencia']),
                        float(row['horas_netas'])
                    ))

                # SQL PODEROSO:
                # 1. Intenta Insertar.
                # 2. Si choca con el UNIQUE(id_contrato, anio, mes)...
                # 3. ...Hace un UPDATE solo de los campos calculados.
                # NOTA: NO tocamos 'horas_reales_marcaje', así que ese dato se salva si ya existía.
                
                sql_upsert = """
                    INSERT INTO resumen_horas_mensuales 
                    (id_contrato, anio, mes, dias_teoricos, horas_jornada_base, 
                    horas_esperadas, total_inasistencia, horas_programadas_netas, fecha_calculo)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(id_contrato, anio, mes) 
                    DO UPDATE SET
                        dias_teoricos = excluded.dias_teoricos,
                        horas_jornada_base = excluded.horas_jornada_base,
                        horas_esperadas = excluded.horas_esperadas,
                        total_inasistencia = excluded.total_inasistencia,
                        horas_programadas_netas = excluded.horas_programadas_netas,
                        fecha_calculo = CURRENT_TIMESTAMP;
                """

                cursor.executemany(sql_upsert, data_to_insert)

                conn.commit()
                return True, f"Cierre {anio}-{mes} actualizado. {len(data_to_insert)} registros procesados."

            except Exception as e:
                conn.rollback()
                return False, f"Error en cálculo: {str(e)}"
            finally:
                conn.close()