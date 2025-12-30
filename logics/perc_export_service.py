import pandas as pd
from config.db_connection import DatabaseConnection
import calendar
import sqlite3
from config import settings

class PercExportService:
    def __init__(self):
        self.db = DatabaseConnection()

    def generate_empleados_perc_excel(self, year, month, filepath):
            """
            Genera el reporte Excel para PERC.
            Ahora cruza información con la tabla 'nominas_mensuales' para obtener datos reales.
            """
            conn = self.db.get_connection()
            if not conn:
                return False, "No hay conexión a base de datos."

            try:
                # 1. Definir rango de fechas para validar contratos activos
                start_date_str = f"{year}-{int(month):02d}-01"
                last_day = calendar.monthrange(int(year), int(month))[1]
                end_date_str = f"{year}-{int(month):02d}-{last_day}"

                # 2. Query SQL Enriquecido
                # Lógica: Trae todos los contratos activos. 
                # Si hay nómina cargada para este mes, usa esos montos.
                # Si no hay nómina, usa el salario del contrato y 0 en variables.
                query = """
                SELECT 
                    c.dni_perc as 'Identificación',
                    p.nombre_puesto as 'Nombre',
                    
                    -- PRIORIDAD: Salario de Nómina > Salario Contrato
                    COALESCE(nm.salario_base, c.salario) as 'Salario Base',
                    
                    COALESCE(gp.codigo, 'GEN') as 'Categoría de Empleado',
                    '00' as 'Niveles Laborales',
                    
                    -- PRIORIDAD: Dato de Nómina > 0
                    COALESCE(nm.bonificaciones, 0) as 'Bonificaciones',
                    COALESCE(nm.beneficios_laborales, 0) as 'Beneficios Laborales',
                    
                    '1' as 'Tipo de Contrato'
                FROM contratos c
                JOIN empleados e ON c.id_empleado = e.id_empleado
                JOIN cat_puestos p ON c.id_puesto = p.id_puesto
                LEFT JOIN cat_grupos_perc gp ON p.id_grupo_perc = gp.id_grupo
                
                -- JOIN con la tabla de nóminas ESPECÍFICA para el año/mes solicitado
                LEFT JOIN nominas_mensuales nm ON c.id_contrato = nm.id_contrato 
                                            AND nm.anio = ? 
                                            AND nm.mes = ?
                WHERE 
                    c.activo = 1
                    AND c.fecha_inicio <= ?
                    AND (c.fecha_fin IS NULL OR c.fecha_fin >= ?)
                """
                
                # IMPORTANTE: El orden de los parámetros debe coincidir con los ? en el SQL
                # 1 y 2: Para el LEFT JOIN (nm.anio, nm.mes)
                # 3 y 4: Para el WHERE de fechas (end_date, start_date)
                params = (year, int(month), end_date_str, start_date_str)
                
                # Usamos pandas para leer SQL directamente
                df = pd.read_sql_query(query, conn, params=params)
                
                if df.empty:
                    return False, "No se encontraron contratos activos en el periodo seleccionado."

                # 3. Post-Procesamiento
                df['Identificación'] = df['Identificación'].astype(str)
                df['Categoría de Empleado'] = df['Categoría de Empleado'].astype(str).str.zfill(5)

                # 4. Exportar a Excel
                with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Empleado')
                    
                    # Auto-ajustar ancho columnas
                    worksheet = writer.sheets['Empleado']
                    for column_cells in worksheet.columns:
                        length = max(len(str(cell.value)) for cell in column_cells)
                        worksheet.column_dimensions[column_cells[0].column_letter].width = length + 2

                return True, f"Reporte generado exitosamente en:\n{filepath}"

            except Exception as e:
                return False, f"Error generando reporte: {str(e)}"
            finally:
                conn.close()
    

    def generate_programacion_horas_perc_excel(self, year, month, filepath, input_path, dias_feriado=0, cant_horas_diarias=8):
            """
            year, month: Periodo
            filepath: Ruta donde se GUARDARÁ el resultado
            input_path: Ruta del Excel que el usuario CARGÓ
            """
            try:
                # 1. Importar el archivo cargado por el usuario
                df = pd.read_excel(input_path)

                # Limpieza de DNI (como tenías en tu lógica)
                if 'Empleado' not in df.columns:
                    return False, "El archivo cargado no tiene la columna 'Empleado'"
                
                df['dni_perc'] = df['Empleado'].str.split('__').str[1]

                # --- Función interna de cálculo ---
                def obtener_horas_programadas(anio, mes, feriados, horas_dia):
                    num_dias = calendar.monthrange(int(anio), int(mes))[1]
                    dias_laborales = 0
                    for dia in range(1, num_dias + 1):
                        if calendar.weekday(int(anio), int(mes), dia) < 5: # Lunes a Viernes
                            dias_laborales += 1
                    return (dias_laborales - int(feriados)) * int(horas_dia)

                horas_totales = obtener_horas_programadas(year, month, dias_feriado, cant_horas_diarias)
                df['horas_programadas'] = horas_totales
                
                df_base_perc = df[['Empleado','Total Empleados', 'Total Pagado', 'Componente Salarial','dni_perc','horas_programadas']].copy()

                # 2. Traer distribución desde DB
                conn = self.db.get_connection()
                query = """
                SELECT 
                    up.codigo_up || '-' || up.nombre_up AS unidad_produccion,
                    c.dni_perc,
                    COALESCE(dc.porcentaje, 0) AS porcentaje
                FROM cat_unidades_produccion AS up
                LEFT JOIN distribucion_costos AS dc ON up.id_unidad = dc.id_unidad
                LEFT JOIN contratos AS c ON dc.id_contrato = c.id_contrato;
                """
                dist_up = pd.read_sql_query(query, conn)
                conn.close()

                # 3. Procesamiento y Pivot
                base = pd.merge(df_base_perc, dist_up, on='dni_perc', how='right')
                base['horas'] = base['horas_programadas'] * (base['porcentaje'] / 100)
                base = base[['Empleado', 'Total Empleados', 'Total Pagado', 'Componente Salarial','unidad_produccion','horas']].fillna({'horas':0})
                
                df_pivot = base.pivot(
                    index=['Empleado', 'Total Empleados', 'Total Pagado', 'Componente Salarial'],
                    columns='unidad_produccion',
                    values='horas'
                ).reset_index()

                # 4. Exportar al filepath seleccionado por el usuario
                with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                    df_pivot[df_pivot['Empleado'].notna()].to_excel(writer, index=False, sheet_name='Programación Hora')
                    
                    worksheet = writer.sheets['Programación Hora']
                    for column_cells in worksheet.columns:
                        length = max(len(str(cell.value)) for cell in column_cells)
                        worksheet.column_dimensions[column_cells[0].column_letter].width = length + 2

                return True, f"Reporte procesado y guardado en:\n{filepath}"

            except Exception as e:
                return False, f"Error en procesamiento: {str(e)}"


    def generate_horas_extras_excel():
        pass

    def export_database_to_excel(self, output_path):
        """
        Exporta todas las tablas de la BD a un Excel (hoja por tabla).
        No requiere parámetros de fecha.
        """
        db_path = settings.DB_PATH

        if not db_path.exists():
            return False, f"No se encontró la base de datos en: {db_path}"

        conn = sqlite3.connect(db_path)

        try:
            # 1. Obtener lista de tablas
            query_tables = """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            AND name NOT LIKE 'sqlite_%';
            """
            tables = pd.read_sql(query_tables, conn)

            if tables.empty:
                return False, "La base de datos está vacía (no tiene tablas)."

            # 2. Escribir Excel
            with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
                for table_name in tables["name"]:
                    # Leemos cada tabla
                    df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
                    
                    # Excel limita nombres de hoja a 31 chars
                    sheet_name = table_name[:31]
                    
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    
                    # Ajuste cosmético de ancho de columnas
                    worksheet = writer.sheets[sheet_name]
                    for column_cells in worksheet.columns:
                        length = max(len(str(cell.value)) for cell in column_cells)
                        if length > 0:
                            worksheet.column_dimensions[column_cells[0].column_letter].width = length + 2

            return True, f"Base de datos exportada correctamente en:\n{output_path}"

        except Exception as e:
            return False, f"Error exportando BD: {str(e)}"
        finally:
            conn.close()