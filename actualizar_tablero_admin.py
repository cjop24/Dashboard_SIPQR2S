import os
import urllib.parse
import pandas as pd
from sqlalchemy import create_engine, text, URL
from dotenv import load_dotenv

# Intentar importar streamlit por si el script se ejecuta dentro de la app web
try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

# Cargar credenciales desde el archivo .env local
load_dotenv()

def obtener_engine():
    """
    Crea el motor de conexión a PostgreSQL usando la estructura robusta de SQLAlchemy.
    """
    DB_USER = os.getenv("DB_USER")
    DB_PASS = os.getenv("DB_PASS")
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT", "6543")
    DB_NAME = os.getenv("DB_NAME", "postgres")

    if not DB_USER or not DB_PASS or not DB_HOST:
        print("❌ Error: Faltan credenciales de base de datos en el archivo .env")
        return None

    # Manejo de tipos de contraseña (bytes a str) y sanitización
    if isinstance(DB_PASS, bytes):
        DB_PASS = DB_PASS.decode("utf-8", errors="ignore")

    connection_url = URL.create(
        drivername="postgresql+psycopg2",
        username=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=int(DB_PORT),
        database=DB_NAME,
    )

    return create_engine(
        connection_url,
        connect_args={"client_encoding": "utf8"},
        pool_pre_ping=True,
        pool_recycle=300,
    )

def forzar_actualizacion_administrador():
    """
    Script de consola para el Administrador.
    Verifica las métricas clave en PostgreSQL e invalida la caché si aplica.
    """
    print("🚀 Iniciando verificación de refresco de datos para Administrador...")

    engine = obtener_engine()
    if engine is None:
        return

    try:
        # 1. Conteo total de registros en la vista consolidada
        query_cnt = text('SELECT COUNT(*) AS total FROM "V_SIPQR2S_CONSOLIDADO";')
        
        # 2. Rango de fechas activo
        query_fechas = text('SELECT MIN("fecha_dt") AS min_f, MAX("fecha_dt") AS max_f FROM "V_SIPQR2S_CONSOLIDADO";')
        
        # 3. Verificación de parametrización para HOCEN
        query_hocen = text('SELECT DISTINCT "RASES" FROM "V_SIPQR2S_CONSOLIDADO" WHERE "UNIDAD DE ASIGNACIÓN" LIKE \'%HOCEN%\';')

        with engine.connect() as conn:
            df_cnt = pd.read_sql(query_cnt, con=conn)
            df_fechas = pd.read_sql(query_fechas, con=conn)
            df_hocen = pd.read_sql(query_hocen, con=conn)

        total = df_cnt["total"].iloc[0]
        min_f = df_fechas["min_f"].iloc[0]
        max_f = df_fechas["max_f"].iloc[0]
        rases_hocen = df_hocen["RASES"].tolist() if not df_hocen.empty else ["N/A"]

        print("\n================ RESUMEN DE LA BASE DE DATOS ================")
        print(f"📊 Total Registros en V_SIPQR2S_CONSOLIDADO: {total:,}")
        print(f"📅 Rango de Fechas Activo: {min_f}  --->  {max_f}")
        print(f"🏥 Parametrización RASES para HOCEN: {rases_hocen}")
        print("=============================================================\n")

        # Invalidador de caché si se ejecuta dentro del runtime de Streamlit
        if HAS_STREAMLIT:
            try:
                st.cache_data.clear()
                st.cache_resource.clear()
                print("🧹 Caché interna de Streamlit purgada exitosamente.")
            except Exception:
                pass

        print("✅ Estado de la base de datos validado correctamente.")
        print("👉 Al ejecutar 'git push origin main', la aplicación web en Streamlit Cloud")
        print(f"   detectará el nuevo despliegue y actualizará la consola visual.")

    except Exception as e:
        print(f"❌ Error al consultar la base de datos: {e}")

if __name__ == "__main__":
    forzar_actualizacion_administrador()