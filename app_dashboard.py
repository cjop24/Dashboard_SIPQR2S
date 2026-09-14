import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
import urllib.parse
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE PÁGINA RESPONSIVA (Mobile-First iOS)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard SIPQRS Móvil",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilos CSS estilo iOS Card para mobile
st.markdown("""
    <style>
    .main { padding: 0.5rem; }
    
    /* Tarjetas de métricas tipo iOS Card */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 12px 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        border: 1px solid #e5e7eb;
        margin-bottom: 8px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
        font-weight: 700;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        color: #4b5563;
        font-weight: 600;
    }

    h1 { font-size: 1.6rem !important; font-weight: 800; color: #0f172a; }
    h3 { font-size: 1.1rem !important; font-weight: 700; color: #1e293b; margin-top: 1rem; }
    </style>
""", unsafe_allow_html=True)

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
    st.warning("Ingrese sus credenciales corporativas")

elif authentication_status:
    # -----------------------------------------------------------------------------
    # 3. CONEXIÓN A BASE DE DATOS Y CACHÉ
    # -----------------------------------------------------------------------------
    try:
        DB_USER = st.secrets["postgres"]["user"]
        DB_PASS = st.secrets["postgres"]["password"]
        DB_HOST = st.secrets["postgres"]["host"]
        DB_PORT = st.secrets["postgres"]["port"]
        DB_NAME = st.secrets["postgres"]["dbname"]
    except Exception:
        DB_USER = "postgres.gsszvzxswzkqsnajimij"
        DB_PASS = ""
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
        st.error(f"Error cargando base de datos: {e}")
        st.stop()

    # -----------------------------------------------------------------------------
    # 4. SEGMENTADORES INTERACTIVOS (SIDEBAR)
    # -----------------------------------------------------------------------------
    st.sidebar.write(f"👤 **{name}**")
    authenticator.logout('Cerrar Sesión', 'sidebar')
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filtros de Consulta")

    # Segmentador de Categorías Salud
    cat_counts = df_raw['ESPECIALIDAD_CATEGORIA'].value_counts()
    opciones_cat = [f"{cat} ({count:,})" for cat, count in cat_counts.items() if cat != '']
    mapa_cat = {f"{cat} ({count:,})": cat for cat, count in cat_counts.items() if cat != ''}

    sel_cat_display = st.sidebar.multiselect("Categoría Salud / Especialidad", options=opciones_cat, placeholder="Buscar categoría...")
    sel_cat = [mapa_cat[item] for item in sel_cat_display]

    # Filtros estructurales
    lista_rases = sorted([x for x in df_raw['RASES'].dropna().unique() if x != ''])
    sel_rases = st.sidebar.multiselect("RASES", options=lista_rases)

    df_filtered_unidad = df_raw[df_raw['RASES'].isin(sel_rases)] if sel_rases else df_raw
    lista_unidades = sorted([x for x in df_filtered_unidad['UNIDAD DE ASIGNACIÓN'].dropna().unique() if x != ''])
    sel_unidades = st.sidebar.multiselect("Unidad de Asignación (UPRES)", options=lista_unidades)

    lista_tipos = sorted([x for x in df_raw['Tipo de Solicitud'].dropna().unique() if x != ''])
    sel_tipos = st.sidebar.multiselect("Tipo de Solicitud", options=lista_tipos)

    # Aplicar filtros base (Especialidad, RASES, Unidad, Tipo)
    df_base = df_raw.copy()
    if sel_cat: df_base = df_base[df_base['ESPECIALIDAD_CATEGORIA'].isin(sel_cat)]
    if sel_rases: df_base = df_base[df_base['RASES'].isin(sel_rases)]
    if sel_unidades: df_base = df_base[df_base['UNIDAD DE ASIGNACIÓN'].isin(sel_unidades)]
    if sel_tipos: df_base = df_base[df_base['Tipo de Solicitud'].isin(sel_tipos)]

    # -----------------------------------------------------------------------------
    # 5. VISTA PRINCIPAL (PESTAÑAS OPTIMIZADAS PARA MÓVIL)
    # -----------------------------------------------------------------------------
    st.title("🛡️ SIPQRS Sanidad")
    st.caption("Consola Ejecutiva de Atención al Usuario")

    tab_resumen, tab_comparativo, tab_detalle = st.tabs(["📊 Resumen", "🔄 Comparador de Periodos", "📋 Detalle"])

    # -----------------------------------------------------------------------------
    # PESTAÑA 1: RESUMEN GENERAL
    # -----------------------------------------------------------------------------
    with tab_resumen:
        min_f = df_base['fecha_dt'].min().date() if not df_base.empty else None
        max_f = df_base['fecha_dt'].max().date() if not df_base.empty else None
        rango_general = st.date_input("Filtrar Rango del Resumen", value=(min_f, max_f), min_value=min_f, max_value=max_f)
        
        df_resumen = df_base.copy()
        if len(rango_general) == 2:
            df_resumen = df_resumen[(df_resumen['fecha_dt'].dt.date >= rango_general[0]) & (df_resumen['fecha_dt'].dt.date <= rango_general[1])]

        kpi1, kpi2 = st.columns(2)
        kpi1.metric("Total Tickets", f"{len(df_resumen):,}")
        kpi2.metric("Unidades Activas", f"{df_resumen['UNIDAD DE ASIGNACIÓN'].nunique():,}")

        kpi3, kpi4 = st.columns(2)
        kpi3.metric("Especialidades", f"{df_resumen['ESPECIALIDAD_CATEGORIA'].nunique():,}")
        kpi4.metric("Solicitudes", f"{df_resumen['Tipo de Solicitud'].nunique():,}")

        st.markdown("---")

        st.subheader("🩺 Top 7 Especialidades")
        df_esp = df_resumen['ESPECIALIDAD_CATEGORIA'].value_counts().head(7).reset_index()
        df_esp.columns = ['Especialidad', 'Cantidad']
        fig_esp = px.bar(df_esp, y='Especialidad', x='Cantidad', orientation='h', text_auto=True, color_discrete_sequence=['#2e7d32'])
        fig_esp.update_layout(yaxis=dict(autorange="reversed"), height=320, margin=dict(l=5, r=5, t=10, b=10))
        st.plotly_chart(fig_esp, use_container_width=True, config={'displayModeBar': False})

    # -----------------------------------------------------------------------------
    # PESTAÑA 2: COMPARADOR ENTRE DOS PERIODOS (NUEVA FUNCIONALIDAD)
    # -----------------------------------------------------------------------------
    with tab_comparativo:
        st.subheader("⚔️ Comparativo entre Periodos")
        st.caption("Selecciona los dos rangos de tiempo que deseas contrastar.")

        min_hist = df_raw['fecha_dt'].min().date()
        max_hist = df_raw['fecha_dt'].max().date()

        # En iPhone, colocamos los selectores en 2 columnas compactas
        col_pA, col_pB = st.columns(2)

        with col_pA:
            st.markdown("**📅 Periodo A (Base)**")
            f_inicio_a = st.date_input("Inicio A", value=pd.to_datetime("2025-08-08").date(), min_value=min_hist, max_value=max_hist, key="pa_start")
            f_fin_a = st.date_input("Fin A", value=pd.to_datetime("2025-08-14").date(), min_value=min_hist, max_value=max_hist, key="pa_end")

        with col_pB:
            st.markdown("**📅 Periodo B (Comparado)**")
            f_inicio_b = st.date_input("Inicio B", value=pd.to_datetime("2025-09-08").date(), min_value=min_hist, max_value=max_hist, key="pb_start")
            f_fin_b = st.date_input("Fin B", value=pd.to_datetime("2025-09-14").date(), min_value=min_hist, max_value=max_hist, key="pb_end")

        # Filtrar DataFrames
        df_pa = df_base[(df_base['fecha_dt'].dt.date >= f_inicio_a) & (df_base['fecha_dt'].dt.date <= f_fin_a)]
        df_pb = df_base[(df_base['fecha_dt'].dt.date >= f_inicio_b) & (df_base['fecha_dt'].dt.date <= f_fin_b)]

        cnt_pa = len(df_pa)
        cnt_pb = len(df_pb)
        diff_abs = cnt_pb - cnt_pa
        diff_pct = ((cnt_pb - cnt_pa) / cnt_pa * 100) if cnt_pa > 0 else 0

        st.markdown("---")

        # Tarjetas comparativas con Deltas
        st.markdown("##### 📊 Resultado General del Comparativo")
        comp_col1, comp_col2 = st.columns(2)

        comp_col1.metric(
            label=f"Periodo A ({f_inicio_a.strftime('%d/%m')} - {f_fin_a.strftime('%d/%m')})",
            value=f"{cnt_pa:,} tickets"
        )
        
        comp_col2.metric(
            label=f"Periodo B ({f_inicio_b.strftime('%d/%m')} - {f_fin_b.strftime('%d/%m')})",
            value=f"{cnt_pb:,} tickets",
            delta=f"{diff_abs:+} tickets ({diff_pct:+.1f}%)",
            delta_color="inverse"  # En salud/reclamos, un aumento suele ser alerta (rojo) y reducción verde
        )

        # Gráfico comparativo de barras agrupadas por Especialidades Top 5
        st.markdown("##### 🩺 Comparativa por Top 5 Especialidades")
        
        top_esp_a = df_pa['ESPECIALIDAD_CATEGORIA'].value_counts().head(5)
        top_esp_b = df_pb['ESPECIALIDAD_CATEGORIA'].value_counts().head(5)
        
        # Combinar índices para el gráfico
        esp_combinadas = list(set(top_esp_a.index).union(set(top_esp_b.index)))
        
        df_graf_comp = pd.DataFrame({
            'Especialidad': esp_combinadas,
            'Periodo A': [df_pa[df_pa['ESPECIALIDAD_CATEGORIA'] == e].shape[0] for e in esp_combinadas],
            'Periodo B': [df_pb[df_pb['ESPECIALIDAD_CATEGORIA'] == e].shape[0] for e in esp_combinadas]
        }).sort_values(by='Periodo B', ascending=False)

        fig_comp_esp = go.Figure(data=[
            go.Bar(name='Periodo A', x=df_graf_comp['Especialidad'], y=df_graf_comp['Periodo A'], marker_color='#81c784', text=df_graf_comp['Periodo A'], textposition='auto'),
            go.Bar(name='Periodo B', x=df_graf_comp['Especialidad'], y=df_graf_comp['Periodo B'], marker_color='#1b5e20', text=df_graf_comp['Periodo B'], textposition='auto')
        ])
        
        fig_comp_esp.update_layout(
            barmode='group',
            height=340,
            margin=dict(l=5, r=5, t=10, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_comp_esp, use_container_width=True, config={'displayModeBar': False})

    # -----------------------------------------------------------------------------
    # PESTAÑA 3: DETALLE
    # -----------------------------------------------------------------------------
    with tab_detalle:
        st.subheader("📋 Resumen por Unidad de Asignación")
        df_tabla = df_base.groupby(['UNIDAD DE ASIGNACIÓN', 'RASES']).size().reset_index(name='Total Reclamos')
        df_tabla = df_tabla.sort_values(by='Total Reclamos', ascending=False)
        st.dataframe(df_tabla, use_container_width=True, hide_index=True)