import sqlite3
from config.db_connection import DatabaseConnection
from logics.vacation_service import VacationService

class ContractDAO:
    def __init__(self):
        self.db = DatabaseConnection()

    # Añadir este método helper dentro de la clase ContractDAO
    def _sync_initial_balance_kardex(self, cursor, id_contrato, fecha_kardex, dias_iniciales):
        """Inserta o actualiza el registro de SALDO_INICIAL en el Kardex"""
        # 1. Verificar si ya existe un saldo inicial
        cursor.execute("""
            SELECT id_movimiento FROM kardex_vacaciones 
            WHERE id_contrato = ? AND tipo_movimiento = 'SALDO_INICIAL'
        """, (id_contrato,))
        row = cursor.fetchone()

        obs = f"Saldo Inicial al corte {fecha_kardex}"
        
        if row:
            # Actualizar existente
            cursor.execute("""
                UPDATE kardex_vacaciones 
                SET dias = ?, fecha_movimiento = ?, observacion = ?
                WHERE id_movimiento = ?
            """, (dias_iniciales, fecha_kardex, obs, row[0]))
        else:
            # Insertar nuevo
            if dias_iniciales > 0: # Solo si hay saldo
                cursor.execute("""
                    INSERT INTO kardex_vacaciones (id_contrato, fecha_movimiento, tipo_movimiento, dias, observacion)
                    VALUES (?, ?, 'SALDO_INICIAL', ?, ?)
                """, (id_contrato, fecha_kardex, dias_iniciales, obs))

