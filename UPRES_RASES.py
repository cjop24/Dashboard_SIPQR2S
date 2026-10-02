import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# Cargar variables del entorno local (.env)
load_dotenv()

# Parámetros de Conexión a PostgreSQL
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "6543")
DB_NAME = os.getenv("DB_NAME", "postgres")

if not DB_USER or not DB_PASS or not DB_HOST:
    raise ValueError("❌ Error: Faltan credenciales de base de datos en el archivo .env")

def cargar_tabla_upres():
    print("🚀 Iniciando la carga dedicada de 'UPRES_RASES' a Supabase...")
    
    archivo_excel = "UPRES_RASES.xlsx"
    hoja_excel = "UPRES_RASES"
    
    try:
        df_upres = pd.read_excel(archivo_excel, sheet_name=hoja_excel, dtype=str)
        print(f"  ✓ Archivo 'UPRES_RASES.xlsx' leído. Registros: {len(df_upres)}")
    except Exception as e:
        print(f"❌ Error al leer el archivo Excel: {e}")
        return

    df_upres.columns = [str(col).strip().upper() for col in df_upres.columns]
    
    # Mapeo de columnas agregando 'USUARIOS'
    mapa_columnas = {
        "LUGAR": "LUGAR",
        "RASES": "RASES",
        "UNIDAD": "UNIDAD",
        "USUARIOS": "USUARIOS",
        "CANTIDAD DE USUARIOS": "USUARIOS",
        "CANTIDAD USUARIOS": "USUARIOS",
        "POBLACION": "USUARIOS"
    }
    df_upres = df_upres.rename(columns=mapa_columnas)
    
    if "USUARIOS" not in df_upres.columns:
        df_upres["USUARIOS"] = "0"
        
    cols_destino = ["LUGAR", "RASES", "UNIDAD", "USUARIOS"]
    df_upres = df_upres[[col for col in cols_destino if col in df_upres.columns]]
    
    for col in df_upres.columns:
        df_upres[col] = df_upres[col].astype(str).str.strip()

    df_upres["USUARIOS"] = pd.to_numeric(df_upres["USUARIOS"].str.replace(',', '').str.replace('.', ''), errors='coerce').fillna(0)

    df_upres = df_upres.drop_duplicates(subset=["LUGAR"])
    df_upres = df_upres[df_upres["LUGAR"].str.upper() != "NAN"]
    df_upres = df_upres[df_upres["LUGAR"] != ""]

    print("  📥 Insertando registros en la tabla 'UPRES_RASES' en la nube...")
    
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

        cursor.execute('TRUNCATE TABLE "UPRES_RASES" CASCADE;')

        tuples = [tuple(x) for x in df_upres.to_numpy()]
        query = 'INSERT INTO "UPRES_RASES" ("LUGAR", "RASES", "UNIDAD", "USUARIOS") VALUES %s'
        
        execute_values(cursor, query, tuples)
        conn.commit()
        
        cursor.close()
        conn.close()
        
        print("✅ ¡Carga de 'UPRES_RASES' completada con éxito en Supabase!")
        
    except Exception as e:
        print(f"⚠️ Error al insertar registros en PostgreSQL: {e}")

if __name__ == "__main__":
    cargar_tabla_upres()