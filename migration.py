import sqlite3
from config import settings

def run_migrations():
    print("--- INICIANDO MIGRACIÓN DE BASE DE DATOS ---")
    
    # Conexión directa (sin pasar por el Singleton para este script admin)
    db_path = settings.DB_PATH
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. CREAR TABLA CAT_JORNADAS
        print("1. Verificando tabla cat_jornadas...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cat_jornadas (
                id_jornada INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                horas_diarias REAL NOT NULL
            )
        """)
        # Insertar jornada default si está vacía
        cursor.execute("SELECT count(*) FROM cat_jornadas")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO cat_jornadas (nombre, horas_diarias) VALUES ('Diurna (8h)', 8.0)")
            cursor.execute("INSERT INTO cat_jornadas (nombre, horas_diarias) VALUES ('Mixta (7h)', 7.0)")
            cursor.execute("INSERT INTO cat_jornadas (nombre, horas_diarias) VALUES ('Nocturna (6h)', 6.0)")
            print("   -> Datos semilla de jornadas insertados.")

        # 2. MODIFICAR TABLA CONTRATOS (Agregar FK id_jornada)
        print("2. Verificando esquema de Contratos...")
        cursor.execute("PRAGMA table_info(contratos)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'id_jornada' not in columns:
            print("   -> Agregando columna 'id_jornada' a Contratos...")
            # Default 1 (Diurna) para contratos existentes
            cursor.execute("ALTER TABLE contratos ADD COLUMN id_jornada INTEGER DEFAULT 1 REFERENCES cat_jornadas(id_jornada)")
        else:
            print("   -> Columna 'id_jornada' ya existe.")

        # 3. MODIFICAR TABLA INASISTENCIAS (Soporte por horas)
        print("3. Verificando esquema de Inasistencias...")
        cursor.execute("PRAGMA table_info(inasistencias)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'es_por_horas' not in columns:
            print("   -> Agregando columnas de tiempo a Inasistencias...")
            cursor.execute("ALTER TABLE inasistencias ADD COLUMN es_por_horas INTEGER DEFAULT 0")
            cursor.execute("ALTER TABLE inasistencias ADD COLUMN hora_inicio TEXT DEFAULT '08:00'")
            cursor.execute("ALTER TABLE inasistencias ADD COLUMN hora_fin TEXT DEFAULT '16:00'")
        else:
            print("   -> Columnas de tiempo ya existen.")

        # 4. CREAR TABLA CAT_REGLAS_VACACIONES (Matriz de Antigüedad)
        print("4. Verificando tabla cat_reglas_vacaciones...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cat_reglas_vacaciones (
                id_regla INTEGER PRIMARY KEY AUTOINCREMENT,
                id_tipo_inasistencia INTEGER NOT NULL, -- FK a "Vacaciones Ordinarias", etc.
                anios_antiguedad INTEGER NOT NULL,     -- Año 1, Año 2...
                dias_otorgar INTEGER NOT NULL,         -- 12, 15, etc.
                FOREIGN KEY(id_tipo_inasistencia) REFERENCES cat_tipos_inasistencia(id_tipo)
            )
        """)

        # 5. CREAR KARDEX DE VACACIONES (Mayor Contable)
        print("5. Verificando tabla kardex_vacaciones...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kardex_vacaciones (
                id_movimiento INTEGER PRIMARY KEY AUTOINCREMENT,
                id_contrato INTEGER NOT NULL,
                fecha_movimiento TEXT DEFAULT CURRENT_DATE,
                tipo_movimiento TEXT NOT NULL, -- 'SALDO_INICIAL', 'ACUMULACION_MENSUAL', 'GOCE', 'AJUSTE'
                dias REAL NOT NULL,            -- Positivo suma (Haber), Negativo resta (Debe)
                saldo_snapshot REAL,           -- Saldo después del movimiento (para consultas rápidas)
                id_referencia INTEGER,         -- ID de inasistencia (si es goce)
                observacion TEXT,
                FOREIGN KEY(id_contrato) REFERENCES contratos(id_contrato)
            )
        """)

        # 6. Actualizar CAT_TIPOS_INASISTENCIA (Flag descuenta)
        # Esto ya lo hicimos manualmente antes, pero el script asegura consistencia
        print("6. Verificando flags en tipos de inasistencia...")
        cursor.execute("PRAGMA table_info(cat_tipos_inasistencia)")
        cols_cat = [info[1] for info in cursor.fetchall()]
        if 'descuenta_vacaciones' not in cols_cat:
             cursor.execute("ALTER TABLE cat_tipos_inasistencia ADD COLUMN descuenta_vacaciones INTEGER DEFAULT 0")

                # 7. ACTUALIZACIÓN CONTRATOS (Campos para Vacaciones)
        print("7. Agregando campos de Vacaciones a Contratos...")
        cursor.execute("PRAGMA table_info(contratos)")
        cols_con = [info[1] for info in cursor.fetchall()]
        
        if 'saldo_inicial_vacaciones' not in cols_con:
            cursor.execute("ALTER TABLE contratos ADD COLUMN saldo_inicial_vacaciones REAL DEFAULT 0.0")
            print("   -> Columna 'saldo_inicial_vacaciones' agregada.")
            
        if 'fecha_inicio_kardex' not in cols_con:
            # Por defecto, la fecha de inicio del kardex podría ser la fecha de inicio del contrato
            cursor.execute("ALTER TABLE contratos ADD COLUMN fecha_inicio_kardex TEXT") 
            print("   -> Columna 'fecha_inicio_kardex' agregada.")

        conn.commit()
        print("\n--- MIGRACIÓN COMPLETADA EXITOSAMENTE ---")

    except Exception as e:
        conn.rollback()
        print(f"\n!!! ERROR CRÍTICO EN MIGRACIÓN: {e}")
    finally:
        conn.close()

# migrations.py (Agregar al final o ejecutar un script nuevo)
import sqlite3
from config import settings

def run_new_migrations():
    print("--- APLICANDO MIGRACIÓN: DOBLE CONTABILIDAD ---")
    conn = sqlite3.connect(settings.DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. Modificar KARDEX para soportar tipos de cuenta (Ordinaria vs Profiláctica)
        cursor.execute("PRAGMA table_info(kardex_vacaciones)")
        cols = [c[1] for c in cursor.fetchall()]
        if 'cuenta_tipo' not in cols:
            print("-> Agregando 'cuenta_tipo' al Kardex...")
            cursor.execute("ALTER TABLE kardex_vacaciones ADD COLUMN cuenta_tipo TEXT DEFAULT 'ORDINARIA'")
        
        # 2. Modificar CONTRATOS para saldo inicial de profilácticas
        cursor.execute("PRAGMA table_info(contratos)")
        cols_con = [c[1] for c in cursor.fetchall()]
        if 'saldo_inicial_profilacticas' not in cols_con:
            print("-> Agregando 'saldo_inicial_profilacticas' a Contratos...")
            cursor.execute("ALTER TABLE contratos ADD COLUMN saldo_inicial_profilacticas REAL DEFAULT 0.0")

        # 3. Modificar TIPOS DE INASISTENCIA para saber qué cuenta afectan
        # Antes usábamos "descuenta_vacaciones" (0/1). Ahora necesitamos más detalle.
        cursor.execute("PRAGMA table_info(cat_tipos_inasistencia)")
        cols_cat = [c[1] for c in cursor.fetchall()]
        
        if 'cuenta_afectada' not in cols_cat:
            print("-> Actualizando lógica de tipos de inasistencia...")
            cursor.execute("ALTER TABLE cat_tipos_inasistencia ADD COLUMN cuenta_afectada TEXT DEFAULT 'NINGUNA'")
            
            # Migrar datos viejos: Si descuenta_vacaciones era 1, ahora es 'ORDINARIA'
            cursor.execute("UPDATE cat_tipos_inasistencia SET cuenta_afectada = 'ORDINARIA' WHERE descuenta_vacaciones = 1")
            
            # (Opcional) Podemos eliminar la columna vieja descuenta_vacaciones en SQLite es complejo, 
            # así que simplemente la ignoraremos de ahora en adelante.

        conn.commit()
        print("--- MIGRACIÓN COMPLETADA ---")
        
    except Exception as e:
        conn.rollback()
        print(f"!!! ERROR: {e}")
    finally:
        conn.close()

import sqlite3

def apply_perc_migrations():
    conn = sqlite3.connect('rrhh.db') # Ajusta la ruta si es necesario
    cursor = conn.cursor()
    
    print("--- INICIANDO MIGRACIÓN PERC INTEGRAL ---")

    try:
        # 1. TABLA CATÁLOGO GRUPOS PERC (Los 14 códigos)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cat_grupos_perc (
                id_grupo INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT NOT NULL,      -- Ej: '00102'
                descripcion TEXT NOT NULL  -- Ej: 'MÉDICO ESPECIALISTA'
            )
        """)
        
        # Insertar datos semilla (Si está vacía)
        cursor.execute("SELECT count(*) FROM cat_grupos_perc")
        if cursor.fetchone()[0] == 0:
            print("-> Insertando códigos PERC semilla...")
            datos = [
                ('00102', 'MÉDICO ESPECIALISTA'), ('00103', 'MÉDICO GENERAL'),
                ('00203', 'AUXILIAR DE ENFERMERÍA'), ('00209', 'ENFERMERA'),
                ('00304', 'PSICÓLOGO'), ('00305', 'ODONTÓLOGO'),
                ('00309', 'QUÍMICO FARMACÉUTICO'), ('00324', 'MICROBIÓLOGO'),
                ('00409', 'TÉCNICO EN LABORATORIO'), ('00410', 'TÉCNICO EN ANESTESIA'),
                ('00701', 'PERSONAL ADMINISTRATIVO'), ('00708', 'TRABAJADOR SOCIAL'),
                ('00736', 'ASESOR LEGAL'), ('00818', 'OTROS')
            ]
            cursor.executemany("INSERT INTO cat_grupos_perc (codigo, descripcion) VALUES (?,?)", datos)

        # 2. COLUMNA EN PUESTOS (Vincular Puesto -> Grupo PERC)
        cursor.execute("PRAGMA table_info(cat_puestos)")
        cols_puesto = [c[1] for c in cursor.fetchall()]
        if 'id_grupo_perc' not in cols_puesto:
            print("-> Agregando id_grupo_perc a cat_puestos...")
            cursor.execute("ALTER TABLE cat_puestos ADD COLUMN id_grupo_perc INTEGER REFERENCES cat_grupos_perc(id_grupo)")

        # 3. COLUMNA DNI_PERC EN CONTRATOS (La clave del éxito)
        cursor.execute("PRAGMA table_info(contratos)")
        cols_contrato = [c[1] for c in cursor.fetchall()]
        if 'dni_perc' not in cols_contrato:
            print("-> Agregando dni_perc a contratos...")
            cursor.execute("ALTER TABLE contratos ADD COLUMN dni_perc TEXT")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_dni_perc ON contratos(dni_perc)")

        # 4. TABLA NOMINA VARIABLES (Para cargar el Excel de Bonos)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nomina_variables_mensual (
                id_variable INTEGER PRIMARY KEY AUTOINCREMENT,
                id_contrato INTEGER NOT NULL,
                dni_perc_snapshot TEXT, -- Guardamos copia del DNI usado para auditoría
                periodo TEXT NOT NULL,  -- '2025-01'
                monto REAL DEFAULT 0.0,
                FOREIGN KEY(id_contrato) REFERENCES contratos(id_contrato)
            )
        """)
        
        conn.commit()
        print("--- MIGRACIÓN EXITOSA ---")
        
    except Exception as e:
        conn.rollback()
        print(f"!!! ERROR: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    apply_perc_migrations()