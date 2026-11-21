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
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "postgres")


def obtener_conexion_psycopg2():
    """Conexión nativa psycopg2 con keepalives y sin timeout de sesión."""
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT,
        client_encoding='UTF8',
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5
    )
    return conn


def normalizar_texto_cruce(texto):
    """Convierte el texto a mayúsculas, elimina tildes y caracteres especiales."""
    if pd.isna(texto) or texto is None:
        return ""
    s = str(texto).upper().strip()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    s = re.sub(r'[^A-Z0-9\s]', '', s)
    return re.sub(r'\s+', ' ', s).strip()


def aplicar_formulas_excel_estrictas(cadena):
    """Desglosa la cadena concatenada por virgulilla (~) en los 6 niveles de clasificación."""
    if pd.isna(cadena) or not str(cadena).strip():
        return ["", "", "", "", "", ""]
    partes = [p.strip() for p in str(cadena).split("~")]
    codigo = partes[0] if len(partes) > 0 and partes[0] != "" else str(cadena).strip()
    macro = partes[1].upper() if len(partes) > 1 and partes[1] != "" else codigo.upper()
    general = partes[2] if len(partes) > 2 and partes[2] != "" else macro
    especifico = partes[3] if len(partes) > 3 and partes[3] != "" else general
    if len(partes) > 4 and partes[4] != "":
        val_tipo = partes[4]
        tipo = especifico if val_tipo.upper() in ["NA", "N/A", "NONE", "NAN"] else val_tipo
    else:
        tipo = especifico
    if len(partes) > 5 and partes[5] != "":
        val_subtipo = partes[5].rstrip(")").strip()
        subtipo = tipo if val_subtipo.upper() in ["NA", "N/A", "NONE", "NAN"] else val_subtipo
    else:
        subtipo = tipo
    return [codigo, macro, general, especifico, tipo, subtipo]


