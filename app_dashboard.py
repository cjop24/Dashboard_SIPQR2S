import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
import urllib.parse
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE PÁGINA (Responsive PC / Mobile)[cite: 1]
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Seguimiento SIPQRS",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo CSS personalizado para adaptar tarjetas y contenedores[cite: 1]
st.markdown("""
    <style>
    .main { padding: 1rem; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. AUTENTICACIÓN DE USUARIOS
# -----------------------------------------------------------------------------
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# Renderizado de la pantalla de inicio de sesión
authenticator.login('main')

# Lectura directa del estado en sesión
authentication_status = st.session_state.get("authentication_status")
name = st.session_state.get("name")
username = st.session_state.get("username")

if authentication_status == False:
    st.error("Usuario o contraseña incorrectos")
elif authentication_status is None:
    st.warning("Por favor ingrese sus credenciales para acceder al sistema")

elif authentication_status:

    # -----------------------------------------------------------------------------
    # 3. CONTROL DE SESIÓN Y BARRA LATERAL[cite: 1]
    # -----------------------------------------------------------------------------
    st.sidebar.write(f"👤 Bienvenido(a), **{name}**")
    authenticator.logout('Cerrar Sesión', 'sidebar')
    st.sidebar.markdown("---")

    # -----------------------------------------------------------------------------
    # 4. CONEXIÓN A POSTGRESQL EN LA NUBE (Supabase) CON CACHÉ[cite: 1]
    # -----------------------------------------------------------------------------
    try:
        DB_USER = st.secrets["postgres"]["user"]
        DB_PASS = st.secrets["postgres"]["password"]
        DB_HOST = st.secrets["postgres"]["host"]
        DB_PORT = st.secrets["postgres"]["port"]
        DB_NAME = st.secrets["postgres"]["dbname"]
    except Exception:
        # Fallback con parámetros de Supabase[cite: 1]
        DB_USER = "postgres.gsszvzxswzkqsnajimij"
        DB_PASS = "TuContraseñaActivaDeSupabase"
        DB_HOST = "aws-0-us-east-2.pooler.supabase.com"
        DB_PORT = "6543"
        DB_NAME = "postgres"

    pass_encoded = urllib.parse.quote_plus(DB_PASS)
    engine = create_engine(f"postgresql://{DB_USER}:{pass_encoded}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

    @st.cache_data(ttl=600)
    def cargar_datos_consolidados():
        query = 'SELECT * FROM "V_SIPQR2S_CONSOLIDADO";'
        df = pd.read_sql(query, con=engine)
        df['fecha_dt'] = pd.to_datetime(df['fecha_dt'])
        return df

    try:
        df_raw = cargar_datos_consolidados()
    except Exception as e:
        st.error(f"Error conectando a la base de datos PostgreSQL: {e}")
        st.stop()

    # -----------------------------------------------------------------------------
    # 5. SEGMENTADORES INTERACTIVOS (SIDEBAR)[cite: 1]
    # -----------------------------------------------------------------------------
    st.sidebar.header("🔍 Filtros de Control")

    # Segmentador CATEGORÍA SALUD (Con Búsqueda y Ordenado por Cantidad)[cite: 1]
    cat_counts = df_raw['ESPECIALIDAD_CATEGORIA'].value_counts()
    opciones_cat = [f"{cat} ({count:,})" for cat, count in cat_counts.items() if cat != '']
    mapa_cat = {f"{cat} ({count:,})": cat for cat, count in cat_counts.items() if cat != ''}

    sel_cat_display = st.sidebar.multiselect(
        "Categoría Salud / Especialidad",
        options=opciones_cat,
        placeholder="Escribe para buscar..."
    )
    sel_cat = [mapa_cat[item] for item in sel_cat_display]

    st.sidebar.markdown("---")

    # Filtro RASES[cite: 1]
    lista_rases = sorted([x for x in df_raw['RASES'].dropna().unique() if x != ''])
    sel_rases = st.sidebar.multiselect("RASES", options=lista_rases)

    # Filtro UNIDAD (UPRES) condicionado a RASES[cite: 1]
    df_filtered_unidad = df_raw[df_raw['RASES'].isin(sel_rases)] if sel_rases else df_raw
    lista_unidades = sorted([x for x in df_filtered_unidad['UNIDAD DE ASIGNACIÓN'].dropna().unique() if x != ''])
    sel_unidades = st.sidebar.multiselect("UNIDAD DE ASIGNACIÓN", options=lista_unidades)

    # Filtro Tipo de Solicitud[cite: 1]
    lista_tipos = sorted([x for x in df_raw['Tipo de Solicitud'].dropna().unique() if x != ''])
    sel_tipos = st.sidebar.multiselect("Tipo de Solicitud", options=lista_tipos)

    # Filtro Medio de Recepción[cite: 1]
    lista_medios = sorted([x for x in df_raw['Medio de Recepción'].dropna().unique() if x != ''])
    sel_medios = st.sidebar.multiselect("Medio de Recepción", options=lista_medios)

    # Filtro Rango de Fechas[cite: 1]
    min_fecha = df_raw['fecha_dt'].min().date() if not df_raw.empty else None
    max_fecha = df_raw['fecha_dt'].max().date() if not df_raw.empty else None

    if min_fecha and max_fecha:
        rango_fechas = st.sidebar.date_input("Rango de Fechas", value=(min_fecha, max_fecha), min_value=min_fecha, max_value=max_fecha)
    else:
        rango_fechas = []

    # -----------------------------------------------------------------------------
    # 6. APLICACIÓN DE FILTROS EN MEMORIA[cite: 1]
    # -----------------------------------------------------------------------------
    df_final = df_raw.copy()

    if sel_cat:
        df_final = df_final[df_final['ESPECIALIDAD_CATEGORIA'].isin(sel_cat)]
    if sel_rases:
        df_final = df_final[df_final['RASES'].isin(sel_rases)]
    if sel_unidades:
        df_final = df_final[df_final['UNIDAD DE ASIGNACIÓN'].isin(sel_unidades)]
    if sel_tipos:
        df_final = df_final[df_final['Tipo de Solicitud'].isin(sel_tipos)]
    if sel_medios:
        df_final = df_final[df_final['Medio de Recepción'].isin(sel_medios)]
    if len(rango_fechas) == 2:
        df_final = df_final[(df_final['fecha_dt'].dt.date >= rango_fechas[0]) & (df_final['fecha_dt'].dt.date <= rango_fechas[1])]

    # -----------------------------------------------------------------------------
    # 7. ENCABEZADO Y TARJETAS KPI[cite: 1]
    # -----------------------------------------------------------------------------
    st.title("🛡️ Dashboard de Seguimiento SIPQRS")
    st.caption("Dirección de Sanidad Policía Nacional - Oficina de Atención al Usuario")

    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    col_kpi1.metric("Total Reclamos / Tickets", f"{len(df_final):,}")
    col_kpi2.metric("Unidades Activas", f"{df_final['UNIDAD DE ASIGNACIÓN'].nunique():,}")
    col_kpi3.metric("Especialidades", f"{df_final['ESPECIALIDAD_CATEGORIA'].nunique():,}")
    col_kpi4.metric("Tipos de Solicitud", f"{df_final['Tipo de Solicitud'].nunique():,}")

    st.markdown("---")

    # -----------------------------------------------------------------------------
    # 8. FILA 1 DE GRÁFICOS: DISTRIBUCIÓN TERRITORIAL Y VOLUMEN[cite: 1]
    # -----------------------------------------------------------------------------
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("📍 Distribución por RASES")
        df_rases = df_final['RASES'].value_counts().reset_index()
        df_rases.columns = ['RASES', 'Cantidad']
        fig_rases = px.bar(df_rases, x='RASES', y='Cantidad', text_auto=True, color_discrete_sequence=['#2e7d32'])
        fig_rases.update_layout(xaxis_title="", yaxis_title="", height=320, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig_rases, use_container_width=True)

    with c2:
        st.subheader("🏢 Top 5 Cantidad de SIPQRS por Unidad")
        df_unid = df_final['UNIDAD DE ASIGNACIÓN'].value_counts().head(5).reset_index()
        df_unid.columns = ['Unidad', 'Cantidad']
        fig_unid = px.bar(df_unid, x='Unidad', y='Cantidad', text_auto=True, color_discrete_sequence=['#388e3c'])
        fig_unid.update_layout(xaxis_title="", yaxis_title="", height=320, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig_unid, use_container_width=True)

    # -----------------------------------------------------------------------------
    # 9. FILA 2 DE GRÁFICOS: ESPECIALIDADES Y MOTIVOS GENERALES[cite: 1]
    # -----------------------------------------------------------------------------
    c3, c4 = st.columns(2)

    with c3:
        st.subheader("🩺 Top Especialidades (Categoría Salud)")
        df_esp = df_final['ESPECIALIDAD_CATEGORIA'].value_counts().head(10).reset_index()
        df_esp.columns = ['Especialidad', 'Cantidad']
        fig_esp = px.bar(df_esp, y='Especialidad', x='Cantidad', orientation='h', text_auto=True, color_discrete_sequence=['#43a047'])
        fig_esp.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="", yaxis_title="", height=400, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig_esp, use_container_width=True)

    with c4:
        st.subheader("📋 SIPQRS por Motivo General")
        df_mot = df_final['MOTIVO GENERAL'].value_counts().head(5).reset_index()
        df_mot.columns = ['Motivo General', 'Cantidad']
        fig_mot = px.bar(df_mot, y='Motivo General', x='Cantidad', orientation='h', text_auto=True, color_discrete_sequence=['#1b5e20'])
        fig_mot.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="", yaxis_title="", height=400, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig_mot, use_container_width=True)

    # -----------------------------------------------------------------------------
    # 10. FILA 3 DE GRÁFICOS: TIPO DE SOLICITUD Y MEDIO DE RECEPCIÓN[cite: 1]
    # -----------------------------------------------------------------------------
    c5, c6 = st.columns(2)

    with c5:
        st.subheader("📩 Tipo de Solicitud")
        df_sol = df_final['Tipo de Solicitud'].value_counts().reset_index()
        df_sol.columns = ['Tipo', 'Cantidad']
        fig_sol = px.bar(df_sol, y='Tipo', x='Cantidad', orientation='h', text_auto=True, color_discrete_sequence=['#66bb6a'])
        fig_sol.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="", yaxis_title="", height=300, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig_sol, use_container_width=True)

    with c6:
        st.subheader("📬 Medio de Recepción")
        df_med = df_final['Medio de Recepción'].value_counts().reset_index()
        df_med.columns = ['Medio', 'Cantidad']
        fig_med = px.bar(df_med, y='Medio', x='Cantidad', orientation='h', text_auto=True, color_discrete_sequence=['#81c784'])
        fig_med.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="", yaxis_title="", height=300, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig_med, use_container_width=True)