import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
import urllib.parse
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN RESPONSIVA (Mobile-First / iOS Friendly)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard SIPQRS",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilos CSS optimizados para tarjetas táctiles y eliminación de interrupciones de scroll
st.markdown("""
    <style>
    .main { padding: 0.5rem; }
    
    /* Tarjetas KPI estilo iOS */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 12px 14px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        border: 1px solid #e5e7eb;
        margin-bottom: 8px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.4rem !important;
        font-weight: 700;
        color: #1b5e20;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.8rem !important;
        color: #4b5563;
        font-weight: 600;
    }

    h1 { font-size: 1.5rem !important; font-weight: 800; color: #0f172a; }
    h3 { font-size: 1.05rem !important; font-weight: 700; color: #1e293b; margin-top: 0.8rem; }
    </style>
""", unsafe_allow_html=True)

# Función para fijar los ejes y deshabilitar gestos táctiles de zoom
def aplicar_touch_safe(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig

CONFIG_PLOTLY_TOUCH = {
    'displayModeBar': False,
    'scrollZoom': False,
    'doubleClick': False,
    'showAxisDragHandles': False
}

# -----------------------------------------------------------------------------
# 2. AUTENTICACIÓN
# -----------------------------------------------------------------------------
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

name, authentication_status, username = authenticator.login('main')

if authentication_status == False:
    st.error("Usuario o contraseña incorrectos")
elif authentication_status == None:
    st.warning("Ingrese sus credenciales para acceder")

elif authentication_status:
    # -----------------------------------------------------------------------------
    # 3. CONEXIÓN Y DATOS CON CACHÉ
    # -----------------------------------------------------------------------------
    try:
        DB_USER = st.secrets["postgres"]["user"]
        DB_PASS = st.secrets["postgres"]["password"]
        DB_HOST = st.secrets["postgres"]["host"]
        DB_PORT = st.secrets["postgres"]["port"]
        DB_NAME = st.secrets["postgres"]["dbname"]
    except Exception:
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
        st.error(f"Error al conectar con la base de datos: {e}")
        st.stop()

    # -----------------------------------------------------------------------------
    # 4. SEGMENTADORES EN SIDEBAR (LOS 8 SOLICITADOS)
    # -----------------------------------------------------------------------------
    st.sidebar.write(f"👤 **{name}**")
    authenticator.logout('Cerrar Sesión', 'sidebar')
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filtros de Consulta")

    # 1. RASES
    lista_rases = sorted([x for x in df_raw['RASES'].dropna().unique() if x != ''])
    sel_rases = st.sidebar.multiselect("1. RASES", options=lista_rases)

    # 2. UPRES
    df_filtered_upres = df_raw[df_raw['RASES'].isin(sel_rases)] if sel_rases else df_raw
    lista_unidades = sorted([x for x in df_filtered_upres['UNIDAD DE ASIGNACIÓN'].dropna().unique() if x != ''])
    sel_unidades = st.sidebar.multiselect("2. UPRES (Unidad)", options=lista_unidades)

    # 3. Tipo Solicitud
    lista_tipos = sorted([x for x in df_raw['Tipo de Solicitud'].dropna().unique() if x != ''])
    sel_tipos = st.sidebar.multiselect("3. Tipo de Solicitud", options=lista_tipos)

    # 4. Medio Recepción
    lista_medios = sorted([x for x in df_raw['Medio de Recepción'].dropna().unique() if x != ''])
    sel_medios = st.sidebar.multiselect("4. Medio de Recepción", options=lista_medios)

    # 5. Fecha Creación
    min_fecha = df_raw['fecha_dt'].min().date() if not df_raw.empty else None
    max_fecha = df_raw['fecha_dt'].max().date() if not df_raw.empty else None
    rango_fechas = st.sidebar.date_input("5. Fecha de Creación", value=(min_fecha, max_fecha), min_value=min_fecha, max_value=max_fecha) if min_fecha else []

    # 6. Categoría Salud (Con buscador por conteo)
    cat_counts = df_raw['ESPECIALIDAD_CATEGORIA'].value_counts()
    opciones_cat = [f"{cat} ({count:,})" for cat, count in cat_counts.items() if cat != '']
    mapa_cat = {f"{cat} ({count:,})": cat for cat, count in cat_counts.items() if cat != ''}
    sel_cat_disp = st.sidebar.multiselect("6. Categoría Salud", options=opciones_cat, placeholder="Escriba para buscar...")
    sel_cat = [mapa_cat[item] for item in sel_cat_disp]

    # 7. Macromotivo
    lista_macro = sorted([x for x in df_raw['MACROMOTIVO'].dropna().unique() if str(x).strip() != '']) if 'MACROMOTIVO' in df_raw.columns else []
    sel_macro = st.sidebar.multiselect("7. Macromotivo", options=lista_macro)

    # 8. Motivo General
    lista_motivo = sorted([x for x in df_raw['MOTIVO GENERAL'].dropna().unique() if str(x).strip() != '']) if 'MOTIVO GENERAL' in df_raw.columns else []
    sel_motivo = st.sidebar.multiselect("8. Motivo General", options=lista_motivo)

    # Filtrado unificado
    df_base = df_raw.copy()
    if sel_rases: df_base = df_base[df_base['RASES'].isin(sel_rases)]
    if sel_unidades: df_base = df_base[df_base['UNIDAD DE ASIGNACIÓN'].isin(sel_unidades)]
    if sel_tipos: df_base = df_base[df_base['Tipo de Solicitud'].isin(sel_tipos)]
    if sel_medios: df_base = df_base[df_base['Medio de Recepción'].isin(sel_medios)]
    if len(rango_fechas) == 2:
        df_base = df_base[(df_base['fecha_dt'].dt.date >= rango_fechas[0]) & (df_base['fecha_dt'].dt.date <= rango_fechas[1])]
    if sel_cat: df_base = df_base[df_base['ESPECIALIDAD_CATEGORIA'].isin(sel_cat)]
    if sel_macro and 'MACROMOTIVO' in df_base.columns: df_base = df_base[df_base['MACROMOTIVO'].isin(sel_macro)]
    if sel_motivo and 'MOTIVO GENERAL' in df_base.columns: df_base = df_base[df_base['MOTIVO GENERAL'].isin(sel_motivo)]

    # -----------------------------------------------------------------------------
    # 5. PESTAÑAS DEL DASHBOARD
    # -----------------------------------------------------------------------------
    st.title("🛡️ SIPQRS Sanidad")
    
    tab_ind, tab_comp, tab_det = st.tabs(["📊 Análisis Individual", "🔄 Comparativo", "📋 Detalle"])

    # -----------------------------------------------------------------------------
    # PESTAÑA: ANÁLISIS INDIVIDUAL
    # -----------------------------------------------------------------------------
    with tab_ind:
        st.caption("Resumen Ejecutivo e Individualización de Variables")

        # Cargar Tarjetas Principales
        top_cat_serie = df_base['ESPECIALIDAD_CATEGORIA'].value_counts()
        top_cat_nombre = top_cat_serie.index[0] if not top_cat_serie.empty else "N/A"
        top_cat_val = top_cat_serie.iloc[0] if not top_cat_serie.empty else 0

        kpi_col1, kpi_col2 = st.columns(2)
        kpi_col1.metric("Total SIPQRS País", f"{len(df_base):,}")
        kpi_col2.metric("Categoría Más Afectada", f"{top_cat_nombre}", delta=f"{top_cat_val:,} tickets", delta_color="off")

        st.markdown("---")

        # Gráfico 1: SIPQRS por RASES
        st.subheader("📍 SIPQRS por RASES")
        df_g1 = df_base['RASES'].value_counts().reset_index()
        df_g1.columns = ['RASES', 'Cantidad']
        fig1 = px.bar(df_g1, x='RASES', y='Cantidad', text_auto=True, color_discrete_sequence=['#2e7d32'])
        fig1.update_layout(xaxis_title="", yaxis_title="", height=300, margin=dict(l=5, r=5, t=10, b=10))
        st.plotly_chart(aplicar_touch_safe(fig1), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

        # Gráfico 2: SIPQRS por UPRES (Top 10)
        st.subheader("🏢 SIPQRS por UPRES (Top 10)")
        df_g2 = df_base['UNIDAD DE ASIGNACIÓN'].value_counts().head(10).reset_index()
        df_g2.columns = ['UPRES', 'Cantidad']
        fig2 = px.bar(df_g2, y='UPRES', x='Cantidad', orientation='h', text_auto=True, color_discrete_sequence=['#388e3c'])
        fig2.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="", yaxis_title="", height=340, margin=dict(l=5, r=5, t=10, b=10))
        st.plotly_chart(aplicar_touch_safe(fig2), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

        # Gráfico 3: SIPQRS por CATEGORÍA_SALUD (Top 10)
        st.subheader("🩺 SIPQRS por Categoría Salud (Top 10)")
        df_g3 = df_base['ESPECIALIDAD_CATEGORIA'].value_counts().head(10).reset_index()
        df_g3.columns = ['Categoría', 'Cantidad']
        fig3 = px.bar(df_g3, y='Categoría', x='Cantidad', orientation='h', text_auto=True, color_discrete_sequence=['#43a047'])
        fig3.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="", yaxis_title="", height=340, margin=dict(l=5, r=5, t=10, b=10))
        st.plotly_chart(aplicar_touch_safe(fig3), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

        # Gráfico 4: SIPQRS por MOTIVO GENERAL (Top 8)
        st.subheader("📋 SIPQRS por Motivo General")
        df_g4 = df_base['MOTIVO GENERAL'].value_counts().head(8).reset_index() if 'MOTIVO GENERAL' in df_base.columns else pd.DataFrame()
        if not df_g4.empty:
            df_g4.columns = ['Motivo General', 'Cantidad']
            fig4 = px.bar(df_g4, y='Motivo General', x='Cantidad', orientation='h', text_auto=True, color_discrete_sequence=['#1b5e20'])
            fig4.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="", yaxis_title="", height=320, margin=dict(l=5, r=5, t=10, b=10))
            st.plotly_chart(aplicar_touch_safe(fig4), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

        # Gráfico 5: SIPQRS por Tipo de Solicitud (Barras)
        st.subheader("📩 SIPQRS por Tipo de Solicitud")
        df_g5 = df_base['Tipo de Solicitud'].value_counts().reset_index()
        df_g5.columns = ['Tipo', 'Cantidad']
        fig5 = px.bar(df_g5, x='Tipo', y='Cantidad', text_auto=True, color_discrete_sequence=['#66bb6a'])
        fig5.update_layout(xaxis_title="", yaxis_title="", height=280, margin=dict(l=5, r=5, t=10, b=10))
        st.plotly_chart(aplicar_touch_safe(fig5), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

        # Gráfico 6: Porcentaje SIPQRS por Tipo de Solicitud (Torta / Donut)
        st.subheader("🍰 Proporción (%) por Tipo de Solicitud")
        fig6 = px.pie(df_g5, values='Cantidad', names='Tipo', hole=0.4, color_discrete_sequence=px.colors.sequential.Greens_r)
        fig6.update_layout(height=300, margin=dict(l=5, r=5, t=10, b=10), legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(aplicar_touch_safe(fig6), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

        # Gráfico 7: SIPQRS por Medio de Recepción (Barras)
        st.subheader("📬 SIPQRS por Medio de Recepción")
        df_g7 = df_base['Medio de Recepción'].value_counts().reset_index()
        df_g7.columns = ['Medio', 'Cantidad']
        fig7 = px.bar(df_g7, y='Medio', x='Cantidad', orientation='h', text_auto=True, color_discrete_sequence=['#81c784'])
        fig7.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="", yaxis_title="", height=280, margin=dict(l=5, r=5, t=10, b=10))
        st.plotly_chart(aplicar_touch_safe(fig7), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

        # Gráfico 8: Porcentaje SIPQRS por Medio de Recepción (Torta / Donut)
        st.subheader("🍩 Proporción (%) por Medio de Recepción")
        fig8 = px.pie(df_g7, values='Cantidad', names='Medio', hole=0.4, color_discrete_sequence=px.colors.sequential.YlGn_r)
        fig8.update_layout(height=300, margin=dict(l=5, r=5, t=10, b=10), legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(aplicar_touch_safe(fig8), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

    # -----------------------------------------------------------------------------
    # PESTAÑA: COMPARATIVO
    # -----------------------------------------------------------------------------
    with tab_comp:
        st.subheader("⚔️ Comparativa Temporal de Períodos")
        st.info("Utilice los controles para comparar dos ventanas de tiempo independientes.")

    # -----------------------------------------------------------------------------
    # PESTAÑA: DETALLE
    # -----------------------------------------------------------------------------
    with tab_det:
        st.subheader("📋 Consolidado de Datos")
        st.dataframe(df_base[['RASES', 'UNIDAD DE ASIGNACIÓN', 'ESPECIALIDAD_CATEGORIA', 'Tipo de Solicitud']].head(100), use_container_width=True)