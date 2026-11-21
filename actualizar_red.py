import os
import re
import unicodedata
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "6543")
DB_NAME = os.getenv("DB_NAME", "neondb")

if not DB_USER or not DB_PASS or not DB_HOST:
    raise ValueError("❌ Error: Faltan credenciales de base de datos en el archivo .env")


def obtener_conexion_psycopg2():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT,
        client_encoding='UTF8'
    )


def seleccionar_archivo_excel():
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    archivo = filedialog.askopenfilename(
        title="Selecciona el Excel con la columna Red",
        filetypes=[("Archivos de Excel", "*.xlsx *.xls"), ("Todos los archivos", "*.*")]
    )
    return archivo


def normalizar_red(valor):
    """Normaliza el valor de Red: Red Propia / Red Externa / vacío."""
    if pd.isna(valor) or not str(valor).strip():
        return ""
    s = str(valor).strip().upper()
    if "PROPIA" in s:
        return "Red Propia"
    elif "EXTERNA" in s:
        return "Red Externa"
    return ""


def actualizar_columna_red():
    print("🚀 Iniciando actualización de la columna 'Red' desde Excel...")
    archivo_excel = seleccionar_archivo_excel()
    if not archivo_excel:
        print("❌ Operación cancelada.")
        return
    print(f"📁 Archivo: {os.path.basename(archivo_excel)}")

    try:
        df = pd.read_excel(
            archivo_excel,
            dtype=str,
            engine="openpyxl",
            engine_kwargs={"read_only": True, "data_only": True}
        )
        print(f"  ✓ Registros en el Excel: {len(df)}")
    except Exception as e:
        print(f"❌ Error al leer el Excel: {e}")
        return

    df.columns = [str(col).strip() for col in df.columns]

    # Validar que existan las columnas necesarias
    if "Consecutivo Ticket" not in df.columns:
        print("❌ El Excel no tiene la columna 'Consecutivo Ticket'.")
        return
    if "Red" not in df.columns:
        print("❌ El Excel no tiene la columna 'Red'.")
        return

    # Construir pares (Consecutivo Ticket, Red) SOLO donde Red tiene valor
    df["Consecutivo Ticket"] = df["Consecutivo Ticket"].astype(str).str.strip()
    df["Red"] = df["Red"].apply(normalizar_red)
    df_valido = df[df["Red"] != ""].copy()
    df_valido = df_valido.drop_duplicates(subset=["Consecutivo Ticket"])

    print(f"  📝 Registros con valor de Red para actualizar: {len(df_valido)}")
    if df_valido.empty:
        print("⚠️ No hay valores de Red en el Excel. Nada que actualizar.")
        return

    conn = obtener_conexion_psycopg2()
    cursor = conn.cursor()

    try:
        # 1. UPDATE masivo en TICKETS_SIPQR2S
        print("  🔄 Actualizando columna 'Red' en TICKETS_SIPQR2S...")
        valores = [tuple(x) for x in df_valido[["Consecutivo Ticket", "Red"]].to_numpy()]
        update_sql = '''
            UPDATE "TICKETS_SIPQR2S" AS t
            SET "Red" = v."Red"
            FROM (VALUES %s) AS v("Consecutivo Ticket", "Red")
            WHERE t."Consecutivo Ticket" = v."Consecutivo Ticket"
              AND (t."Red" IS NULL OR t."Red" = '' OR t."Red" <> v."Red");
        '''
        execute_values(cursor, update_sql, valores, page_size=5000)
        tickets_actualizados = cursor.rowcount
        print(f"  ✓ TICKETS_SIPQR2S actualizados: {tickets_actualizados}")

        # 2. PROPAGAR a COMPLEMENTOS_TICKETS_SIPQR2S desde TICKETS_SIPQR2S
        print("  🔄 Propagando 'Red' a COMPLEMENTOS_TICKETS_SIPQR2S...")
        propagate_sql = '''
            UPDATE "COMPLEMENTOS_TICKETS_SIPQR2S" AS c
            SET "Red" = t."Red"
            FROM "TICKETS_SIPQR2S" AS t
            WHERE c."Consecutivo Ticket" = t."Consecutivo Ticket"
              AND t."Red" IS NOT NULL AND t."Red" <> ''
              AND (c."Red" IS NULL OR c."Red" = '' OR c."Red" <> t."Red");
        '''
        cursor.execute(propagate_sql)
        comp_actualizados = cursor.rowcount
        print(f"  ✓ COMPLEMENTOS actualizados: {comp_actualizados}")

        conn.commit()
        print("✅ ¡Actualización de 'Red' completada exitosamente!")

        # 3. Verificación final
        cursor.execute('SELECT "Red", COUNT(*) FROM "TICKETS_SIPQR2S" GROUP BY "Red" ORDER BY "Red";')
        print("\n📊 Distribución final de 'Red' en TICKETS_SIPQR2S:")
        for fila in cursor.fetchall():
            valor = fila[0] if fila[0] else "(vacío)"
            print(f"   • {valor}: {fila[1]:,}")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error durante la actualización: {e}")
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    actualizar_columna_red()