import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN Y CONEXIÓN (Neon.tech) - credenciales desde .env
# -----------------------------------------------------------------------------
load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "neondb")

if not DB_USER or not DB_PASS or not DB_HOST:
    raise ValueError("❌ Error: Faltan credenciales de base de datos en el archivo .env")

def cargar_usuarios_mensuales():
    print("🚀 Cargando datos mensuales de usuarios atendidos a Neon...")

    archivo_excel = "USUARIOS_ATENDIDOS_MENSUAL.xlsx"

    if not os.path.exists(archivo_excel):
        print(f"❌ Error: No se encontró el archivo '{archivo_excel}' en la carpeta del proyecto.")
        return

    try:
        df_raw = pd.read_excel(archivo_excel, sheet_name=0, engine="openpyxl", dtype=str)
        print(f"  ✓ Archivo '{archivo_excel}' leído correctamente ({len(df_raw)} filas).")
    except Exception as e:
        print(f"❌ Error al leer el archivo Excel: {e}")
        return

    df_raw.columns = [str(c).strip().upper() for c in df_raw.columns]

    # Acepta ANIO + MES, o una sola columna MES_ANIO ("2026-01")
    if "ANIO" not in df_raw.columns or "MES" not in df_raw.columns:
        if "MES_ANIO" in df_raw.columns:
            fechas = pd.to_datetime(df_raw["MES_ANIO"].astype(str).str.strip(), format="%Y-%m", errors="coerce")
            df_raw["ANIO"] = fechas.dt.year
            df_raw["MES"] = fechas.dt.month
        else:
            print("❌ Error: el Excel debe tener las columnas ANIO y MES (o MES_ANIO).")
            return

    for col in ["UNIDAD", "USUARIOS"]:
        if col not in df_raw.columns:
            print(f"❌ Error: La columna '{col}' no se encuentra en el Excel.")
            return

    registros = []
    for _, fila in df_raw.iterrows():
        unidad = str(fila['UNIDAD']).strip().upper()

        # Ignorar filas vacías o de totales
        if unidad in ['TOTAL GENERAL', 'NAN', '', 'NONE']:
            continue

        val_anio = pd.to_numeric(fila['ANIO'], errors='coerce')
        val_mes = pd.to_numeric(fila['MES'], errors='coerce')
        val_usuarios = pd.to_numeric(fila['USUARIOS'], errors='coerce')

        if pd.notna(val_anio) and pd.notna(val_mes) and pd.notna(val_usuarios):
            registros.append((unidad, int(val_anio), int(val_mes), float(val_usuarios)))

    # Evita el error "ON CONFLICT ... cannot affect row a second time" si el Excel repite (UNIDAD, ANIO, MES)
    registros = list({(u, a, m): (u, a, m, v) for u, a, m, v in registros}.values())

    print(f"  📥 Insertando/actualizando {len(registros)} registros mensuales en Neon...")

    if not registros:
        print("⚠️ No se generaron registros válidos para insertar.")
        return

    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT,
            client_encoding='UTF8'
        )
        cursor = conn.cursor()

        query = """
            INSERT INTO "USUARIOS_ATENDIDOS_MENSUAL" ("UNIDAD", "ANIO", "MES", "USUARIOS")
            VALUES %s
            ON CONFLICT ("UNIDAD", "ANIO", "MES")
            DO UPDATE SET "USUARIOS" = EXCLUDED."USUARIOS";
        """
        execute_values(cursor, query, registros)
        conn.commit()

        cursor.close()
        conn.close()
        print("✅ ¡Carga de usuarios mensuales completada con éxito en Neon!")

    except Exception as e:
        print(f"⚠️ Error al insertar registros en PostgreSQL: {e}")

if __name__ == "__main__":
    cargar_usuarios_mensuales()
