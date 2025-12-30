import pandas as pd
from config.db_connection import DatabaseConnection
import calendar
import sqlite3
import re
import numpy as np
from config import settings

class PercExportService:
    def __init__(self):
        self.db = DatabaseConnection()

    # --------------------------------------------------------------------------
    # 1. GENERACIÓN DE REPORTES (EXPORTACIÓN)
    # --------------------------------------------------------------------------

    def generate_empleados_perc_excel(self, year, month, filepath):
        """
        Genera el reporte Excel para PERC cruzando con nóminas.
        """
        conn = self.db.get_connection()
        if not conn:
            return False, "No hay conexión a base de datos."

        try:
            # 1. Definir rango de fechas
            start_date_str = f"{year}-{int(month):02d}-01"
            last_day = calendar.monthrange(int(year), int(month))[1]
            end_date_str = f"{year}-{int(month):02d}-{last_day}"

            # 2. Query SQL Enriquecido
            query = """
            SELECT 
                c.dni_perc as 'Identificación',
                p.nombre_puesto as 'Nombre',
                COALESCE(nm.salario_base, c.salario) as 'Salario Base',
                COALESCE(gp.codigo, 'GEN') as 'Categoría de Empleado',
                '00' as 'Niveles Laborales',
                COALESCE(nm.bonificaciones, 0) as 'Bonificaciones',
                COALESCE(nm.beneficios_laborales, 0) as 'Beneficios Laborales',
                '1' as 'Tipo de Contrato'
            FROM contratos c
            JOIN empleados e ON c.id_empleado = e.id_empleado
            JOIN cat_puestos p ON c.id_puesto = p.id_puesto
            LEFT JOIN cat_grupos_perc gp ON p.id_grupo_perc = gp.id_grupo
            LEFT JOIN nominas_mensuales nm ON c.id_contrato = nm.id_contrato 
                                        AND nm.anio = ? 
                                        AND nm.mes = ?
            WHERE 
                c.activo = 1
                AND c.fecha_inicio <= ?
                AND (c.fecha_fin IS NULL OR c.fecha_fin >= ?)
            """
            
            params = (year, int(month), end_date_str, start_date_str)
            df = pd.read_sql_query(query, conn, params=params)
            
            if df.empty:
                return False, "No se encontraron contratos activos en el periodo seleccionado."

            # 3. Post-Procesamiento
            df['Identificación'] = df['Identificación'].astype(str)
            df['Categoría de Empleado'] = df['Categoría de Empleado'].astype(str).str.zfill(5)

            # 4. Exportar
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Empleado')
                
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
        Procesa el archivo de programación de horas.
        """
        try:
            # 1. Importar el archivo cargado por el usuario
            df = pd.read_excel(input_path)

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

            # 4. Exportar
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df_pivot[df_pivot['Empleado'].notna()].to_excel(writer, index=False, sheet_name='Programación Hora')
                
                worksheet = writer.sheets['Programación Hora']
                for column_cells in worksheet.columns:
                    length = max(len(str(cell.value)) for cell in column_cells)
                    worksheet.column_dimensions[column_cells[0].column_letter].width = length + 2

            return True, f"Reporte procesado y guardado en:\n{filepath}"

        except Exception as e:
            return False, f"Error en procesamiento: {str(e)}"

    def export_database_to_excel(self, output_path):
        """
        Exporta todas las tablas de la BD a un Excel (Backup Completo).
        """
        db_path = settings.DB_PATH

        if not db_path.exists():
            return False, f"No se encontró la base de datos en: {db_path}"

        conn = sqlite3.connect(db_path)

        try:
            # 1. Obtener lista de tablas
            query_tables = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
            tables = pd.read_sql(query_tables, conn)

            if tables.empty:
                return False, "La base de datos está vacía (no tiene tablas)."

            # 2. Escribir Excel
            with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
                for table_name in tables["name"]:
                    df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
                    sheet_name = table_name[:31]
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    
                    # Ajuste ancho columnas
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

    # --------------------------------------------------------------------------
    # 2. IMPORTACIÓN INTELIGENTE (RESTORE) - NUEVA IMPLEMENTACIÓN
    # --------------------------------------------------------------------------

    def import_database_from_excel(self, input_path):
            """
            Restaura la BD aplicando limpieza, validación de esquema y manejo de columnas generadas.
            Incluye verificación final de integridad referencial.
            """
            conn = self.db.get_connection()
            if not conn: return False, "Sin conexión a BD."

            try:
                # 1. Leer Excel completo con Conversión de Tipos
                try:
                    # Diccionario de seguridad para preservar ceros a la izquierda
                    text_cols = {
                        'dni': str,
                        'codigo': str,
                        'dni_perc': str,
                        'codigo_up': str,       # Unidades de producción
                        'codigo_interno': str,  # Departamentos
                        'Identificación': str   # Por si importas reportes exportados
                    }
                    
                    # converters=text_cols fuerza a Pandas a leer esas columas como Texto puro
                    xls_dict = pd.read_excel(input_path, sheet_name=None, converters=text_cols)
                except Exception as e:
                    return False, f"No se pudo leer el archivo Excel: {e}"

                cursor = conn.cursor()
                
                # 2. Configuración para Inserción Masiva
                cursor.execute("PRAGMA foreign_keys = OFF") # Apagamos validación temporalmente
                cursor.execute("BEGIN TRANSACTION")         # Iniciamos bloque atómico

                # Obtener tablas que REALMENTE existen en la BD (Target)
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                db_tables = [row[0] for row in cursor.fetchall()]

                tables_processed = 0
                logs = []

                for sheet_name, df in xls_dict.items():
                    table_name = sheet_name.strip()

                    if table_name in db_tables:
                        # A. Limpieza de Datos (Quitar espacios, formatear fechas, NaN -> None)
                        df = self._clean_dataframe(df)

                        # B. Análisis de Columnas
                        # Obtenemos las columnas válidas de la tabla destino (sin generadas)
                        valid_columns = self._get_writable_columns(cursor, table_name)
                        
                        # Intersección: Solo columnas que existen en Excel Y en BD
                        cols_to_import = [c for c in df.columns if c in valid_columns]
                        
                        if not cols_to_import:
                            logs.append(f"⚠ {table_name}: Se omitió (sin columnas coincidentes).")
                            continue

                        # Filtramos el DF final
                        df_final = df[cols_to_import]

                        # C. Wipe & Load (Borrar y Cargar)
                        cursor.execute(f"DELETE FROM {table_name}")
                        
                        # Insertar (usamos chunksize para prevenir errores de memoria)
                        df_final.to_sql(table_name, conn, if_exists='append', index=False, chunksize=500)
                        
                        tables_processed += 1
                        logs.append(f"✅ {table_name}: {len(df_final)} registros importados.")

                # 3. Validación preliminar
                if tables_processed == 0:
                    conn.rollback()
                    return False, "El Excel no contiene ninguna hoja que coincida con las tablas del sistema."

                # ------------------------------------------------------------------
                # 4. VERIFICACIÓN DE INTEGRIDAD REFERENCIAL (CRÍTICO)
                # ------------------------------------------------------------------
                # Antes de hacer COMMIT, reactivamos las llaves foráneas y buscamos huérfanos.
                
                cursor.execute("PRAGMA foreign_keys = ON")
                
                # foreign_key_check revisa toda la BD buscando violaciones
                cursor.execute("PRAGMA foreign_key_check")
                integrity_errors = cursor.fetchall()

                if integrity_errors:
                    # Si hay errores, construimos un reporte y cancelamos todo.
                    error_msg = "⛔ ERROR DE INTEGRIDAD: La importación se canceló porque el archivo contiene inconsistencias:\n"
                    
                    limit = 0
                    for err in integrity_errors:
                        if limit < 5: # Solo mostramos los primeros 5 errores
                            # Formato err: (table_name, rowid, target_table, fkid)
                            tabla_origen = err[0]
                            tabla_destino = err[2]
                            error_msg += f"- La tabla '{tabla_origen}' referencia registros inexistentes en '{tabla_destino}'.\n"
                        limit += 1
                    
                    error_msg += "\nRevise que no haya borrado registros padres (Empleados, Puestos) que son usados en otras tablas."
                    
                    # Lanzamos excepción manual para activar el rollback en el bloque except
                    raise Exception(error_msg)

                # 5. Finalización Exitosa
                conn.commit() # ¡Solo guardamos si pasó la prueba de integridad!
                
                # Mantenimiento
                try: cursor.execute("VACUUM") 
                except: pass

                return True, "Restauración completada y verificada con éxito.\n\nDetalle:\n" + "\n".join(logs)

            except Exception as e:
                if conn:
                    conn.rollback() # Revertimos cualquier cambio a la BD
                    try: conn.execute("PRAGMA foreign_keys = ON") # Restauramos seguridad
                    except: pass
                return False, f"Error CRÍTICO durante la restauración:\n{str(e)}"
            finally:
                conn.close()

    # --------------------------------------------------------------------------
    # 3. HELPERS PRIVADOS (LIMPIEZA Y VALIDACIÓN)
    # --------------------------------------------------------------------------

    def _clean_dataframe(self, df):
        """Aplica limpieza estándar a todo el DataFrame antes de insertar"""

        # 0. Lista de columnas forzadas a String (Limpieza profunda)
        target_string_cols = ['dni', 'codigo', 'dni_perc', 'codigo_up', 'codigo_interno']
        
        for col in target_string_cols:
            if col in df.columns:
                # Asegurar string
                df[col] = df[col].astype(str)
                # Si Pandas leyó "nan" (texto) donde había nulos, lo corregimos
                df[col] = df[col].replace({'nan': None, 'None': None, '<NA>': None})
                # Eliminar decimales fantasmas (ej: "0801.0" -> "0801")
                df[col] = df[col].apply(lambda x: x.split('.')[0] if x and '.' in x else x)

        # 1. Quitar espacios en strings
        df_obj = df.select_dtypes(['object'])
        if not df_obj.empty:
            df[df_obj.columns] = df_obj.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

        # 2. Manejo de Nulos: Reemplazar NaN de numpy por None (para que sea NULL en SQLite)
        df = df.replace({np.nan: None})
        
        # 3. Limpieza de Fechas Genérica
        for col in df.columns:
            if 'fecha' in col.lower() or 'date' in col.lower():
                try:
                    # Convertir a datetime y luego a string ISO (YYYY-MM-DD)
                    df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d')
                    df[col] = df[col].replace({np.nan: None})
                except:
                    pass 
        return df

    def _get_writable_columns(self, cursor, table_name):
        """
        Retorna la lista de columnas de una tabla en las que SE PUEDE ESCRIBIR.
        Excluye columnas GENERATED ALWAYS AS (...) usando Regex.
        """
        # 1. Obtener todas las columnas físicas
        cursor.execute(f"PRAGMA table_info({table_name})")
        all_cols = [row[1] for row in cursor.fetchall()]

        # 2. Detectar columnas generadas analizando el DDL SQL
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        row = cursor.fetchone()
        generated_cols = []
        
        if row and row[0]:
            ddl = row[0].upper()
            for col in all_cols:
                # Regex: Busca "NOMBRE_COL ... AS ("
                pattern = fr'\b{col}\b[^,]*AS\s*\('
                if re.search(pattern, ddl):
                    generated_cols.append(col)

        # 3. Retornar solo las escribibles
        writable = [c for c in all_cols if c not in generated_cols]
        return writable