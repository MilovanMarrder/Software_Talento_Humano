from models.kardex_dao import KardexDAO
from logics.vacation_service import VacationService

class ReportService:
    def __init__(self):
        self.kardex_dao = KardexDAO()
        self.vac_service = VacationService()

    def get_kardex_report_data(self, id_contrato, fecha_ini=None, fecha_fin=None):
        """
        Genera la estructura de datos completa para el reporte de Kardex.
        Agnóstico de la UI (sirve para Tkinter, Excel, PDF, JSON API).
        """
        response = {
            "saldo_anterior": 0.0,
            "movimientos": [], # Lista de dicts
            "totales": {"debe": 0.0, "haber": 0.0, "saldo_final": 0.0}
        }

        # 1. Procesar devengos automáticos hasta hoy (Write to BD)
        try:
            self.vac_service.process_monthly_accruals(id_contrato)
        except Exception as e:
            print(f"Error procesando devengos automáticos: {e}")

        # 2. Obtener datos históricos (Read from BD)
        saldo_ant, raw_movs = self.kardex_dao.get_kardex_report(id_contrato, fecha_ini, fecha_fin)
        response["saldo_anterior"] = saldo_ant
        
        current_balance = saldo_ant
        total_debe = 0.0
        total_haber = 0.0

        # 3. Procesar filas históricas
        # raw_movs estructura: (id, fecha, tipo, obs, dias, f_ini_real, f_fin_real)
        for m in raw_movs:
            dias = m[4]
            current_balance += dias
            
            # Formatear detalle
            detalle = m[3]
            if m[5] and m[6]:
                detalle = f"{detalle} [Del {m[5]} al {m[6]}]"

            # Clasificar Debe/Haber
            debe = abs(dias) if dias < 0 else 0.0
            haber = dias if dias > 0 else 0.0
            
            total_debe += debe
            total_haber += haber

            response["movimientos"].append({
                "fecha": m[1],
                "tipo": m[2],
                "detalle": detalle,
                "debe": debe,
                "haber": haber,
                "saldo": current_balance,
                "es_proyeccion": False
            })

        # 4. Procesar Proyecciones (Si hay fecha fin futura)
        if fecha_fin:
            proyecciones = self.vac_service.get_future_projections(id_contrato, fecha_fin)
            for p in proyecciones:
                dias = p['dias']
                current_balance += dias
                total_haber += dias # Proyección siempre suma (es ganancia futura)
                
                response["movimientos"].append({
                    "fecha": p['fecha'],
                    "tipo": "PROYECCION",
                    "detalle": p['detalle'],
                    "debe": 0.0,
                    "haber": dias,
                    "saldo": current_balance,
                    "es_proyeccion": True
                })

        # 5. Totales Finales
        response["totales"]["debe"] = total_debe
        response["totales"]["haber"] = total_haber
        response["totales"]["saldo_final"] = current_balance
        
        return response