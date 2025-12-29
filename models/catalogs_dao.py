import sqlite3
from config.db_connection import DatabaseConnection

class CatalogsDAO:
    def __init__(self):
        self.db = DatabaseConnection()

    # --- GENÉRICOS DE LECTURA ---
    def get_departamentos(self):
        return self._get_all("cat_departamentos", "id_departamento", "nombre") # Retorna (id, nombre, codigo)

    def get_puestos(self):
        # Necesitamos un join o selección específica para mostrar datos ricos
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id_puesto, nombre_puesto FROM cat_puestos ORDER BY nombre_puesto")
        rows = cursor.fetchall()
        conn.close()
        return rows

    def get_tipos_contrato(self):
        return self._get_all("cat_tipos_contrato", "id_tipo_contrato", "nombre")

    def get_unidades_produccion(self):
        # Retorna (id, nombre_up, codigo_up)
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id_unidad, nombre_up, codigo_up FROM cat_unidades_produccion ORDER BY nombre_up")
        rows = cursor.fetchall()
        conn.close()
        return rows

    def _get_all(self, table, id_col, sort_col):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            # Nota: SELECT * asume orden de columnas. 
            # Para deptos: id, nombre, codigo_interno
            cursor.execute(f"SELECT * FROM {table} ORDER BY {sort_col}")
            return cursor.fetchall()
        finally:
            conn.close()

    # --- CRUD DEPARTAMENTOS ---
    def crud_departamento(self, action, id_item=None, nombre=None, codigo=None):
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            if action == 'INSERT':
                cursor.execute("INSERT INTO cat_departamentos (nombre, codigo_interno) VALUES (?, ?)", (nombre, codigo))
            elif action == 'UPDATE':
                cursor.execute("UPDATE cat_departamentos SET nombre=?, codigo_interno=? WHERE id_departamento=?", (nombre, codigo, id_item))
            elif action == 'DELETE':
                cursor.execute("DELETE FROM cat_departamentos WHERE id_departamento=?", (id_item,))
            conn.commit()
            return True, "Operación exitosa"
        except sqlite3.IntegrityError as e:
            return False, f"Error de integridad (¿Registro en uso?): {e}"
        except Exception as e:
            return False, f"Error: {e}"
        finally:
            conn.close()

    # --- CRUD UNIDADES PRODUCCION ---
    def crud_unidad(self, action, id_item=None, nombre=None, codigo=None):
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            if action == 'INSERT':
                cursor.execute("INSERT INTO cat_unidades_produccion (nombre_up, codigo_up) VALUES (?, ?)", (nombre, codigo))
            elif action == 'UPDATE':
                cursor.execute("UPDATE cat_unidades_produccion SET nombre_up=?, codigo_up=? WHERE id_unidad=?", (nombre, codigo, id_item))
            elif action == 'DELETE':
                cursor.execute("DELETE FROM cat_unidades_produccion WHERE id_unidad=?", (id_item,))
            conn.commit()
            return True, "Operación exitosa"
        except sqlite3.IntegrityError:
            return False, "No se puede eliminar: La unidad tiene costos asociados en contratos."
        except Exception as e:
            return False, f"Error: {e}"
        finally:
            conn.close()

