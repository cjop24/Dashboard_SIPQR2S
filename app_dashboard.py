import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
import urllib.parse
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import re

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN RESPONSIVA (Mobile-First / iOS Friendly)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard SIPQR2S",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilos CSS estilo iOS Card para mobile
st.markdown("""
    <style>
    .main { padding: 0.5rem; }
    
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 10px 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        border: 1px solid #e5e7eb;
        margin-bottom: 6px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.3rem !important;
        font-weight: 700;
        color: #1b5e20;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.78rem !important;
        color: #4b5563;
        font-weight: 600;
    }

    h1 { font-size: 1.5rem !important; font-weight: 800; color: #0f172a; }
    h3 { font-size: 1.05rem !important; font-weight: 700; color: #1e293b; margin-top: 0.8rem; }
    </style>
""", unsafe_allow_html=True)

# Función para fijar los ejes y deshabilitar gestos táctiles de zoom molesto en móviles
def aplicar_touch_safe(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig

# Función para acortar textos mediante abreviaturas y eliminación estricta de artículos/preposiciones
def acortar_texto_abreviado(texto):
    if pd.isna(texto) or not texto:
        return "N/A"
    s = str(texto).upper().strip()
    
    # 1. Eliminar artículos, preposiciones y conectores
    preposiciones_y_articulos = r'\b(DE|DEL|LA|EL|LOS|LAS|EN|POR|CON|SIN|PARA|SOBRE|ANTE|A|Y|O|U|AL|UN|UNO|UNAS|UNOS|SU|SUS)\b'
    s = re.sub(preposiciones_y_articulos, ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    
    # 2. Reemplazo por abreviaturas corporativas y médicas
    abrev = {
        'INSATISFACCION': 'INSATISF.',
        'INSATISFACCIÓN': 'INSATISF.',
        'RELACIONADA': 'RELAC.',
        'ATENCION': 'ATENC.',
        'ATENCIÓN': 'ATENC.',
        'PERSONAL': 'PERS.',
        'PROFESIONAL': 'PROF.',
        'ADMINISTRATIVO': 'ADMIN.',
        'ADMINISTRATIVA': 'ADMIN.',
        'AUTORIZACION': 'AUTORIZ.',
        'AUTORIZACIÓN': 'AUTORIZ.',
        'MEDICAMENTOS': 'MEDICAM.',
        'ESPECIALIDAD': 'ESPEC.',
        'ESPECIALIDADES': 'ESPEC.',
        'PROCEDIMIENTOS': 'PROCED.',
        'INFRAESTRUCTURA': 'INFRAESTR.',
        'OPORTUNIDAD': 'OPORT.',
        'SERVICIO': 'SERV.',
        'SERVICIOS': 'SERV.',
        'SOLICITUD': 'SOLICIT.',
        'SOLICITUDES': 'SOLICIT.',
        'PRESTACION': 'PREST.',
        'PRESTACIÓN': 'PREST.',
        'USUARIO': 'USUAR.',
        'USUARIOS': 'USUAR.'
    }
    
    words = s.split()
    words_clean = [abrev.get(w, w) for w in words]
    return " ".join(words_clean)

CONFIG_PLOTLY_TOUCH = {
    'displayModeBar': False,
    'scrollZoom': False,
    'doubleClick': False,
    'showAxisDragHandles': False
}

# Coordenadas geográficas para UPRES en Colombia
GEO_DEPARTAMENTOS_COL = {
    'BOGOTA': [4.6097, -74.0817], 'BOGOTÁ': [4.6097, -74.0817], 'ANTIOQUIA': [6.2442, -75.5812],
    'VALLE': [3.4516, -76.5320], 'VALLE DEL CAUCA': [3.4516, -76.5320], 'ATLANTICO': [10.9685, -74.7813],
    'CUNDINAMARCA': [4.6097, -74.0817], 'SANTANDER': [7.1254, -73.1198], 'BOLIVAR': [10.3997, -75.5144],
    'BOYACA': [5.5353, -73.3678], 'CALDAS': [5.0689, -75.5174], 'CAUCA': [2.4448, -76.6147],
    'CESAR': [10.4631, -73.2532], 'CORDOBA': [8.7479, -75.8814], 'HUILA': [2.9273, -75.2819],
    'MAGDALENA': [11.2408, -74.1990], 'META': [4.1420, -73.6266], 'NARIÑO': [1.2136, -77.2811],
    'NORTE DE SANTANDER': [7.8939, -72.5078], 'QUINDIO': [4.5339, -75.6811], 'RISARALDA': [4.8133, -75.6961],
    'TOLIMA': [4.4389, -75.2322], 'AMAZONAS': [-4.2153, -69.9406], 'ARAUCA': [7.0847, -70.7591],
    'CASANARE': [5.3378, -72.3959], 'CHOCO': [5.6947, -76.6611], 'GUAINIA': [2.5819, -67.5819],
    'GUAVIARE': [2.5648, -72.6459], 'LA GUAJIRA': [11.5444, -72.9072], 'PUTUMAYO': [1.1496, -76.6461],
    'SAN ANDRES': [12.5847, -81.7006], 'SUCRE': [9.3047, -75.3978], 'VAUPES': [1.1983, -70.1733], 'VICHADA': [4.4234, -67.9239]
}

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

name, authentication_status, username = authenticator.login('main')

if authentication_status == False:
    st.error("Usuario o contraseña incorrectos")
elif authentication_status == None:
    st.warning("Por favor ingrese sus credenciales para acceder")

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
        df['dia_semana'] = df['fecha_dt'].dt.day_name()
        df['fecha_corta'] = df['fecha_dt'].dt.strftime('%Y-%m-%d')
        return df

    try:
        df_raw = cargar_datos_consolidados()
    except Exception as e:
        st.error(f"Error conectando a la base de datos: {e}")
        st.stop()

    # -----------------------------------------------------------------------------
    # 4. SEGMENTADORES ORDENADOS (1 AL 5)
    # -----------------------------------------------------------------------------
    st.sidebar.write(f"👤 **{name}**")
    authenticator.logout('Cerrar Sesión', 'sidebar')
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filtros de Control")

    # 1. Rango de Fecha de Creación
    min_f = df_raw['fecha_dt'].min().date() if not df_raw.empty else None
    max_f = df_raw['fecha_dt'].max().date() if not df_raw.empty else None
    rango_fechas = st.sidebar.date_input("1. Rango de Fecha de Creación", value=(min_f, max_f), min_value=min_f, max_value=max_f) if min_f else []

    df_temp_fecha = df_raw.copy()
    if len(rango_fechas) == 2:
        df_temp_fecha = df_temp_fecha[(df_temp_fecha['fecha_dt'].dt.date >= rango_fechas[0]) & (df_temp_fecha['fecha_dt'].dt.date <= rango_fechas[1])]

    # 2. UPRES
    lista_unidades = sorted([x for x in df_raw['UNIDAD DE ASIGNACIÓN'].dropna().unique() if str(x).strip() != ''])
    sel_unidades = st.sidebar.multiselect("2. UPRES", options=lista_unidades)

    # 3. RASES
    lista_rases = sorted([x for x in df_raw['RASES'].dropna().unique() if str(x).strip() != ''])
    sel_rases = st.sidebar.multiselect("3. RASES", options=lista_rases)

    # 4. Categoría Salud (Organizada de mayor a menor frecuencia)
    cat_ordenadas = df_temp_fecha['ESPECIALIDAD_CATEGORIA'].value_counts().index.tolist()
    cat_ordenadas = [c for c in cat_ordenadas if str(c).strip() != '']
    sel_cat = st.sidebar.multiselect("4. Categoría Salud", options=cat_ordenadas, placeholder="Seleccione categoría...")

    # 5. Motivo Específico (Organizado de mayor a menor frecuencia)
    col_mot_esp = 'MOTIVO ESPECÍFICO' if 'MOTIVO ESPECÍFICO' in df_raw.columns else 'MOTIVO GENERAL'
    motivos_ordenados = df_temp_fecha[col_mot_esp].value_counts().index.tolist()
    motivos_ordenados = [m for m in motivos_ordenados if str(m).strip() != '']
    sel_motivos = st.sidebar.multiselect("5. Motivo Específico", options=motivos_ordenados, placeholder="Seleccione motivo...")

    # Aplicar filtrado final
    df_base = df_raw.copy()
    if len(rango_fechas) == 2:
        df_base = df_base[(df_base['fecha_dt'].dt.date >= rango_fechas[0]) & (df_base['fecha_dt'].dt.date <= rango_fechas[1])]
    if sel_unidades:
        df_base = df_base[df_base['UNIDAD DE ASIGNACIÓN'].isin(sel_unidades)]
    if sel_rases:
        df_base = df_base[df_base['RASES'].isin(sel_rases)]
    if sel_cat:
        df_base = df_base[df_base['ESPECIALIDAD_CATEGORIA'].isin(sel_cat)]
    if sel_motivos:
        df_base = df_base[df_base[col_mot_esp].isin(sel_motivos)]

    # -----------------------------------------------------------------------------
    # 5. VISTA PRINCIPAL (PESTAÑAS)
    # -----------------------------------------------------------------------------
    st.title("🛡️ SIPQR2S Sanidad")

    tab_ind, tab_comp, tab_det = st.tabs(["📊 Análisis Individual", "🔄 Comparativo", "📋 Detalle"])

    with tab_ind:
        st.caption("Consola Ejecutiva de Atención al Usuario")

        # Tarjetas KPI
        top_upres_s = df_base['UNIDAD DE ASIGNACIÓN'].value_counts()
        top_upres_nom = top_upres_s.index[0] if not top_upres_s.empty else "N/A"
        top_upres_val = top_upres_s.iloc[0] if not top_upres_s.empty else 0

        top_rases_s = df_base['RASES'].value_counts()
        top_rases_nom = top_rases_s.index[0] if not top_rases_s.empty else "N/A"
        top_rases_val = top_rases_s.iloc[0] if not top_rases_s.empty else 0

        top_dia_s = df_base['fecha_corta'].value_counts()
        top_dia_nom = top_dia_s.index[0] if not top_dia_s.empty else "N/A"
        top_dia_val = top_dia_s.iloc[0] if not top_dia_s.empty else 0

        k1, k2 = st.columns(2)
        k1.metric("Total SIPQR2S País", f"{len(df_base):,}")
        k1_cat = df_base['ESPECIALIDAD_CATEGORIA'].value_counts()
        cat_top_name = k1_cat.index[0] if not k1_cat.empty else "N/A"
        k2.metric("Categoría con más SIPQR2S", acortar_texto_abreviado(cat_top_name), delta=f"{k1_cat.iloc[0] if not k1_cat.empty else 0:,} tickets", delta_color="off")

        k3, k4, k5 = st.columns(3)
        k3.metric("UPRES con más SIPQR2S", acortar_texto_abreviado(top_upres_nom), delta=f"{top_upres_val:,} tickets", delta_color="off")
        k4.metric("RASES con más SIPQR2S", acortar_texto_abreviado(top_rases_nom), delta=f"{top_rases_val:,} tickets", delta_color="off")
        k5.metric("Día con más SIPQR2S", f"{top_dia_nom}", delta=f"{top_dia_val:,} tickets", delta_color="off")

        st.markdown("---")

        # Gráfico 1: Mapa Geográfico de Colombia por UPRES
        st.subheader("🗺️ Distribución Geográfica SIPQR2S por UPRES")
        df_geo = df_base.groupby('UNIDAD DE ASIGNACIÓN').size().reset_index(name='Cantidad')
        
        lats, lons = [], []
        for u in df_geo['UNIDAD DE ASIGNACIÓN']:
            matched = False
            for dep, coords in GEO_DEPARTAMENTOS_COL.items():
                if dep in str(u).upper():
                    lats.append(coords[0])
                    lons.append(coords[1])
                    matched = True
                    break
            if not matched:
                lats.append(4.6097)
                lons.append(-74.0817)

        df_geo['lat'] = lats
        df_geo['lon'] = lons
        
        fig_mapa = px.scatter_map(
            df_geo, 
            lat='lat', 
            lon='lon', 
            size='Cantidad', 
            hover_name='UNIDAD DE ASIGNACIÓN',
            hover_data={'Cantidad': True, 'lat': False, 'lon': False},
            color='Cantidad',
            color_continuous_scale=px.colors.sequential.Greens,
            zoom=4.5,
            center={"lat": 4.5709, "lon": -74.2973},
            map_style="carto-positron"
        )
        fig_mapa.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(aplicar_touch_safe(fig_mapa), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

        # Gráfico 2: SIPQR2S por Día con Tendencia
        st.subheader("📈 Comportamiento Diario de SIPQR2S")
        df_dia = df_base.groupby(['fecha_dt', 'fecha_corta']).size().reset_index(name='Cantidad').sort_values('fecha_dt')
        
        if not df_dia.empty:
            fig_dia = go.Figure()
            fig_dia.add_trace(go.Scatter(
                x=df_dia['fecha_corta'],
                y=df_dia['Cantidad'],
                mode='lines+markers',
                name='Tickets Diarios',
                line=dict(color='#2e7d32', width=2),
                marker=dict(size=6, color='#1b5e20')
            ))
            
            if len(df_dia) > 1:
                x_vals = np.arange(len(df_dia))
                y_vals = df_dia['Cantidad'].values
                m, b = np.polyfit(x_vals, y_vals, 1)
                trend_line = m * x_vals + b
                
                fig_dia.add_trace(go.Scatter(
                    x=df_dia['fecha_corta'],
                    y=trend_line,
                    mode='lines',
                    name='Tendencia Periodo',
                    line=dict(color='#d32f2f', width=2, dash='dash')
                ))
            
            fig_dia.update_layout(
                xaxis_title="", yaxis_title="", height=300,
                margin=dict(l=5, r=5, t=10, b=10),
                legend=dict(orientation="h", y=1.1, x=0.8)
            )
            st.plotly_chart(aplicar_touch_safe(fig_dia), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

        # Gráfico 3: SIPQR2S por RASES
        st.subheader("📍 SIPQR2S por RASES")
        df_g1 = df_base['RASES'].value_counts().reset_index()
        df_g1.columns = ['RASES', 'Cantidad']
        df_g1['RASES_fmt'] = df_g1['RASES'].apply(acortar_texto_abreviado)
        fig1 = px.bar(df_g1, x='RASES_fmt', y='Cantidad', text_auto=True, color_discrete_sequence=['#2e7d32'])
        fig1.update_layout(xaxis_title="", yaxis_title="", height=300, margin=dict(l=5, r=5, t=10, b=10))
        st.plotly_chart(aplicar_touch_safe(fig1), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

        # -----------------------------------------------------------------------------
        # SECCIÓN DINÁMICA DE UPRES APILADO (SELECTOR EN MÓVIL)
        # -----------------------------------------------------------------------------
        st.subheader("🏢 Distribución por UPRES (Top 10)")
        
        dim_apilamiento = st.radio(
            "Seleccione dimensión de apilamiento:",
            ["Categoría Salud", "Motivo Específico"],
            horizontal=True
        )

        top_10_upres = df_base['UNIDAD DE ASIGNACIÓN'].value_counts().head(10).index
        df_g2 = df_base[df_base['UNIDAD DE ASIGNACIÓN'].isin(top_10_upres)]

        if dim_apilamiento == "Categoría Salud":
            df_stack = df_g2.groupby(['UNIDAD DE ASIGNACIÓN', 'ESPECIALIDAD_CATEGORIA']).size().reset_index(name='Cantidad')
            df_stack['UPRES_fmt'] = df_stack['UNIDAD DE ASIGNACIÓN'].apply(acortar_texto_abreviado)
            df_stack['Grupo_fmt'] = df_stack['ESPECIALIDAD_CATEGORIA'].apply(acortar_texto_abreviado)
            palette = px.colors.qualitative.Prism
        else:
            df_stack = df_g2.groupby(['UNIDAD DE ASIGNACIÓN', col_mot_esp]).size().reset_index(name='Cantidad')
            df_stack['UPRES_fmt'] = df_stack['UNIDAD DE ASIGNACIÓN'].apply(acortar_texto_abreviado)
            df_stack['Grupo_fmt'] = df_stack[col_mot_esp].apply(acortar_texto_abreviado)
            palette = px.colors.qualitative.Safe

        fig_stack = px.bar(
            df_stack, 
            y='UPRES_fmt', 
            x='Cantidad', 
            color='Grupo_fmt', 
            orientation='h',
            color_discrete_sequence=palette
        )
        fig_stack.update_layout(
            barmode='stack',
            yaxis=dict(autorange="reversed"), 
            xaxis_title="", yaxis_title="", 
            height=440, 
            margin=dict(l=5, r=5, t=10, b=10),
            legend=dict(
                orientation="h", 
                y=-0.25, 
                x=0,
                title=None,
                font=dict(size=10)
            )
        )
        st.plotly_chart(aplicar_touch_safe(fig_stack), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

        st.markdown("---")

        # Gráficos de Torta de Porcentajes
        col_t1, col_t2 = st.columns(2)

        with col_t1:
            st.subheader("🍰 Porcentaje (%) por Tipo de Solicitud")
            df_pie_sol = df_base['Tipo de Solicitud'].value_counts().reset_index()
            df_pie_sol.columns = ['Tipo', 'Cantidad']
            fig_pie1 = px.pie(df_pie_sol, values='Cantidad', names='Tipo', hole=0.4, color_discrete_sequence=px.colors.sequential.Greens_r)
            fig_pie1.update_layout(height=300, margin=dict(l=5, r=5, t=10, b=10), legend=dict(orientation="h", y=-0.15))
            st.plotly_chart(aplicar_touch_safe(fig_pie1), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

        with col_t2:
            st.subheader("🍩 Porcentaje (%) por Medio de Recepción")
            df_pie_med = df_base['Medio de Recepción'].value_counts().reset_index()
            df_pie_med.columns = ['Medio', 'Cantidad']
            fig_pie2 = px.pie(df_pie_med, values='Cantidad', names='Medio', hole=0.4, color_discrete_sequence=px.colors.sequential.YlGn_r)
            fig_pie2.update_layout(height=300, margin=dict(l=5, r=5, t=10, b=10), legend=dict(orientation="h", y=-0.15))
            st.plotly_chart(aplicar_touch_safe(fig_pie2), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

    with tab_comp:
        st.subheader("⚔️ Comparativo de Periodos")
        st.info("Utilice los filtros para comparar diferentes ventanas de tiempo.")

    with tab_det:
        st.subheader("📋 Consolidado de Datos")
        st.dataframe(df_base[['RASES', 'UNIDAD DE ASIGNACIÓN', 'ESPECIALIDAD_CATEGORIA', 'Tipo de Solicitud', 'Medio de Recepción']].head(100), use_container_width=True)