# --- MÉTODO HELPER INTERNO ---
    def _calculate_dni_perc(self, cursor, id_empleado, id_tipo_contrato):
        """
        Calcula el DNI PERC basado en la regla de negocio:
        - HMEP -> DNI Limpio
        - OTROS -> DNI + Primera Letra del Tipo Contrato
        """
        # 1. Obtener DNI del empleado
        cursor.execute("SELECT dni FROM empleados WHERE id_empleado = ?", (id_empleado,))
        row_emp = cursor.fetchone()
        dni = row_emp[0] if row_emp else ""
        
        # 2. Obtener Nombre del Tipo de Contrato
        cursor.execute("SELECT nombre FROM cat_tipos_contrato WHERE id_tipo_contrato = ?", (id_tipo_contrato,))
        row_tipo = cursor.fetchone()
        nombre_tipo = row_tipo[0] if row_tipo else ""
        
        # 3. Aplicar Lógica
        nombre_upper = nombre_tipo.upper().strip()
        if "HMEP" in nombre_upper:
            return dni
        else:
            suffix = nombre_upper[0] if nombre_upper else "X"
            return f"{dni}{suffix}"



    def create_contract(self, data_contrato, lista_costos):
        # Abrimos la conexión principal
        conn = self.db.get_connection()
        id_contrato = None
        
        try:
            cursor = conn.cursor()
            
            # 1. DESEMPAQUETADO
            (id_emp, id_puesto, id_depto, id_tipo, id_jornada, 
            f_kardex, s_inicial, f_ini, f_fin, salario) = data_contrato

            # 2. CÁLCULO DE DNI PERC (Regla de negocio automática)
            dni_perc = self._calculate_dni_perc(cursor, id_emp, id_tipo)

            # 3. INSERT DEL CONTRATO
            query = """
                INSERT INTO contratos 
                (id_empleado, id_puesto, id_departamento, id_tipo_contrato, id_jornada, 
                fecha_inicio_kardex, saldo_inicial_vacaciones,
                fecha_inicio, fecha_fin, salario, dni_perc, activo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """
            cursor.execute(query, (id_emp, id_puesto, id_depto, id_tipo, id_jornada, 
                                f_kardex, s_inicial, f_ini, f_fin, salario, dni_perc))
            
            id_contrato = cursor.lastrowid # Capturamos el ID de inmediato

            # 4. INSERT DE DISTRIBUCIÓN DE COSTOS
            for uid, pct in lista_costos:
                cursor.execute("""
                    INSERT INTO distribucion_costos (id_contrato, id_unidad, porcentaje) 
                    VALUES (?, ?, ?)
                """, (id_contrato, uid, pct))
            
            # 5. SINCRONIZACIÓN DE SALDO INICIAL EN KARDEX (Si hay fecha)
            if f_kardex:
                self._sync_initial_balance_kardex(cursor, id_contrato, f_kardex, s_inicial)

            # 6. CIERRE DE TRANSACCIÓN ATÓMICA
            # Guardamos todo lo anterior (Contrato + Costos + Saldo Inicial)
            conn.commit() 
            conn.close() # Cerramos conexión A para liberar el bloqueo de escritura de SQLite

            # 7. LÓGICA PROACTIVA POST-CIERRE
            # Disparamos el cálculo de meses acumulados. 
            # Al estar fuera de la conexión anterior, el Service puede abrir la suya propia sin bloqueos.
            try:
                vac_service = VacationService()
                vac_service.process_monthly_accruals(id_contrato)
                msg_exito = "Contrato creado y saldos proyectados correctamente."
            except Exception as e_acc:
                msg_exito = f"Contrato creado, pero hubo un detalle calculando los meses: {e_acc}"

            return True, msg_exito

        except Exception as e:
            # Si algo falla antes del commit, limpiamos todo (Atomicidad)
            if conn:
                conn.rollback()
                conn.close()
            print(f"DEBUG: Error al crear contrato: {e}")
            return False, f"No se pudo crear el contrato: {e}"

    # --- UPDATE ACTUALIZADO ---
    def update_contract(self, id_contrato, data_contrato, lista_costos):
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            
            # Data recibida desde la vista (Nota: NO trae id_empleado, hay que buscarlo)
            (id_puesto, id_depto, id_tipo, id_jornada, 
             f_kardex, s_inicial, 
             f_ini, f_fin, salario, _id_con_param) = data_contrato
            
            # 1. RECUPERAR ID_EMPLEADO (Para recalcular dni_perc si cambió el tipo)
            cursor.execute("SELECT id_empleado FROM contratos WHERE id_contrato = ?", (id_contrato,))
            row_emp = cursor.fetchone()
            if not row_emp: raise Exception("Contrato no encontrado")
            id_emp = row_emp[0]

            # 2. RECALCULAR DNI PERC
            dni_perc = self._calculate_dni_perc(cursor, id_emp, id_tipo)

            query = """
                UPDATE contratos 
                SET id_puesto=?, id_departamento=?, id_tipo_contrato=?, id_jornada=?,
                    fecha_inicio_kardex=?, saldo_inicial_vacaciones=?,
                    fecha_inicio=?, fecha_fin=?, salario=?,
                    dni_perc=?   -- <-- Actualizamos esto
                WHERE id_contrato=?
            """
            cursor.execute(query, (id_puesto, id_depto, id_tipo, id_jornada, f_kardex, s_inicial, 
                                   f_ini, f_fin, salario, dni_perc, id_contrato))
            
            # Costos...
            cursor.execute("DELETE FROM distribucion_costos WHERE id_contrato=?", (id_contrato,))
            for uid, pct in lista_costos:
                cursor.execute("INSERT INTO distribucion_costos (id_contrato, id_unidad, porcentaje) VALUES (?, ?, ?)", (id_contrato, uid, pct))

            # Sincronizar Kardex
            if f_kardex:
                self._sync_initial_balance_kardex(cursor, id_contrato, f_kardex, s_inicial)

            conn.commit()
            return True, "Actualizado."
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()



    def delete_contract(self, id_contrato):
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            # Gracias al ON DELETE CASCADE, esto borrará automáticamente:
            # - Filas en distribucion_costos
            # - Filas en kardex_vacaciones
            # - Filas en inasistencias
            cursor.execute("DELETE FROM contratos WHERE id_contrato = ?", (id_contrato,))
            
            conn.commit()
            return True, "Contrato y todos sus registros vinculados eliminados correctamente."
        except Exception as e:
            conn.rollback()
            return False, f"Error al eliminar: {e}"
        finally:
            conn.close()
            
    def get_employee_by_code(self, codigo):
        """Busca ID y Nombre de empleado por su código"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id_empleado, nombres, apellidos FROM empleados WHERE codigo = ? AND activo = 1", (codigo,))
        row = cursor.fetchone()
        conn.close()
        return row
    


    def get_all_contracts(self):
        """Obtiene lista resumen para la tabla inferior"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        query = """
        SELECT 
            c.id_contrato, 
            e.codigo || ' - ' || e.nombres || ' ' || e.apellidos,
            p.nombre_puesto,
            tc.nombre,
            c.fecha_inicio
        FROM contratos c
        JOIN empleados e ON c.id_empleado = e.id_empleado
        JOIN cat_puestos p ON c.id_puesto = p.id_puesto
        JOIN cat_tipos_contrato tc ON c.id_tipo_contrato = tc.id_tipo_contrato
        WHERE c.activo = 1
        ORDER BY c.id_contrato DESC
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        return rows

    def get_contract_details(self, id_contrato):
        """Recupera toda la info de un contrato y sus costos para editar"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # 1. Datos Contrato
        cursor.execute("SELECT * FROM contratos WHERE id_contrato = ?", (id_contrato,))
        contrato = cursor.fetchone()
        
        # 2. Datos Empleado (Para mostrar el nombre en el label)
        cursor.execute("""
            SELECT e.id_empleado, e.codigo, e.nombres, e.apellidos 
            FROM empleados e 
            JOIN contratos c ON e.id_empleado = c.id_empleado 
            WHERE c.id_contrato = ?
        """, (id_contrato,))
        empleado = cursor.fetchone()
        
        # 3. Distribución Costos (Join para traer nombre de unidad)
        cursor.execute("""
            SELECT dc.id_unidad, up.nombre_up, dc.porcentaje
            FROM distribucion_costos dc
            JOIN cat_unidades_produccion up ON dc.id_unidad = up.id_unidad
            WHERE dc.id_contrato = ?
        """, (id_contrato,))
        costos = cursor.fetchall()
        
        conn.close()
        return contrato, empleado, costos
    
# ... (métodos anteriores)

    def search_contracts(self, term):
        """
        Busca contratos por Nombre de Empleado, Código, DNI o Puesto.
        Optimizado para el Selector.
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()
        search_term = f"%{term}%"
        
        query = """
        SELECT 
            c.id_contrato, 
            e.codigo || ' - ' || e.nombres || ' ' || e.apellidos as empleado,
            p.nombre_puesto,
            tc.nombre as tipo,
            c.fecha_inicio,
            CASE WHEN c.activo = 1 THEN 'Activo' ELSE 'Inactivo' END as estado
        FROM contratos c
        JOIN empleados e ON c.id_empleado = e.id_empleado
        JOIN cat_puestos p ON c.id_puesto = p.id_puesto
        JOIN cat_tipos_contrato tc ON c.id_tipo_contrato = tc.id_tipo_contrato
        WHERE 
            e.nombres LIKE ? OR 
            e.apellidos LIKE ? OR 
            e.codigo LIKE ? OR 
            e.dni LIKE ? OR
            p.nombre_puesto LIKE ?
        ORDER BY c.activo DESC, c.fecha_inicio DESC
        LIMIT 50 -- Límite de seguridad para no saturar UI
        """
        # Repetimos el término para cada ?
        params = (search_term, search_term, search_term, search_term, search_term)
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return rows