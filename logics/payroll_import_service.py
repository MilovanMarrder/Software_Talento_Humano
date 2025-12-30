import pandas as pd
from datetime import datetime
from config.db_connection import DatabaseConnection
from models.payroll_dao import PayrollDAO

class PayrollImportService:
    def __init__(self):
        self.db = DatabaseConnection()
        self.dao = PayrollDAO()

    def generate_payroll_template(self, filepath, anio, mes):
        """
        Genera un Excel con los empleados ACTIVOS.
        Columnas: ID_CONTRATO (Oculto o visible), CODIGO, NOMBRE, DNI, PUESTO, DEPARTAMENTO, SALARIO_BASE_ACTUAL
        """
        conn = self.db.get_connection()
        try:
            # 1. Obtenemos datos de contratos ACTIVOS
            query = """
                SELECT 
                    c.id_contrato,
                    e.codigo as CODIGO_EMPLEADO,
                    e.nombres || ' ' || e.apellidos as NOMBRE_COMPLETO,
                    e.dni as DNI,
                    p.nombre_puesto as PUESTO,
                    tc.nombre as TIPO_CONTRATO,
                    c.salario as SALARIO_CONTRATO_BASE -- Referencia visual para RRHH
                FROM contratos c
                JOIN empleados e ON c.id_empleado = e.id_empleado
                JOIN cat_puestos p ON c.id_puesto = p.id_puesto
                JOIN cat_tipos_contrato tc ON c.id_tipo_contrato = tc.id_tipo_contrato
                WHERE c.activo = 1
                ORDER BY e.apellidos
            """
            
            df = pd.read_sql(query, conn)

            # 2. Agregamos las columnas vacías que RRHH debe llenar
            # Pre-llenamos el Año y Mes para evitar errores manuales
            df['ANIO_PROCESO'] = anio
            df['MES_PROCESO'] = mes
            
            # Columnas monetarias vacías (o con 0)
            df['SALARIO_DEVENGADO'] = df['SALARIO_CONTRATO_BASE'] # Sugerencia: Pre-llenar con el base
            df['BONIFICACIONES'] = 0.0
            df['BENEFICIOS_LABORALES'] = 0.0
            df['DEDUCCIONES'] = 0.0
            df['OBSERVACIONES'] = ""

            # 3. Ordenar columnas para usabilidad
            cols_order = [
                'id_contrato', # NECESARIO para la carga, aunque RRHH no lo toque
                'CODIGO_EMPLEADO', 'NOMBRE_COMPLETO', 'DNI', 'PUESTO', 'TIPO_CONTRATO',
                'ANIO_PROCESO', 'MES_PROCESO',
                'SALARIO_DEVENGADO', 'BONIFICACIONES', 'BENEFICIOS_LABORALES', 'DEDUCCIONES', 'OBSERVACIONES'
            ]
            df = df[cols_order]

            # 4. Exportar a Excel con formato
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Plantilla_Nomina')
                # Aquí podrías agregar lógica de OpenPyXL para bloquear la columna id_contrato si quisieras
            
            return True, f"Plantilla generada exitosamente en: {filepath}"

        except Exception as e:
            return False, f"Error generando plantilla: {e}"
        finally:
            conn.close()

    def process_payroll_import(self, filepath):
        """
        Lee la plantilla llena e inserta/actualiza en nominas_mensuales.
        """
        try:
            df = pd.read_excel(filepath)
            
            # Validar columnas críticas
            required_cols = ['id_contrato', 'ANIO_PROCESO', 'MES_PROCESO', 'SALARIO_DEVENGADO']
            if not all(col in df.columns for col in required_cols):
                return False, "El archivo no tiene el formato correcto (faltan columnas clave)."

            exito = 0
            errores = 0
            
            for index, row in df.iterrows():
                try:
                    # Datos
                    id_c = row['id_contrato']
                    anio = row['ANIO_PROCESO']
                    mes = row['MES_PROCESO']
                    sal = row['SALARIO_DEVENGADO'] if pd.notnull(row['SALARIO_DEVENGADO']) else 0
                    bon = row['BONIFICACIONES'] if pd.notnull(row['BONIFICACIONES']) else 0
                    ben = row['BENEFICIOS_LABORALES'] if pd.notnull(row['BENEFICIOS_LABORALES']) else 0
                    ded = row['DEDUCCIONES'] if pd.notnull(row['DEDUCCIONES']) else 0
                    obs = row['OBSERVACIONES'] if pd.notnull(row['OBSERVACIONES']) else ""

                    # Validación básica
                    if pd.isna(id_c) or pd.isna(anio) or pd.isna(mes):
                        continue # Saltar filas vacías

                    # Lógica de UPSERT (Insertar o Actualizar)
                    # Verificamos si existe
                    if self.dao.exists_payroll(id_c, anio, mes):
                        # Opción A: Actualizar (Recomendado para correcciones)
                        # Necesitamos el id_nomina, lo buscamos rápido
                        # (Podrías optimizar esto en el DAO, pero por ahora:)
                        payroll_rows = self.dao.get_payrolls_by_contract(id_c, anio)
                        # Filtramos en Python (ineficiente si son millones, ok para 500)
                        target_row = next((r for r in payroll_rows if r[2] == mes), None) # r[2] es mes
                        
                        if target_row:
                            self.dao.update_payroll_record(target_row[0], sal, bon, ben, ded, obs)
                    else:
                        # Insertar
                        self.dao.insert_payroll_record(id_c, anio, mes, sal, bon, ben, ded, obs)
                    
                    exito += 1
                except Exception as e:
                    print(f"Error en fila {index}: {e}")
                    errores += 1

            return True, f"Proceso completado. Procesados: {exito}, Errores: {errores}"

        except Exception as e:
            return False, f"Error leyendo archivo: {e}"