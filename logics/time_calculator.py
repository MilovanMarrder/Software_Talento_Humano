from datetime import datetime, timedelta

class TimeCalculator:
    
    @staticmethod
    def calculate_duration(fecha_ini, fecha_fin, es_por_horas=False, hora_ini="00:00", hora_fin="00:00", jornada_horas=8):
        try:
            # Caso 1: Por Días (Lógica mejorada: Excluir Sábados y Domingos )
            if not es_por_horas:
                start = datetime.strptime(fecha_ini, '%Y-%m-%d')
                end = datetime.strptime(fecha_fin, '%Y-%m-%d')
                
                # Validación básica
                if start > end: return 0.0

                total_days = 0
                current = start
                
                # Iteramos día por día para verificar reglas
                while current <= end:
                    # current.weekday(): 0=Lunes, 6=Domingo
                    # REGLA DE NEGOCIO (Ejemplo): Si es Domingo (6), no cuenta.
                    # TODO: Conectar esto con la configuración de la Jornada real del empleado.
                    if current.weekday() < 5: 
                        total_days += 1
                    
                    current += timedelta(days=1)
                
                return float(total_days)
            
            # Caso 2: Por Horas (Mantiene tu lógica actual, que es correcta para horas intra-día)
            else:
                t_ini = datetime.strptime(hora_ini, '%H:%M')
                t_fin = datetime.strptime(hora_fin, '%H:%M')
                delta = t_fin - t_ini
                horas_totales = delta.total_seconds() / 3600
                
                if jornada_horas > 0:
                    return round(horas_totales / jornada_horas, 2)
                return 0.0
                
        except Exception as e:
            print(f"Error calculando tiempo: {e}")
            return 0.0