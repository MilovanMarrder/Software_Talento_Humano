import sqlite3
from config.db_connection import DatabaseConnection

class CatalogsDAO:
    def __init__(self):
        self.db = DatabaseConnection()
        self._check_and_migrate_puestos_structure()

    def _check_and_migrate_puestos_structure(self):
        """
        Verifica si cat_puestos tiene id_departamento. Si no, lo crea.
        Esto es necesario para la refactorización arquitectónica.
        """
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            # Truco para ver columnas
            cursor.execute("PRAGMA table_info(cat_puestos)")
            columns = [info[1] for info in cursor.fetchall()]
            
            if "id_departamento" not in columns:
                print("⚠ MIGRACIÓN DETECTADA: Agregando 'id_departamento' a 'cat_puestos'...")
                cursor.execute("ALTER TABLE cat_puestos ADD COLUMN id_departamento INTEGER REFERENCES cat_departamentos(id_departamento)")
                conn.commit()
                print("✅ Migración exitosa. Ahora los puestos están vinculados a departamentos.")
        except Exception as e:
            print(f"Error en migración automática: {e}")
        finally:
            conn.close()

    # --- GENÉRICOS DE LECTURA ---
    def get_departamentos(self):
        return self._get_all("cat_departamentos", "id_departamento", "nombre")

    def get_puestos(self):
        # Versión simple para comboboxes genéricos
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id_puesto, nombre_puesto FROM cat_puestos ORDER BY nombre_puesto")
        rows = cursor.fetchall()
        conn.close()
        return rows

    def get_tipos_contrato(self):
        return self._get_all("cat_tipos_contrato", "id_tipo_contrato", "nombre")


    def get_unidades_produccion(self):
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

    # --- HELPER METHODS ---
    def get_grupos_perc_combo(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id_grupo, codigo || ' - ' || descripcion FROM cat_grupos_perc ORDER BY codigo")
        rows = cursor.fetchall()
        conn.close()
        return rows


    def get_puestos_jefatura_combo(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id_puesto, nombre_puesto FROM cat_puestos WHERE tiene_personal_cargo = 1 ORDER BY nombre_puesto")
        rows = cursor.fetchall()
        conn.close()
        return rows


    # --- PUESTOS ---
    def get_puestos_detailed(self): 
                """
                Retorna datos enriquecidos.
                AHORA SÍ hacemos JOIN con Departamentos para mostrar la realidad.
                """
                conn = self.db.get_connection()
                cursor = conn.cursor()
                query = """
                    SELECT 
                        p.id_puesto,                    -- 0
                        p.nombre_puesto,                -- 1
                        COALESCE(d.nombre, 'Sin Asignar') as depto_nombre, -- 2 
                        CASE WHEN p.tiene_personal_cargo = 1 THEN 'Sí' ELSE 'No' END as es_jefe, -- 3
                        COALESCE(jefe.nombre_puesto, '---') as reporta_a, -- 4
                        COALESCE(gp.codigo || ' - ' || gp.descripcion, '---') as grupo_perc, -- 5
                        
                        -- RAW DATA para edición
                        p.id_departamento,              -- 6 
                        p.tiene_personal_cargo,         -- 7
                        p.id_puesto_jefe,               -- 8
                        p.id_grupo_perc                 -- 9
                    FROM cat_puestos p
                    LEFT JOIN cat_departamentos d ON p.id_departamento = d.id_departamento
                    LEFT JOIN cat_puestos jefe ON p.id_puesto_jefe = jefe.id_puesto
                    LEFT JOIN cat_grupos_perc gp ON p.id_grupo_perc = gp.id_grupo
                    -- CAMBIO AQUÍ: Ordenar estrictamente por nombre del puesto
                    ORDER BY p.nombre_puesto ASC
                """
                cursor.execute(query)
                rows = cursor.fetchall()
                conn.close()
                return rows
        
    # Sobreescritura vital
    get_puestos = get_puestos_detailed 

    def crud_puesto(self, action, id_item=None, nombre=None, 
                    id_depto=None,  # AHORA SÍ SE USA ESTE PARÁMETRO
                    tiene_personal=0, id_jefe=None, id_grupo_perc=None, id_tipo=1):
        
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            
            # Sanitización
            if not id_jefe: id_jefe = None
            if not id_grupo_perc: id_grupo_perc = None
            if not id_depto: id_depto = None # Importante
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
            return False, "Error de Integridad (Probablemente el puesto está en uso)."
        except Exception as e:
            return False, f"Error: {e}"
        finally:
            conn.close()

# --- CRUD CATEGORÍAS INASISTENCIA  ---
    def get_categorias_inasistencia(self):
        return self._get_all("cat_categorias_inasistencia", "id_categoria", "nombre_categoria")

    def get_categorias_combo(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id_categoria, nombre_categoria FROM cat_categorias_inasistencia ORDER BY nombre_categoria")
        rows = cursor.fetchall()
        conn.close()
        return rows

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
            return False, "No se puede eliminar: Existen Tipos de Inasistencia vinculados."
        except Exception as e:
            return False, f"Error: {e}"
        finally:
            conn.close()

    # --- CRUD TIPOS INASISTENCIA (CORREGIDO CON JOIN Y REMUNERADO) ---
    def get_tipos_inasistencia(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        query = """
            SELECT 
                t.id_tipo, t.nombre_tipo, COALESCE(c.nombre_categoria, 'Sin Categoría'), 
                CASE WHEN t.cuenta_afectada = 'ORDINARIA' THEN 'Sí' ELSE 'No' END,
                t.id_categoria, t.cuenta_afectada, t.remunerado
            FROM cat_tipos_inasistencia t
            LEFT JOIN cat_categorias_inasistencia c ON t.id_categoria = c.id_categoria
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
            remunerado = int(remunerado) if remunerado else 0
            if not id_cat: id_cat = 1 
            if action == 'INSERT':
                cursor.execute("INSERT INTO cat_tipos_inasistencia (nombre_tipo, id_categoria, cuenta_afectada, remunerado) VALUES (?, ?, ?, ?)", (nombre, id_cat, cuenta_afectada, remunerado))
            elif action == 'UPDATE':
                cursor.execute("UPDATE cat_tipos_inasistencia SET nombre_tipo=?, id_categoria=?, cuenta_afectada=?, remunerado=? WHERE id_tipo=?", (nombre, id_cat, cuenta_afectada, remunerado, id_item))
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
            return False, "No se puede eliminar: Existen contratos activos."
        except Exception as e:
            return False, f"Error: {e}"
        finally:
            conn.close()


    # --- NUEVO: CRUD DÍAS FESTIVOS ---
    def get_dias_festivos(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id_feriado, fecha, descripcion FROM dias_festivos ORDER BY fecha DESC")
        rows = cursor.fetchall()
        conn.close()
        return rows

    def crud_dias_festivos(self, action, id_item=None, fecha=None, descripcion=None):
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            if action == 'INSERT':
                cursor.execute("INSERT INTO dias_festivos (fecha, descripcion) VALUES (?, ?)", (fecha, descripcion))
            elif action == 'UPDATE':
                cursor.execute("UPDATE dias_festivos SET fecha=?, descripcion=? WHERE id_feriado=?", (fecha, descripcion, id_item))
            elif action == 'DELETE':
                cursor.execute("DELETE FROM dias_festivos WHERE id_feriado=?", (id_item,))
            conn.commit()
            return True, "Operación exitosa"
        except sqlite3.IntegrityError:
            return False, "Error: Ya existe un feriado en esa fecha."
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    # --- MODIFICADO: CRUD JORNADAS (Agregar campo aplica_feriados) ---
    def get_jornadas(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id_jornada, nombre, horas_diarias, 
            CASE WHEN aplica_feriados = 1 THEN 'Sí' ELSE 'No' END as visual_aplica,
            aplica_feriados -- Raw data
            FROM cat_jornadas ORDER BY nombre
        """)
        rows = cursor.fetchall()
        conn.close()
        return rows

    def crud_jornada(self, action, id_item=None, nombre=None, horas=8.0, aplica_feriados=1):
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            aplica_feriados = 1 if aplica_feriados else 0 

            if action == 'INSERT':
                cursor.execute("INSERT INTO cat_jornadas (nombre, horas_diarias, aplica_feriados) VALUES (?, ?, ?)", 
                               (nombre, horas, aplica_feriados))
            elif action == 'UPDATE':
                cursor.execute("UPDATE cat_jornadas SET nombre=?, horas_diarias=?, aplica_feriados=? WHERE id_jornada=?", 
                               (nombre, horas, aplica_feriados, id_item))
            elif action == 'DELETE':
                cursor.execute("DELETE FROM cat_jornadas WHERE id_jornada=?", (id_item,))
            conn.commit()
            return True, "Operación exitosa"
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()
            
# --- CRUD REGLAS VACACIONES (CORREGIDO FINAL) ---
    def get_reglas_vacaciones(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        query = "SELECT id_regla, anios_antiguedad, dias_otorgar FROM cat_reglas_vacaciones ORDER BY anios_antiguedad"
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        return rows

    def crud_regla_vacacion(self, action, id_item=None, anios=None, dias=None):
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            if action == 'INSERT':
                cursor.execute("INSERT INTO cat_reglas_vacaciones (anios_antiguedad, dias_otorgar) VALUES (?, ?)", (anios, dias))
            elif action == 'UPDATE':
                cursor.execute("UPDATE cat_reglas_vacaciones SET anios_antiguedad=?, dias_otorgar=? WHERE id_regla=?", (anios, dias, id_item))
            elif action == 'DELETE':
                cursor.execute("DELETE FROM cat_reglas_vacaciones WHERE id_regla=?", (id_item,))
            conn.commit()
            return True, "Operación exitosa"
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()


    def get_only_vacation_types_combo(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            query = "SELECT id_tipo, nombre_tipo FROM cat_tipos_inasistencia WHERE cuenta_afectada = 'ORDINARIA'"
            cursor.execute(query)
            rows = cursor.fetchall()
            return rows
        finally:
            conn.close()