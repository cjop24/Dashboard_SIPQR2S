import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# -----------------------------------------------------------------------------
# 1. CARGA DE CONFIGURACIÓN Y CONEXIÓN
# -----------------------------------------------------------------------------
load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "neondb")

def cargar_usuarios_mensuales():
    print("🚀 Cargando datos mensuales de usuarios atendidos a Neon.tech...")
    
    archivo_excel = "USUARIOS_ATENDIDOS_MENSUAL.xlsx"
    
    if not os.path.exists(archivo_excel):
        print(f"❌ Error: No se encontró el archivo '{archivo_excel}' en la carpeta del proyecto.")
        return

    try:
        df_raw = pd.read_excel(
            archivo_excel,
            sheet_name=0,
            engine="openpyxl",
            dtype=str
        )
        print(f"  ✓ Archivo '{archivo_excel}' leído correctamente ({len(df_raw)} filas).")
    except Exception as e:
        print(f"❌ Error al leer el archivo Excel: {e}")
        return

    # Normalizar encabezados eliminando espacios y convirtiendo a mayúsculas
    df_raw.columns = [str(c).strip().upper() for c in df_raw.columns]

    registros = []
    
    for _, fila in df_raw.iterrows():
        unidad = str(fila['UNIDAD']).strip().upper()
        
        # Ignorar filas vacías o de totales
        if unidad in ['TOTAL GENERAL', 'NAN', '', 'NONE', 'NULL']:
            continue

        # Soporte para ambas estructuras de Excel: MES_ANIO único o ANIO + MES
        if "MES_ANIO" in df_raw.columns:
            mes_anio = str(fila['MES_ANIO']).strip()
        elif "ANIO" in df_raw.columns and "MES" in df_raw.columns:
            val_anio = int(pd.to_numeric(fila['ANIO'], errors='coerce'))
            val_mes = int(pd.to_numeric(fila['MES'], errors='coerce'))
            mes_anio = f"{val_anio}-{val_mes:02d}"
        else:
            continue
            
        val_usuarios = pd.to_numeric(
            str(fila['USUARIOS']).replace(',', '').replace('.', ''), 
            errors='coerce'
        )
        
        if pd.notna(val_usuarios):
            registros.append((
                unidad,
                mes_anio,
                int(val_usuarios)
            ))

    print(f"  📥 Insertando/actualizando {len(registros)} registros mensuales en Neon...")
    
    if not registros:
        print("⚠️ No se generaron registros válidos para insertar.")
        return

    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, 
            user=DB_USER, 
            password=DB_PASS, 
            host=DB_HOST, 
            port=DB_PORT
        )
        cursor = conn.cursor()
        
        # Inserción con conflicto en la restricción UNIQUE ("UNIDAD", "MES_ANIO")
        query = """
            INSERT INTO "USUARIOS_ATENDIDOS_MENSUAL" ("UNIDAD", "MES_ANIO", "USUARIOS")
            VALUES %s
            ON CONFLICT ("UNIDAD", "MES_ANIO") 
            DO UPDATE SET "USUARIOS" = EXCLUDED."USUARIOS";
        """
        execute_values(cursor, query, registros)
        conn.commit()
        
        cursor.close()
        conn.close()
        print("✅ ¡Carga de usuarios mensuales completada con éxito en Neon.tech!")
        
    except Exception as e:
        print(f"⚠️ Error al insertar registros en PostgreSQL: {e}")

if __name__ == "__main__":
    cargar_usuarios_mensuales()