# ... (Dentro de CatalogsDAO) ...

    # --- NUEVOS MÉTODOS HELPER ---
    
    def get_grupos_perc_combo(self):
        """Retorna (id, codigo - descripcion) para el combobox"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id_grupo, codigo || ' - ' || descripcion FROM cat_grupos_perc ORDER BY codigo")
        rows = cursor.fetchall()
        conn.close()
        return rows

    def get_puestos_jefatura_combo(self):
        """Retorna solo los puestos marcados como jefatura"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        # Traemos todos los puestos que tienen personal a cargo
        cursor.execute("SELECT id_puesto, nombre_puesto FROM cat_puestos WHERE tiene_personal_cargo = 1 ORDER BY nombre_puesto")
        rows = cursor.fetchall()
        conn.close()
        return rows

    # PUESTOS
    def get_puestos(self):
        """
        Retorna datos enriquecidos.
        Orden Visual: 
          0.ID, 
          1.Nombre, 
          2.Departamento (NUEVO), 
          3.¿Es Jefe?, 
          4.Reporta A, 
          5.Grupo PERC
        
        Datos Raw (Indices ocultos para edición):
          6. id_departamento (NUEVO)
          7. tiene_personal_cargo
          8. id_puesto_jefe
          9. id_grupo_perc
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()
        query = """
            SELECT 
                p.id_puesto, 
                p.nombre_puesto,
                COALESCE(d.nombre, '---') as depto_nombre, -- Visual
                CASE WHEN p.tiene_personal_cargo = 1 THEN 'Sí' ELSE 'No' END as es_jefe,
                COALESCE(jefe.nombre_puesto, '---') as reporta_a,
                COALESCE(gp.codigo || ' - ' || gp.descripcion, '---') as grupo_perc,
                
                -- RAW DATA
                p.id_departamento,      -- Index 6
                p.tiene_personal_cargo, -- Index 7
                p.id_puesto_jefe,       -- Index 8
                p.id_grupo_perc         -- Index 9
            FROM cat_puestos p
            LEFT JOIN cat_departamentos d ON p.id_departamento = d.id_departamento
            LEFT JOIN cat_puestos jefe ON p.id_puesto_jefe = jefe.id_puesto
            LEFT JOIN cat_grupos_perc gp ON p.id_grupo_perc = gp.id_grupo
            ORDER BY p.nombre_puesto
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        return rows

    def crud_puesto(self, action, id_item=None, nombre=None, 
                    id_depto=None,  # NUEVO PARAM
                    tiene_personal=0, id_jefe=None, id_grupo_perc=None, id_tipo=1):
        
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            
            # Sanitización de Nulos
            if not id_jefe: id_jefe = None
            if not id_grupo_perc: id_grupo_perc = None
            if not id_depto: id_depto = None # <-- Importante
            tiene_personal = 1 if tiene_personal else 0

            if action == 'INSERT':
                cursor.execute("""
                    INSERT INTO cat_puestos 
                    (nombre_puesto, id_departamento, tiene_personal_cargo, id_puesto_jefe, id_grupo_perc, id_tipo_puesto) 
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (nombre, id_depto, tiene_personal, id_jefe, id_grupo_perc, 1))
                
            elif action == 'UPDATE':
                if id_jefe and id_item and int(id_jefe) == int(id_item):
                    return False, "Referencia circular en Jefatura."

                cursor.execute("""
                    UPDATE cat_puestos 
                    SET nombre_puesto=?, id_departamento=?, tiene_personal_cargo=?, id_puesto_jefe=?, id_grupo_perc=? 
                    WHERE id_puesto=?
                """, (nombre, id_depto, tiene_personal, id_jefe, id_grupo_perc, id_item))
                
            elif action == 'DELETE':
                cursor.execute("DELETE FROM cat_puestos WHERE id_puesto=?", (id_item,))
            
            conn.commit()
            return True, "Operación exitosa"
        except sqlite3.IntegrityError:
            return False, "Error de Integridad."
        except Exception as e:
            return False, f"Error: {e}"
        finally:
            conn.close()

# --- NUEVO: CRUD CATEGORÍAS INASISTENCIA (MACRO) ---
    def get_categorias_inasistencia(self):
        # Retorna: (id, nombre)
        return self._get_all("cat_categorias_inasistencia", "id_categoria", "nombre_categoria")

    def crud_categoria_inasistencia(self, action, id_item=None, nombre=None):
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            if action == 'INSERT':
                cursor.execute("INSERT INTO cat_categorias_inasistencia (nombre_categoria) VALUES (?)", (nombre,))
            elif action == 'UPDATE':
                cursor.execute("UPDATE cat_categorias_inasistencia SET nombre_categoria=? WHERE id_categoria=?", (nombre, id_item))
            elif action == 'DELETE':
                cursor.execute("DELETE FROM cat_categorias_inasistencia WHERE id_categoria=?", (id_item,))
            conn.commit()
            return True, "Operación exitosa"
        except sqlite3.IntegrityError:
            return False, "No se puede eliminar: Hay tipos de falta vinculados a esta categoría."
        except Exception as e:
            return False, f"Error: {e}"
        finally:
            conn.close()


    # --- CRUD TIPOS INASISTENCIA (SIMPLIFICADO) ---
    def get_tipos_inasistencia(self):
        # Retorna datos para la tabla y el formulario
        conn = self.db.get_connection()
        cursor = conn.cursor()
        # Traemos 'cuenta_afectada' que ya existe en la BD por la migración
        query = """
            SELECT 
                t.id_tipo, 
                t.nombre_tipo, 
                c.nombre_categoria,
                CASE 
                    WHEN t.cuenta_afectada = 'ORDINARIA' THEN 'Sí' 
                    ELSE 'No' 
                END as descuenta_saldo, -- Visualmente mostramos Sí/No
                t.id_categoria,
                t.cuenta_afectada       -- Raw para el formulario
            FROM cat_tipos_inasistencia t
            JOIN cat_categorias_inasistencia c ON t.id_categoria = c.id_categoria
            ORDER BY c.nombre_categoria, t.nombre_tipo
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        return rows

    def crud_tipo_inasistencia(self, action, id_item=None, nombre=None, id_cat=None, cuenta_afectada='NINGUNA', remunerado=0):
            conn = self.db.get_connection()
            try:
                cursor = conn.cursor()
                
                # Asegurar que remunerado sea 0 o 1 (SQLite no tiene bool nativo estricto)
                remunerado = int(remunerado) if remunerado else 0

                if action == 'INSERT':
                    cursor.execute("""
                        INSERT INTO cat_tipos_inasistencia (nombre_tipo, id_categoria, cuenta_afectada, remunerado) 
                        VALUES (?, ?, ?, ?)
                    """, (nombre, id_cat, cuenta_afectada, remunerado))
                
                elif action == 'UPDATE':
                    cursor.execute("""
                        UPDATE cat_tipos_inasistencia 
                        SET nombre_tipo=?, id_categoria=?, cuenta_afectada=?, remunerado=? 
                        WHERE id_tipo=?
                    """, (nombre, id_cat, cuenta_afectada, remunerado, id_item))
                
                elif action == 'DELETE':
                    cursor.execute("DELETE FROM cat_tipos_inasistencia WHERE id_tipo=?", (id_item,))
                
                conn.commit()
                return True, "Operación exitosa"
            except Exception as e:
                return False, f"Error: {e}"
            finally:
                conn.close()

    # --- CRUD TIPOS DE CONTRATO ---
    def crud_tipo_contrato(self, action, id_item=None, nombre=None):
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            if action == 'INSERT':
                cursor.execute("INSERT INTO cat_tipos_contrato (nombre) VALUES (?)", (nombre,))
            elif action == 'UPDATE':
                cursor.execute("UPDATE cat_tipos_contrato SET nombre=? WHERE id_tipo_contrato=?", (nombre, id_item))
            elif action == 'DELETE':
                cursor.execute("DELETE FROM cat_tipos_contrato WHERE id_tipo_contrato=?", (id_item,))
            conn.commit()
            return True, "Operación exitosa"
        except sqlite3.IntegrityError:
            return False, "No se puede eliminar: Existen contratos activos bajo esta modalidad."
        except Exception as e:
            return False, f"Error: {e}"
        finally:
            conn.close()


    # --- CRUD JORNADAS ---
    def get_jornadas(self):
        # (id, nombre, horas)
        return self._get_all("cat_jornadas", "id_jornada", "nombre")

    def crud_jornada(self, action, id_item=None, nombre=None, horas=8.0):
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            if action == 'INSERT':
                cursor.execute("INSERT INTO cat_jornadas (nombre, horas_diarias) VALUES (?, ?)", (nombre, horas))
            elif action == 'UPDATE':
                cursor.execute("UPDATE cat_jornadas SET nombre=?, horas_diarias=? WHERE id_jornada=?", (nombre, horas, id_item))
            elif action == 'DELETE':
                cursor.execute("DELETE FROM cat_jornadas WHERE id_jornada=?", (id_item,))
            conn.commit()
            return True, "Operación exitosa"
        except sqlite3.IntegrityError:
            return False, "No se puede eliminar: Jornada asignada a contratos."
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    # --- CRUD REGLAS VACACIONES ---
    def get_reglas_vacaciones(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        query = """
            SELECT 
                r.id_regla, 
                ti.nombre_tipo || ' (' || c.nombre_categoria || ')',
                r.anios_antiguedad,
                r.dias_otorgar,
                r.id_tipo_inasistencia -- Raw para edición
            FROM cat_reglas_vacaciones r
            JOIN cat_tipos_inasistencia ti ON r.id_tipo_inasistencia = ti.id_tipo
            JOIN cat_categorias_inasistencia c ON ti.id_categoria = c.id_categoria
            ORDER BY ti.nombre_tipo, r.anios_antiguedad
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        return rows

    def crud_regla_vacacion(self, action, id_item=None, id_tipo_inasistencia=None, anios=None, dias=None):
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            if action == 'INSERT':
                cursor.execute("INSERT INTO cat_reglas_vacaciones (id_tipo_inasistencia, anios_antiguedad, dias_otorgar) VALUES (?, ?, ?)", 
                               (id_tipo_inasistencia, anios, dias))
            elif action == 'UPDATE':
                cursor.execute("UPDATE cat_reglas_vacaciones SET id_tipo_inasistencia=?, anios_antiguedad=?, dias_otorgar=? WHERE id_regla=?", 
                               (id_tipo_inasistencia, anios, dias, id_item))
            elif action == 'DELETE':
                cursor.execute("DELETE FROM cat_reglas_vacaciones WHERE id_regla=?", (id_item,))
            conn.commit()
            return True, "Operación exitosa"
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()


    def get_only_vacation_types_combo(self):
        """Retorna los tipos de inasistencia que afectan el saldo de vacaciones"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            # Usamos 'cuenta_afectada' que es el estándar que definimos para el Kardex
            query = "SELECT id_tipo, nombre_tipo FROM cat_tipos_inasistencia WHERE cuenta_afectada = 'ORDINARIA'"
            cursor.execute(query)
            rows = cursor.fetchall()
            return rows
        finally:
            conn.close()