def ejecutar_recalculo_completo():
    print("🚀 Iniciando recálculo completo de COMPLEMENTOS_TICKETS_SIPQR2S...")
    conn = obtener_conexion_psycopg2()
    cursor = conn.cursor()

    # Desactivar timeout a nivel de sesión antes de leer
    cursor.execute("SET statement_timeout = 0;")

    sql_tickets = """
        SELECT 
            "Consecutivo Ticket", 
            "Clasificación Completa", 
            "Fecha de Creación", 
            "Lugar", 
            "Unidad",
            "Red"
        FROM "TICKETS_SIPQR2S";
    """

    print("  📥 Leyendo registros desde TICKETS_SIPQR2S...")
    # Lectura directa a DataFrames
    df_tickets = pd.read_sql_query(sql_tickets, conn)
    df_upres = pd.read_sql_query('SELECT * FROM "UPRES_RASES";', conn)
    df_cat = pd.read_sql_query('SELECT * FROM "CATEGORÍAS_SALUD";', conn)

    if df_tickets.empty:
        print("⚠️ La tabla TICKETS_SIPQR2S está vacía. No hay registros para procesar.")
        cursor.close()
        conn.close()
        return

    print(f"  ✓ Registros leídos correctamente: {len(df_tickets)}")

    # 1. Reconstruir DataFrame de complementos
    df_comp = pd.DataFrame()
    df_comp["Consecutivo Ticket"] = df_tickets["Consecutivo Ticket"].astype(str).str.strip()

    # Desglose por virgulilla (~)
    desglose = df_tickets["Clasificación Completa"].apply(aplicar_formulas_excel_estrictas)
    df_desglose = pd.DataFrame(desglose.tolist(), index=df_tickets.index)
    df_comp["CODIGO CLASIFICACIÓN"] = df_desglose[0]
    df_comp["MACROMOTIVO"] = df_desglose[1]
    df_comp["MOTIVO GENERAL"] = df_desglose[2]
    df_comp["MOTIVO ESPECÍFICO"] = df_desglose[3]
    df_comp["TIPO DE MOTIVO ESPECÍFICO"] = df_desglose[4]
    df_comp["SUBTIPO DE MOTIVO ESPECÍFICO"] = df_desglose[5]

    # Formato de Fecha Creación
    df_comp["FECHA CREACIÓN"] = pd.to_datetime(
        df_tickets["Fecha de Creación"].astype(str).str.split().str[0],
        format="%d/%m/%Y",
        errors="coerce"
    ).dt.strftime("%Y-%m-%d")

    # 2. Cruce con UPRES_RASES
    df_comp["LUGAR_KEY"] = df_tickets["Lugar"].apply(normalizar_texto_cruce)
    df_upres["LUGAR_KEY"] = df_upres["LUGAR"].apply(normalizar_texto_cruce)
    df_comp = pd.merge(
        df_comp,
        df_upres[["LUGAR_KEY", "RASES", "UNIDAD"]].drop_duplicates(subset=["LUGAR_KEY"]),
        on="LUGAR_KEY",
        how="left"
    )
    df_comp["UNIDAD DE ASIGNACIÓN"] = df_comp["UNIDAD"]

    # 3. Cruce con CATEGORÍAS_SALUD
    df_cat["KEY_MAESTRA"] = df_cat["SUBMOTIVO DE TIPO ESPECÍFICO"].apply(normalizar_texto_cruce)
    df_cat_clean = df_cat.drop_duplicates(subset=["KEY_MAESTRA"])[["KEY_MAESTRA", "CATEGORÍA_SALUD"]]
    df_comp["KEY_SUBTIPO"] = df_comp["SUBTIPO DE MOTIVO ESPECÍFICO"].apply(normalizar_texto_cruce)
    df_comp = pd.merge(
        df_comp,
        df_cat_clean,
        left_on="KEY_SUBTIPO",
        right_on="KEY_MAESTRA",
        how="left"
    )

    # ⭐ NUEVO: Agregar columna Red desde los tickets
    if "Red" in df_tickets.columns:
        df_comp["Red"] = df_tickets["Red"].fillna("").astype(str).str.strip()
    else:
        df_comp["Red"] = ""

    # 4. Filtrar y ordenar las columnas de destino
    cols_comp_exactas = [
        "Consecutivo Ticket", "CODIGO CLASIFICACIÓN", "MACROMOTIVO", "MOTIVO GENERAL",
        "MOTIVO ESPECÍFICO", "TIPO DE MOTIVO ESPECÍFICO", "SUBTIPO DE MOTIVO ESPECÍFICO",
        "RASES", "FECHA CREACIÓN", "UNIDAD DE ASIGNACIÓN", "CATEGORÍA_SALUD", "Red"
    ]
    df_comp_final = df_comp[cols_comp_exactas].fillna("")

    # 5. Vaciar e Inserción masiva con Psycopg2
    print("  🔄 Vaciando la tabla COMPLEMENTOS_TICKETS_SIPQR2S...")
    cursor.execute('TRUNCATE TABLE "COMPLEMENTOS_TICKETS_SIPQR2S";')
    print(f"  📥 Insertando {len(df_comp_final)} registros en COMPLEMENTOS_TICKETS_SIPQR2S...")
    columnas_format = ', '.join([f'"{col}"' for col in df_comp_final.columns])
    tuples = [tuple(x) for x in df_comp_final.to_numpy()]
    query = f'INSERT INTO "COMPLEMENTOS_TICKETS_SIPQR2S" ({columnas_format}) VALUES %s'
    execute_values(cursor, query, tuples, page_size=10000)
    conn.commit()

    # 6. ⭐ CORREGIDO: La vista es NORMAL, no materializada. No necesita REFRESH.
    # Las vistas normales se actualizan automáticamente al cambiar los datos de las tablas base.
    print("  ℹ️ La vista V_SIPQR2S_CONSOLIDADO es una vista normal (no materializada).")
    print("     Se actualiza automáticamente al modificar las tablas base.")
    print("✅ ¡Proceso completado exitosamente!")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    ejecutar_recalculo_completo()