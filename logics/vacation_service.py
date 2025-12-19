# logics/vacation_service.py
import sqlite3
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from config.db_connection import DatabaseConnection


class VacationService:
    def __init__(self):
        self.db = DatabaseConnection()

    def process_monthly_accruals(self, id_contrato):
        """
        Calcula y guarda en BD solo hasta el mes cerrado ANTERIOR o ACTUAL (nunca futuro).
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
            # 1. Datos del contrato
            cursor.execute("SELECT fecha_inicio, fecha_inicio_kardex FROM contratos WHERE id_contrato = ?", (id_contrato,))
            row = cursor.fetchone()
            if not row or not row[1]: return 
            
            fecha_inicio_labores = datetime.strptime(row[0], '%Y-%m-%d').date()
            fecha_inicio_proceso = datetime.strptime(row[1], '%Y-%m-%d').date()
            
            hoy = date.today()
            current_date = fecha_inicio_proceso
            
            while True:
                # Calcular fin de mes
                next_month = current_date.replace(day=28) + timedelta(days=4)
                last_day_of_month = next_month - timedelta(days=next_month.day)
                
                # REGLA DE ORO: Si el fin de mes es mayor a HOY, paramos. No guardamos futuros.
                if last_day_of_month > hoy:
                    break
                
                # Validación de fechas históricas
                if last_day_of_month < fecha_inicio_proceso:
                    current_date = last_day_of_month + timedelta(days=1)
                    continue

                # Insertar en BD si no existe
                self._process_single_month(cursor, id_contrato, fecha_inicio_labores, last_day_of_month)
                
                current_date = last_day_of_month + timedelta(days=1)
            
            conn.commit()
            
        except Exception as e:
            print(f"Error VacationService: {e}")
            conn.rollback()
        finally:
            conn.close()

    def get_future_projections(self, id_contrato, target_date_str):
        """
        Calcula en MEMORIA (sin guardar en BD) las acumulaciones futuras.
        Retorna una lista de diccionarios con la simulación.
        """
        if not target_date_str: return []
        
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        hoy = date.today()
        
        # Si la fecha filtro es hoy o pasado, no hay proyección
        if target_date <= hoy: return []

        proyecciones = []
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
            # Necesitamos fecha inicio para calcular antigüedad futura
            cursor.execute("SELECT fecha_inicio FROM contratos WHERE id_contrato = ?", (id_contrato,))
            row = cursor.fetchone()
            if not row: return []
            fecha_inicio_labores = datetime.strptime(row[0], '%Y-%m-%d').date()

            # Empezamos la proyección desde el primer mes futuro
            # Lógica rápida: Primer día del mes siguiente a hoy
            # (Asumiendo que process_monthly_accruals ya corrió hasta hoy)
            mes_actual = hoy.replace(day=28) + timedelta(days=4)
            fin_mes_actual = mes_actual - timedelta(days=mes_actual.day)
            
            # Si hoy es 17/12, el fin de mes es 31/12. Si 31/12 > 17/12 (True),
            # entonces el cierre de Diciembre es "Futuro". Empezamos a proyectar este mismo mes.
            # Si hoy fuera 31/12, Diciembre ya se guardó en BD. Proyectamos desde Enero.
            
            start_date = hoy
            
            current_date = start_date
            
            while True:
                # Calcular siguiente cierre de mes
                next_month = current_date.replace(day=28) + timedelta(days=4)
                last_day_of_month = next_month - timedelta(days=next_month.day)
                
                # Si nos pasamos de la fecha filtro seleccionada por el usuario, paramos
                if last_day_of_month > target_date:
                    break
                
                # Solo proyectamos fechas futuras a hoy
                if last_day_of_month > hoy:
                    # Cálculos Matemáticos (Idénticos al real)
                    antiguedad = relativedelta(last_day_of_month, fecha_inicio_labores)
                    anio_corriente = antiguedad.years + 1
                    
                    # Buscar Regla (Reutilizamos lógica o consulta rápida)
                    # Nota: Para optimizar, podrías cachear las reglas, aquí hacemos query simple
                    cursor.execute("SELECT dias_otorgar FROM cat_reglas_vacaciones WHERE anios_antiguedad = ?", (anio_corriente,))
                    res = cursor.fetchone()
                    if not res:
                         cursor.execute("SELECT dias_otorgar FROM cat_reglas_vacaciones ORDER BY anios_antiguedad DESC LIMIT 1")
                         res = cursor.fetchone()
                    
                    dias_anuales = res[0] if res else 15
                    dias_mensuales = dias_anuales / 12.0
                    
                    # Estructura Virtual (Simula lo que viene de BD)
                    proyecciones.append({
                        'fecha': last_day_of_month.strftime('%Y-%m-%d'),
                        'tipo': 'PROYECCION', # Etiqueta especial
                        'detalle': f"Proyección a {last_day_of_month.strftime('%Y-%m')} (Antigüedad: {antiguedad.years}a)",
                        'dias': dias_mensuales,
                        'es_virtual': True
                    })

                current_date = last_day_of_month + timedelta(days=1)
                
        finally:
            conn.close()
            
        return proyecciones

    def _process_single_month(self, cursor, id_contrato, fecha_inicio_labores, fecha_cierre):
        # ... (Este método se queda IGUAL que antes, contiene la lógica de INSERT real) ...
        # Solo asegúrate de copiarlo aquí si lo borraste
        periodo = fecha_cierre.strftime('%Y-%m')
        cursor.execute("""
            SELECT id_movimiento FROM kardex_vacaciones
            WHERE id_contrato = ? AND tipo_movimiento = 'ACUMULACION_MENSUAL'
            AND strftime('%Y-%m', fecha_movimiento) = ?
        """, (id_contrato, periodo))
        
        if cursor.fetchone(): return

        antiguedad = relativedelta(fecha_cierre, fecha_inicio_labores)
        anios_cumplidos = antiguedad.years
        anio_corriente = anios_cumplidos + 1
        
        cursor.execute("SELECT dias_otorgar FROM cat_reglas_vacaciones WHERE anios_antiguedad = ?", (anio_corriente,))
        res = cursor.fetchone()
        if not res:
            cursor.execute("SELECT dias_otorgar FROM cat_reglas_vacaciones ORDER BY anios_antiguedad DESC LIMIT 1")
            res = cursor.fetchone()
            
        dias_anuales = res[0] if res else 15
        dias_mensuales = dias_anuales / 12.0
        
        obs = f"Ganados en {periodo} (Antigüedad: {anios_cumplidos}a {antiguedad.months}m)"
        
        # Insertamos explícitamente como ORDINARIA
        cursor.execute("""
            INSERT INTO kardex_vacaciones 
            (id_contrato, fecha_movimiento, tipo_movimiento, dias, observacion, cuenta_tipo)
            VALUES (?, ?, 'ACUMULACION_MENSUAL', ?, ?, 'ORDINARIA')
        """, (id_contrato, fecha_cierre, dias_mensuales, obs))