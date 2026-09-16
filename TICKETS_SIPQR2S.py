import os
import re
import unicodedata
import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extras import execute_values
from sqlalchemy import create_engine
import urllib.parse
import tkinter as tk
from tkinter import filedialog
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# -----------------------------------------------------------------------------
# 1. PARÁMETROS DE CONEXIÓN A POSTGRESQL (Entorno Seguro)
# -----------------------------------------------------------------------------
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "6543")
DB_NAME = os.getenv("DB_NAME", "postgres")

if not DB_USER or not DB_PASS or not DB_HOST:
    raise ValueError("❌ Error: Faltan credenciales de base de datos en el archivo .env")

if isinstance(DB_PASS, bytes):
    DB_PASS = DB_PASS.decode('utf-8', errors='ignore')

pass_encoded = urllib.parse.quote_plus(DB_PASS)
engine = create_engine(f"postgresql://{DB_USER}:{pass_encoded}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

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
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    archivo_seleccionado = filedialog.askopenfilename(
        title="Selecciona el archivo Excel de Tickets SIPQRS",
        filetypes=[("Archivos de Excel", "*.xlsx *.xls"), ("Todos los archivos", "*.*")]
    )
    return archivo_seleccionado

def sanitizar_dataframe(df):
    df_clean = df.copy()
    reemplazos = {
        '№': 'No.',
        '\u2116': 'No.',
        '–': '-',
        '—': '-',
        '‐': '-',
        '‑': '-'
    }
    for col in df_clean.columns:
        series_str = df_clean[col].fillna('').astype(str)
        for orig, remplazo in reemplazos.items():
            series_str = series_str.str.replace(orig, remplazo, regex=False)
        df_clean[col] = series_str.str.strip().replace({'nan': '', 'None': '', 'NaN': ''})

    columnas_a_vaciar = [
        "Nombres", 
        "Apellidos", 
        "Número de Identificación", 
        "Correo Electrónico", 
        "Teléfono Celular",
        "Teléfono Fijo",
        "Dirección Notificación",
        "Dirección Hechos"
    ]
    
    for col in columnas_a_vaciar:
        if col in df_clean.columns:
            df_clean[col] = None
            
    return df_clean

def normalizar_texto_cruce(texto):
    if pd.isna(texto) or texto is None:
        return ""
    s = str(texto).upper().strip()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    s = re.sub(r'[^A-Z0-9\s]', '', s)
    return re.sub(r'\s+', ' ', s).strip()

def aplicar_formulas_excel_estrictas(cadena):
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

def cargar_tickets_y_complementos():
    print("🚀 Iniciando el proceso de ingesta para TICKETS_SIPQR2S...")
    
    archivo_excel = seleccionar_archivo_excel()
    if not archivo_excel:
        print("❌ Operación cancelada. No se seleccionó ningún archivo.")
        return

    print(f"📁 Archivo seleccionado: {os.path.basename(archivo_excel)}")
    
    try:
        df_raw = pd.read_excel(
    archivo_excel, 
    dtype=str, 
    engine="openpyxl", 
    engine_kwargs={"read_only": True, "data_only": True}
)
        print(f"  ✓ Archivo leído. Registros en el archivo de origen: {len(df_raw)}")
    except Exception as e:
        print(f"❌ Error al leer el archivo de Excel: {e}")
        return

    df_raw.columns = [str(col).strip() for col in df_raw.columns]
    df_raw = df_raw.drop_duplicates(subset=["Consecutivo Ticket"]).copy()
    df_raw = sanitizar_dataframe(df_raw)

    try:
        conn_check = obtener_conexion_psycopg2()
        cursor_check = conn_check.cursor()
        cursor_check.execute('SELECT "Consecutivo Ticket" FROM "TICKETS_SIPQR2S";')
        existentes = set(row[0] for row in cursor_check.fetchall())
        cursor_check.close()
        conn_check.close()
        
        df_nuevos = df_raw[~df_raw["Consecutivo Ticket"].isin(existentes)].copy()
        print(f"  ℹ️ Registros ya existentes en BD: {len(existentes)}")
        print(f"  🆕 Nuevos registros listos para ingresar: {len(df_nuevos)}")
        
        if df_nuevos.empty:
            print("✅ La base de datos ya está al día. No hay nuevos registros por insertar.")
            return

    except Exception as e:
        print(f"⚠️ No se pudo consultar preexistencia, se procederá con todos los registros: {e}")
        df_nuevos = df_raw.copy()

    cols_tickets_exactas = [
        "Consecutivo Ticket", "Ticket", "Nombres", "Apellidos", "Tipo de Documento",
        "Número de Identificación", "Correo Electrónico", "Pais Notificación",
        "Departamento Notificación", "Municipio Notificación", "Dirección Notificación",
        "Teléfono Fijo", "Teléfono Celular", "Etnia", "Otra Etnia", "Pais Hechos",
        "Departamento Hechos", "Municipio Hechos", "Dirección Hechos", "Tipo de Solicitud",
        "Clasificación Completa", "Fecha de Recepción", "Fecha de Creación",
        "Aspecto de Interes", "Unidad de Procedencia", "Medio de Recepción",
        "Sigla Fisica", "Sigla Comprometida", "Unidad", "Lugar Asignación",
        "Lugar", "Estado", "Descripción Hechos"
    ]

    df_tickets = df_nuevos[[c for c in cols_tickets_exactas if c in df_nuevos.columns]].copy()

    print("  📥 Insertando registros nuevos en 'TICKETS_SIPQR2S'...")
    _insertar_nativo("TICKETS_SIPQR2S", df_tickets)

    print("  🔄 Replicando desgloses de Excel exactamente por virgulilla (~)...")
    
    df_comp = pd.DataFrame(index=df_nuevos.index)
    df_comp["Consecutivo Ticket"] = df_nuevos["Consecutivo Ticket"].astype(str).str.strip()

    desglose = df_nuevos["Clasificación Completa"].apply(aplicar_formulas_excel_estrictas)
    df_desglose = pd.DataFrame(desglose.tolist(), index=df_nuevos.index)

    df_comp["CODIGO CLASIFICACIÓN"] = df_desglose[0]
    df_comp["MACROMOTIVO"] = df_desglose[1]
    df_comp["MOTIVO GENERAL"] = df_desglose[2]
    df_comp["MOTIVO ESPECÍFICO"] = df_desglose[3]
    df_comp["TIPO DE MOTIVO ESPECÍFICO"] = df_desglose[4]
    df_comp["SUBTIPO DE MOTIVO ESPECÍFICO"] = df_desglose[5]

    df_comp["FECHA CREACIÓN"] = pd.to_datetime(
        df_nuevos["Fecha de Creación"].astype(str).str.split().str[0],
        format="%d/%m/%Y",
        errors="coerce"
    ).dt.strftime("%Y-%m-%d")

    df_upres = pd.read_sql('SELECT * FROM "UPRES_RASES"', con=engine)
    df_comp["LUGAR_KEY"] = df_nuevos["Lugar"].apply(normalizar_texto_cruce)
    df_upres["LUGAR_KEY"] = df_upres["LUGAR"].apply(normalizar_texto_cruce)

    df_comp = pd.merge(
        df_comp,
        df_upres[["LUGAR_KEY", "RASES", "UNIDAD"]].drop_duplicates(subset=["LUGAR_KEY"]),
        on="LUGAR_KEY",
        how="left"
    )
    df_comp["UNIDAD DE ASIGNACIÓN"] = df_comp["UNIDAD"]

    print("  🧠 Cruzando SUBTIPO DE MOTIVO ESPECÍFICO con CATEGORÍAS_SALUD...")
    df_cat = pd.read_sql('SELECT * FROM "CATEGORÍAS_SALUD"', con=engine)
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

    cols_comp_exactas = [
        "Consecutivo Ticket", "CODIGO CLASIFICACIÓN", "MACROMOTIVO", "MOTIVO GENERAL",
        "MOTIVO ESPECÍFICO", "TIPO DE MOTIVO ESPECÍFICO", "SUBTIPO DE MOTIVO ESPECÍFICO",
        "RASES", "FECHA CREACIÓN", "UNIDAD DE ASIGNACIÓN", "CATEGORÍA_SALUD"
    ]
    
    df_comp_final = sanitizar_dataframe(df_comp[cols_comp_exactas])

    print("  📥 Insertando registros en 'COMPLEMENTOS_TICKETS_SIPQR2S'...")
    _insertar_nativo("COMPLEMENTOS_TICKETS_SIPQR2S", df_comp_final)

    print("✅ ¡Inyección completada exitosamente con 100% de coherencia!")

def _insertar_nativo(nombre_tabla, df):
    if df.empty:
        return
    
    conn = obtener_conexion_psycopg2()
    cursor = conn.cursor()

    columnas_format = ', '.join([f'"{col}"' for col in df.columns])
    tuples = [tuple(x) for x in df.fillna("").to_numpy()]
    query = f'INSERT INTO "{nombre_tabla}" ({columnas_format}) VALUES %s'

    execute_values(cursor, query, tuples)
    conn.commit()
    cursor.close()
    conn.close()

if __name__ == "__main__":
    cargar_tickets_y_complementos()