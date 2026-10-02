import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# Cargar variables del entorno local (.env)
load_dotenv()

# Parámetros de Conexión a PostgreSQL (Lectura limpia desde entorno)
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "6543")
DB_NAME = os.getenv("DB_NAME", "postgres")

# Validación estricta de variables obligatorias
if not DB_USER or not DB_PASS or not DB_HOST:
    raise ValueError("❌ Error: Faltan credenciales de base de datos en el archivo .env")

def cargar_tabla_categorias():
    print("🚀 Iniciando la carga independiente de 'CATEGORÍAS_SALUD'...")
    
    archivo_excel = "CATEGORÍAS_SALUD.xlsx"
    hoja_excel = "CATEGORÍAS_SALUD"
    
    try:
        df_cat = pd.read_excel(archivo_excel, sheet_name=hoja_excel, dtype=str)
        print(f"  ✓ Archivo leído. Registros encontrados: {len(df_cat)}")
    except Exception as e:
        print(f"❌ Error al leer el Excel: {e}")
        return

    df_cat.columns = [str(col).strip() for col in df_cat.columns]

    col_submotivo = df_cat.columns[0]
    col_categoria = df_cat.columns[1]

    for col in df_cat.columns:
        col_upper = col.upper()
        if "SUBMOTIVO" in col_upper or "SUBTIPO" in col_upper:
            col_submotivo = col
        elif "CATEGOR" in col_upper:
            col_categoria = col

    df_cat = df_cat.rename(columns={
        col_submotivo: "SUBMOTIVO DE TIPO ESPECÍFICO",
        col_categoria: "CATEGORÍA_SALUD"
    })

    df_cat = df_cat[["SUBMOTIVO DE TIPO ESPECÍFICO", "CATEGORÍA_SALUD"]]

    df_cat["SUBMOTIVO DE TIPO ESPECÍFICO"] = df_cat["SUBMOTIVO DE TIPO ESPECÍFICO"].astype(str).str.strip()
    df_cat["CATEGORÍA_SALUD"] = df_cat["CATEGORÍA_SALUD"].astype(str).str.strip()

    df_cat = df_cat.drop_duplicates(subset=["SUBMOTIVO DE TIPO ESPECÍFICO"])
    df_cat = df_cat[df_cat["SUBMOTIVO DE TIPO ESPECÍFICO"].str.upper() != "NAN"]
    df_cat = df_cat[df_cat["SUBMOTIVO DE TIPO ESPECÍFICO"] != ""]

    print("  📥 Insertando datos en la tabla 'CATEGORÍAS_SALUD'...")
    
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            port=DB_PORT
        )
        
        conn.set_client_encoding('WIN1252')
        cursor = conn.cursor()

        cursor.execute('TRUNCATE TABLE "CATEGORÍAS_SALUD" CASCADE;')

        tuples = [tuple(x) for x in df_cat.to_numpy()]
        query = 'INSERT INTO "CATEGORÍAS_SALUD" ("SUBMOTIVO DE TIPO ESPECÍFICO", "CATEGORÍA_SALUD") VALUES %s'
        
        execute_values(cursor, query, tuples)
        conn.commit()
        
        cursor.close()
        conn.close()
        
        print("✅ ¡Carga de CATEGORÍAS_SALUD completada con éxito!")
        
    except Exception as e:
        print(f"⚠️ Error al insertar registros: {e}")

if __name__ == "__main__":
    cargar_tabla_categorias()