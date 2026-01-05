from datetime import datetime, timedelta

class TimeCalculator:
    
    @staticmethod
    def calculate_duration(fecha_ini, fecha_fin, es_por_horas=False, hora_ini="00:00", hora_fin="00:00", jornada_horas=8):
        try:
            # Validación básica de nulos
            if not fecha_ini or not fecha_fin:
                return 0.0

            # Caso 1: Por Días (Cálculo Inclusivo Natural)
            if not es_por_horas:
                start = datetime.strptime(fecha_ini, '%Y-%m-%d')
                end = datetime.strptime(fecha_fin, '%Y-%m-%d')
                
                # Validación inversa
                if start > end: 
                    return 0.0

                # Fórmula Matemática: (Fin - Inicio) + 1 día para que sea inclusivo
                # Ej: Del 10 al 10. (10-10) = 0 + 1 = 1 día.
                delta = end - start
                return float(delta.days + 1)
            
            # Caso 2: Por Horas (Intra-día)
            else:
                t_ini = datetime.strptime(hora_ini, '%H:%M')
                t_fin = datetime.strptime(hora_fin, '%H:%M')
                
                # Si el turno cruza la medianoche (ej: 22:00 a 06:00), sumamos un día al fin
                if t_fin < t_ini:
                    t_fin += timedelta(days=1)

                delta = t_fin - t_ini
                horas_totales = delta.total_seconds() / 3600
                
                # Si queremos retornar "días equivalentes" (ej: 4 horas = 0.5 días)
                if jornada_horas > 0:
                    return round(horas_totales / jornada_horas, 2)
                
                return 0.0
                
        except Exception as e:
            print(f"Error calculando tiempo: {e}")
            return 0.0