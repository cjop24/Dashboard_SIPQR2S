import os
import json
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
from dotenv import load_dotenv

# Cargar variables de entorno desde .env local
load_dotenv()

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN RESPONSIVA (Mobile-First / iOS Friendly)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard SIPQR2S",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilos CSS con Word-Wrap en Filtros Desplegables de la Barra Lateral
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

    /* Ajuste para visualizar textos largos completos en los desplegables (Multiselect) */
    div[data-baseweb="select"] ul {
        max-width: 90vw !important;
    }
    div[data-baseweb="select"] li {
        white-space: normal !important;
        word-break: break-word !important;
        line-height: 1.3 !important;
        padding-top: 8px !important;
        padding-bottom: 8px !important;
    }
    div[data-baseweb="tag"] {
        max-width: 100% !important;
    }
    div[data-baseweb="tag"] span {
        white-space: normal !important;
        word-break: break-word !important;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. FUNCIONES AUXILIARES Y FORMATO
# -----------------------------------------------------------------------------
ARCH_PREFERENCIAS = "preferencias_usuario.json"

COLOR_PERIODO_A = '#2e7d32'  # Verde RASES
COLOR_PERIODO_B = '#c62828'  # Rojo RASES

def cargar_preferencias():
    if os.path.exists(ARCH_PREFERENCIAS):
        try:
            with open(ARCH_PREFERENCIAS, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def guardar_preferencias(data):
    try:
        with open(ARCH_PREFERENCIAS, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def aplicar_touch_safe(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig

def acortar_texto_abreviado(texto):
    if pd.isna(texto) or not texto:
        return "N/A"
    s = str(texto).upper().strip()
    
    preposiciones_y_articulos = r'\b(DE|DEL|LA|EL|LOS|LAS|EN|POR|CON|SIN|PARA|SOBRE|ANTE|A|Y|O|U|AL|UN|UNO|UNAS|UNOS|SU|SUS)\b'
    s = re.sub(preposiciones_y_articulos, ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    
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

def generar_grafico_upres_apilado(df_base, col_target, titulo_grafico):
    st.subheader(titulo_grafico)
    
    df_filtrado = df_base.dropna(subset=['UNIDAD DE ASIGNACIÓN', col_target]).copy()
    df_filtrado = df_filtrado[
        (df_filtrado['UNIDAD DE ASIGNACIÓN'].astype(str).str.strip() != '') &
        (df_filtrado[col_target].astype(str).str.strip() != '')
    ]
    
    if df_filtrado.empty:
        st.info("No hay datos disponibles para generar esta gráfica.")
        return

    top_10_upres = df_filtrado['UNIDAD DE ASIGNACIÓN'].value_counts().head(10).index.tolist()
    df_g2 = df_filtrado[df_filtrado['UNIDAD DE ASIGNACIÓN'].isin(top_10_upres)].copy()

    conteo_local = df_g2.groupby(['UNIDAD DE ASIGNACIÓN', col_target], observed=True).size().reset_index(name='Cant_Local')
    conteo_local['Rank_Local'] = conteo_local.groupby('UNIDAD DE ASIGNACIÓN')['Cant_Local'].rank(method='first', ascending=False)
    
    top_5_locales = conteo_local[conteo_local['Rank_Local'] <= 5].copy()

    df_stack = top_5_locales.groupby(['UNIDAD DE ASIGNACIÓN', col_target], observed=True)['Cant_Local'].sum().reset_index(name='Cantidad')
    df_stack['UPRES_fmt'] = df_stack['UNIDAD DE ASIGNACIÓN'].apply(acortar_texto_abreviado)
    df_stack['Grupo_fmt'] = df_stack[col_target].apply(acortar_texto_abreviado)
    
    upres_ordenadas_fmt = [acortar_texto_abreviado(u) for u in top_10_upres]
    df_totales = df_stack.groupby('UPRES_fmt', observed=True)['Cantidad'].sum().reset_index(name='Total')

    categorias_unicas = df_stack['Grupo_fmt'].unique().tolist()

    paleta_contraste = [
        '#1b4332', '#2d6a4f', '#40916c', '#1d3557', 
        '#2b2d42', '#d4a373', '#52b788', '#003049', '#e07a5f', '#3d405b'
    ]
    
    color_map = {}
    for idx, cat in enumerate(categorias_unicas):
        color_map[cat] = paleta_contraste[idx % len(paleta_contraste)]

    fig_stack = px.bar(
        df_stack, 
        y='UPRES_fmt', 
        x='Cantidad', 
        color='Grupo_fmt', 
        orientation='h', 
        category_orders={
            'UPRES_fmt': upres_ordenadas_fmt,
            'Grupo_fmt': categorias_unicas
        },
        color_discrete_map=color_map
    )
    
    fig_stack.add_trace(go.Scatter(
        y=df_totales['UPRES_fmt'], 
        x=df_totales['Total'], 
        mode='text', 
        text=df_totales['Total'].apply(lambda v: f" <b>{v:,}</b>"), 
        textposition='middle right', 
        showlegend=False, 
        hoverinfo='skip'
    ))
    
    fig_stack.update_layout(
        barmode='stack', 
        xaxis_title="", 
        yaxis_title="", 
        height=480, 
        margin=dict(l=5, r=40, t=10, b=10), 
        legend=dict(orientation="h", y=-0.25, x=0, title=None, font=dict(size=10))
    )
    st.plotly_chart(aplicar_touch_safe(fig_stack), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

def generar_grafico_upres_comparativo_top5(df_a, df_b, col_target, titulo_grafico, lbl_a="Periodo A", lbl_b="Periodo B"):
    st.subheader(titulo_grafico)
    
    # 1. Limpieza de datos
    df_a_clean = df_a.dropna(subset=['UNIDAD DE ASIGNACIÓN', col_target]).copy()
    df_b_clean = df_b.dropna(subset=['UNIDAD DE ASIGNACIÓN', col_target]).copy()

    df_a_clean = df_a_clean[
        (df_a_clean['UNIDAD DE ASIGNACIÓN'].astype(str).str.strip() != '') &
        (df_a_clean[col_target].astype(str).str.strip() != '')
    ]
    df_b_clean = df_b_clean[
        (df_b_clean['UNIDAD DE ASIGNACIÓN'].astype(str).str.strip() != '') &
        (df_b_clean[col_target].astype(str).str.strip() != '')
    ]

    # 2. Ranking Top 5 local por UPRES para Periodo A
    cA = df_a_clean.groupby(['UNIDAD DE ASIGNACIÓN', col_target], observed=True).size().reset_index(name='Cant')
    cA['Rank'] = cA.groupby('UNIDAD DE ASIGNACIÓN')['Cant'].rank(method='first', ascending=False)
    top5_a = cA[cA['Rank'] <= 5].groupby('UNIDAD DE ASIGNACIÓN', observed=True)['Cant'].sum().reset_index(name='Suma_Top5')

    # 3. Ranking Top 5 local por UPRES para Periodo B
    cB = df_b_clean.groupby(['UNIDAD DE ASIGNACIÓN', col_target], observed=True).size().reset_index(name='Cant')
    cB['Rank'] = cB.groupby('UNIDAD DE ASIGNACIÓN')['Cant'].rank(method='first', ascending=False)
    top5_b = cB[cB['Rank'] <= 5].groupby('UNIDAD DE ASIGNACIÓN', observed=True)['Cant'].sum().reset_index(name='Suma_Top5')

    # 4. Seleccionar las 5 UPRES principales con mayor volumen conjunto
    totales_upres = pd.merge(top5_a, top5_b, on='UNIDAD DE ASIGNACIÓN', how='outer').fillna(0)
    totales_upres['Total_Top5'] = totales_upres['Suma_Top5_x'] + totales_upres['Suma_Top5_y']
    
    if totales_upres.empty:
        st.info("No hay datos disponibles para la comparación.")
        return

    top_5_upres = totales_upres.sort_values('Total_Top5', ascending=False).head(5)['UNIDAD DE ASIGNACIÓN'].tolist()

    # 5. Construir dataset apilado detallado garantizando el orden de izquierda a derecha (Top 1 a Top 5)
    def procesar_periodo_top(df_in, etiqueta_periodo):
        df_sub = df_in[df_in['UNIDAD DE ASIGNACIÓN'].isin(top_5_upres)].copy()
        conteo = df_sub.groupby(['UNIDAD DE ASIGNACIÓN', col_target], observed=True).size().reset_index(name='Cantidad')
        conteo['Rank'] = conteo.groupby('UNIDAD DE ASIGNACIÓN')['Cantidad'].rank(method='first', ascending=False)
        top_local = conteo[conteo['Rank'] <= 5].copy()
        top_local['Top_Etiqueta'] = top_local['Rank'].astype(int).apply(lambda r: f"Top {r}")
        top_local['Periodo'] = etiqueta_periodo
        top_local['UPRES_fmt'] = top_local['UNIDAD DE ASIGNACIÓN'].apply(lambda x: str(acortar_texto_abreviado(x)))
        top_local['Categoria_fmt'] = top_local[col_target].apply(lambda x: str(acortar_texto_abreviado(x)))
        return top_local

    df_stack_a = procesar_periodo_top(df_a_clean, lbl_a)
    df_stack_b = procesar_periodo_top(df_b_clean, lbl_b)

    upres_ordenadas_fmt = [str(acortar_texto_abreviado(u)) for u in reversed(top_5_upres)]
    
    orden_top = ['Top 1', 'Top 2', 'Top 3', 'Top 4', 'Top 5']

    fig_comp = go.Figure()

    colores_top = {
        'Top 1': '#1b4332',
        'Top 2': '#2d6a4f',
        'Top 3': '#40916c',
        'Top 4': '#52b788',
        'Top 5': '#74c69d'
    }

    for t in orden_top:
        sub_a = df_stack_a[df_stack_a['Top_Etiqueta'] == t]
        sub_b = df_stack_b[df_stack_b['Top_Etiqueta'] == t]
        
        # Barra superior: Periodo A
        fig_comp.add_trace(go.Bar(
            y=sub_a['UPRES_fmt'],
            x=sub_a['Cantidad'],
            name=f"{t} ({lbl_a})",
            orientation='h',
            text=sub_a['Top_Etiqueta'],
            textposition='inside',
            insidetextanchor='middle',
            customdata=sub_a[['Periodo', 'Categoria_fmt']],
            hovertemplate=f"<b>%{{y}} - {lbl_a}</b><br>%{{customdata[1]}} (%{{text}}): %{{x}} tickets<extra></extra>",
            marker=dict(color=colores_top[t], line=dict(color='#2e7d32', width=1.5)),
            offsetgroup=0
        ))
        
        # Barra inferior: Periodo B
        fig_comp.add_trace(go.Bar(
            y=sub_b['UPRES_fmt'],
            x=sub_b['Cantidad'],
            name=f"{t} ({lbl_b})",
            orientation='h',
            text=sub_b['Top_Etiqueta'],
            textposition='inside',
            insidetextanchor='middle',
            customdata=sub_b[['Periodo', 'Categoria_fmt']],
            hovertemplate=f"<b>%{{y}} - {lbl_b}</b><br>%{{customdata[1]}} (%{{text}}): %{{x}} tickets<extra></extra>",
            marker=dict(color=colores_top[t], line=dict(color='#c62828', width=1.5)),
            offsetgroup=1
        ))

    fig_comp.update_layout(
        barmode='stack',
        yaxis=dict(categoryorder='array', categoryarray=upres_ordenadas_fmt),
        xaxis_title="",
        yaxis_title="",
        height=520,
        margin=dict(l=5, r=5, t=10, b=10),
        showlegend=False
    )
    
    st.plotly_chart(aplicar_touch_safe(fig_comp), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

# -----------------------------------------------------------------------------
# 3. MÓDULOS DE RENDERIZADO
# -----------------------------------------------------------------------------
def render_tab_individual(df_base_global, col_mot_esp):
    st.caption("Consola Ejecutiva de Atención al Usuario - Periodo Único")

    min_f = df_base_global['fecha_dt'].min().date() if not df_base_global.empty else None
    max_f = df_base_global['fecha_dt'].max().date() if not df_base_global.empty else None
    
    col_fi1, col_fi2 = st.columns(2)
    with col_fi1:
        fecha_ind_inicio = st.date_input(
            "Fecha Inicio", 
            value=min_f, 
            min_value=min_f, 
            max_value=max_f,
            key="fecha_ind_inicio"
        )
    with col_fi2:
        fecha_ind_fin = st.date_input(
            "Fecha Fin", 
            value=max_f, 
            min_value=min_f, 
            max_value=max_f,
            key="fecha_ind_fin"
        )

    df_base = df_base_global.copy()
    if fecha_ind_inicio and fecha_ind_fin:
        if fecha_ind_inicio <= fecha_ind_fin:
            df_base = df_base[(df_base['fecha_dt'].dt.date >= fecha_ind_inicio) & (df_base['fecha_dt'].dt.date <= fecha_ind_fin)]
        else:
            st.warning("⚠️ La Fecha Inicio no puede ser posterior a la Fecha Fin.")

    top_upres_s = df_base['UNIDAD DE ASIGNACIÓN'].dropna().value_counts()
    top_upres_nom = top_upres_s.index[0] if not top_upres_s.empty else "N/A"
    top_upres_val = top_upres_s.iloc[0] if not top_upres_s.empty else 0

    top_rases_s = df_base['RASES'].dropna().value_counts()
    top_rases_nom = top_rases_s.index[0] if not top_rases_s.empty else "N/A"
    top_rases_val = top_rases_s.iloc[0] if not top_rases_s.empty else 0

    top_dia_s = df_base['fecha_corta'].dropna().value_counts()
    top_dia_nom = top_dia_s.index[0] if not top_dia_s.empty else "N/A"
    top_dia_val = top_dia_s.iloc[0] if not top_dia_s.empty else 0

    k1, k2 = st.columns(2)
    k1.metric("Total recepcionado", f"{len(df_base):,}")
    k1_cat = df_base['ESPECIALIDAD_CATEGORIA'].dropna().value_counts()
    cat_top_name = k1_cat.index[0] if not k1_cat.empty else "N/A"
    k2.metric("Especialidad más impactada", acortar_texto_abreviado(cat_top_name), delta=f"{k1_cat.iloc[0] if not k1_cat.empty else 0:,} tickets", delta_color="off")

    k3, k4, k5 = st.columns(3)
    k3.metric("RASES con más PQRS", acortar_texto_abreviado(top_rases_nom), delta=f"{top_rases_val:,} tickets", delta_color="off")
    k4.metric("UPRES con más PQRS", acortar_texto_abreviado(top_upres_nom), delta=f"{top_upres_val:,} tickets", delta_color="off")
    k5.metric("Día con más PQRS", f"{top_dia_nom}", delta=f"{top_dia_val:,} tickets", delta_color="off")

    st.markdown("---")

    st.subheader("MAPA: Distribución Geográfica SIPQR2S por UPRES")
    df_geo_base = df_base.dropna(subset=['UNIDAD DE ASIGNACIÓN'])
    df_geo = df_geo_base.groupby('UNIDAD DE ASIGNACIÓN', observed=True).size().reset_index(name='Cantidad')
    df_geo = df_geo[df_geo['Cantidad'] > 0]
    
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

    st.markdown("---")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.subheader("Porcentaje (%) por Tipo de Solicitud")
        df_pie_sol = df_base['Tipo de Solicitud'].dropna().value_counts().reset_index()
        df_pie_sol.columns = ['Tipo de Solicitud', 'Cantidad']
        df_pie_sol = df_pie_sol[df_pie_sol['Cantidad'] > 0]
        fig_pie1 = px.pie(df_pie_sol, values='Cantidad', names='Tipo de Solicitud', hole=0.4, color_discrete_sequence=px.colors.sequential.Greens_r)
        fig_pie1.update_layout(height=300, margin=dict(l=5, r=5, t=10, b=10), legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(aplicar_touch_safe(fig_pie1), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

    with col_t2:
        st.subheader("Porcentaje (%) por Medio de Recepción")
        df_pie_med = df_base['Medio de Recepción'].dropna().value_counts().reset_index()
        df_pie_med.columns = ['Medio de Recepción', 'Cantidad']
        df_pie_med = df_pie_med[df_pie_med['Cantidad'] > 0]
        fig_pie2 = px.pie(df_pie_med, values='Cantidad', names='Medio de Recepción', hole=0.4, color_discrete_sequence=px.colors.sequential.YlGn_r)
        fig_pie2.update_layout(height=300, margin=dict(l=5, r=5, t=10, b=10), legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(aplicar_touch_safe(fig_pie2), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

    st.markdown("---")

    st.subheader("SIPQR2S por RASES")
    df_g1_raw = df_base['RASES'].dropna().value_counts().reset_index()
    df_g1_raw.columns = ['RASES', 'Cantidad']
    df_g1 = df_g1_raw[(df_g1_raw['Cantidad'] > 0) & (df_g1_raw['RASES'].astype(str).str.strip() != '')].copy()
    df_g1['RASES_fmt'] = df_g1['RASES'].apply(acortar_texto_abreviado)
    
    fig1 = px.bar(df_g1, x='RASES_fmt', y='Cantidad', text_auto=',d', color_discrete_sequence=[COLOR_PERIODO_A])
    fig1.update_layout(xaxis_title="", yaxis_title="", height=300, margin=dict(l=5, r=5, t=10, b=10))
    st.plotly_chart(aplicar_touch_safe(fig1), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

    st.subheader("PQR2S por UPRES")
    df_u1_raw = df_base['UNIDAD DE ASIGNACIÓN'].dropna().value_counts().reset_index()
    df_u1_raw.columns = ['UPRES', 'Cantidad']
    df_u1 = df_u1_raw[(df_u1_raw['Cantidad'] > 0) & (df_u1_raw['UPRES'].astype(str).str.strip() != '')].copy()
    df_u1['UPRES_fmt'] = df_u1['UPRES'].apply(acortar_texto_abreviado)
    
    fig_upres_simple = px.bar(
        df_u1, 
        x='UPRES_fmt', 
        y='Cantidad', 
        text_auto=',d',
        color_discrete_sequence=[COLOR_PERIODO_A]
    )
    fig_upres_simple.update_layout(xaxis_title="", yaxis_title="", height=350, margin=dict(l=5, r=5, t=10, b=10))
    st.plotly_chart(aplicar_touch_safe(fig_upres_simple), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

    generar_grafico_upres_apilado(df_base, 'ESPECIALIDAD_CATEGORIA', "Distribución por UPRES - Categoría Salud (Top 5)")
    generar_grafico_upres_apilado(df_base, col_mot_esp, "Distribución por UPRES - Motivo Específico (Top 5)")


def render_tab_comparativo(df_base_global, col_mot_esp):
    st.caption("Comparación Analítica Cruzada entre dos Ventanas de Tiempo")

    min_hist = df_base_global['fecha_dt'].min().date() if not df_base_global.empty else None
    max_hist = df_base_global['fecha_dt'].max().date() if not df_base_global.empty else None

    # CONTROLES DE FECHAS
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.markdown("### Periodo A (Base)")
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            fecha_a_inicio = st.date_input("Fecha Inicio A", value=min_hist, min_value=min_hist, max_value=max_hist, key="fecha_a_inicio")
        with col_a2:
            fecha_a_fin = st.date_input("Fecha Fin A", value=min_hist + pd.Timedelta(days=30) if min_hist else max_hist, min_value=min_hist, max_value=max_hist, key="fecha_a_fin")

    with col_p2:
        st.markdown("### Periodo B (Comparado)")
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            fecha_b_inicio = st.date_input("Fecha Inicio B", value=max_hist - pd.Timedelta(days=30) if max_hist else min_hist, min_value=min_hist, max_value=max_hist, key="fecha_b_inicio")
        with col_b2:
            fecha_b_fin = st.date_input("Fecha Fin B", value=max_hist, min_value=min_hist, max_value=max_hist, key="fecha_b_fin")

    if fecha_a_inicio and fecha_a_fin and fecha_b_inicio and fecha_b_fin:
        if fecha_a_inicio > fecha_a_fin or fecha_b_inicio > fecha_b_fin:
            st.warning("⚠️ En uno de los periodos, la Fecha Inicio es mayor a la Fecha Fin.")
            return

        # RÓTULOS DINÁMICOS DE FECHAS PARA GRÁFICOS Y LEYENDAS
        lbl_a = f"Periodo A ({fecha_a_inicio.strftime('%d/%m/%Y')} – {fecha_a_fin.strftime('%d/%m/%Y')})"
        lbl_b = f"Periodo B ({fecha_b_inicio.strftime('%d/%m/%Y')} – {fecha_b_fin.strftime('%d/%m/%Y')})"
        vs_header = f"{fecha_a_inicio.strftime('%d/%m/%Y')} – {fecha_a_fin.strftime('%d/%m/%Y')} 🆚 {fecha_b_inicio.strftime('%d/%m/%Y')} – {fecha_b_fin.strftime('%d/%m/%Y')}"

        df_a = df_base_global[(df_base_global['fecha_dt'].dt.date >= fecha_a_inicio) & (df_base_global['fecha_dt'].dt.date <= fecha_a_fin)].copy()
        df_b = df_base_global[(df_base_global['fecha_dt'].dt.date >= fecha_b_inicio) & (df_base_global['fecha_dt'].dt.date <= fecha_b_fin)].copy()

        tot_a, tot_b = len(df_a), len(df_b)
        diff_abs = tot_b - tot_a
        diff_pct = ((diff_abs / tot_a) * 100) if tot_a > 0 else 0.0

        st.markdown("---")
        st.subheader(f"Indicadores Comparativos Generales ({vs_header})")
        kc1, kc2, kc3 = st.columns(3)
        kc1.metric(f"Total {lbl_a}", f"{tot_a:,}")
        kc2.metric(f"Total {lbl_b}", f"{tot_b:,}")
        
        kc3.metric(
            "Variación Periodo B vs A",
            f"{diff_abs:+,}",
            delta=f"{diff_abs:+,} tickets ({diff_pct:+.1f}%)",
            delta_color="inverse"
        )

        st.markdown("---")

        mapa_color_comp = {lbl_a: COLOR_PERIODO_A, lbl_b: COLOR_PERIODO_B}

        # TIPO DE SOLICITUD Y MEDIO DE RECEPCIÓN
        col_cp1, col_cp2 = st.columns(2)
        with col_cp1:
            st.subheader(f"Comparativo Tipo de Solicitud ({vs_header})")
            df_ts_a = df_a['Tipo de Solicitud'].dropna().value_counts().reset_index()
            df_ts_a.columns = ['Tipo de Solicitud', lbl_a]
            
            df_ts_b = df_b['Tipo de Solicitud'].dropna().value_counts().reset_index()
            df_ts_b.columns = ['Tipo de Solicitud', lbl_b]
            
            df_ts_comp = pd.merge(df_ts_a, df_ts_b, on='Tipo de Solicitud', how='outer').fillna(0)
            df_ts_comp['Total_Volume'] = df_ts_comp[lbl_a] + df_ts_comp[lbl_b]
            df_ts_comp = df_ts_comp.sort_values('Total_Volume', ascending=True)
            
            df_ts_melt = df_ts_comp.melt(id_vars=['Tipo de Solicitud', 'Total_Volume'], value_vars=[lbl_a, lbl_b], var_name='Periodo', value_name='Cantidad')
            df_ts_melt = df_ts_melt[df_ts_melt['Cantidad'] > 0]
            
            fig_comp_ts = px.bar(
                df_ts_melt, 
                x='Cantidad', 
                y='Tipo de Solicitud', 
                color='Periodo', 
                barmode='group', 
                orientation='h', 
                text_auto=',d', 
                color_discrete_map=mapa_color_comp,
                category_orders={'Tipo de Solicitud': df_ts_comp['Tipo de Solicitud'].tolist()}
            )
            fig_comp_ts.update_layout(height=300, margin=dict(l=5, r=5, t=10, b=10), legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(aplicar_touch_safe(fig_comp_ts), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

        with col_cp2:
            st.subheader(f"Comparativo Medio de Recepción ({vs_header})")
            df_mr_a = df_a['Medio de Recepción'].dropna().value_counts().reset_index()
            df_mr_a.columns = ['Medio de Recepción', lbl_a]
            
            df_mr_b = df_b['Medio de Recepción'].dropna().value_counts().reset_index()
            df_mr_b.columns = ['Medio de Recepción', lbl_b]
            
            df_mr_comp = pd.merge(df_mr_a, df_mr_b, on='Medio de Recepción', how='outer').fillna(0)
            df_mr_comp['Total_Volume'] = df_mr_comp[lbl_a] + df_mr_comp[lbl_b]
            df_mr_comp = df_mr_comp.sort_values('Total_Volume', ascending=True)
            
            df_mr_melt = df_mr_comp.melt(id_vars=['Medio de Recepción', 'Total_Volume'], value_vars=[lbl_a, lbl_b], var_name='Periodo', value_name='Cantidad')
            df_mr_melt = df_mr_melt[df_mr_melt['Cantidad'] > 0]
            
            fig_comp_mr = px.bar(
                df_mr_melt, 
                x='Cantidad', 
                y='Medio de Recepción', 
                color='Periodo', 
                barmode='group', 
                orientation='h', 
                text_auto=',d', 
                color_discrete_map=mapa_color_comp,
                category_orders={'Medio de Recepción': df_mr_comp['Medio de Recepción'].tolist()}
            )
            fig_comp_mr.update_layout(height=300, margin=dict(l=5, r=5, t=10, b=10), legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(aplicar_touch_safe(fig_comp_mr), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

        st.markdown("---")

        # COMPARATIVO POR RASES
        st.subheader(f"Comparativo por RASES ({vs_header})")
        df_r_a = df_a['RASES'].dropna().value_counts().reset_index()
        df_r_a.columns = ['RASES', 'Cantidad']
        df_r_a['Periodo'] = lbl_a

        df_r_b = df_b['RASES'].dropna().value_counts().reset_index()
        df_r_b.columns = ['RASES', 'Cantidad']
        df_r_b['Periodo'] = lbl_b

        df_comp_rases = pd.concat([df_r_a, df_r_b])
        df_comp_rases = df_comp_rases[(df_comp_rases['Cantidad'] > 0) & (df_comp_rases['RASES'].astype(str).str.strip() != '')].copy()
        df_comp_rases['RASES_fmt'] = df_comp_rases['RASES'].apply(acortar_texto_abreviado)

        fig_comp_rases = px.bar(
            df_comp_rases, x='RASES_fmt', y='Cantidad', color='Periodo', barmode='group',
            text_auto=',d', color_discrete_map=mapa_color_comp
        )
        fig_comp_rases.update_layout(xaxis_title="", yaxis_title="", height=320, margin=dict(l=5, r=5, t=10, b=10), legend=dict(orientation="h", y=1.1, x=0.3))
        st.plotly_chart(aplicar_touch_safe(fig_comp_rases), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

        # COMPARATIVO PQR2S POR UPRES
        st.subheader(f"Comparativo PQR2S por UPRES ({vs_header})")
        df_u_comp_a = df_a['UNIDAD DE ASIGNACIÓN'].dropna().value_counts().reset_index()
        df_u_comp_a.columns = ['UNIDAD DE ASIGNACIÓN', 'Cantidad']
        df_u_comp_a['Periodo'] = lbl_a

        df_u_comp_b = df_b['UNIDAD DE ASIGNACIÓN'].dropna().value_counts().reset_index()
        df_u_comp_b.columns = ['UNIDAD DE ASIGNACIÓN', 'Cantidad']
        df_u_comp_b['Periodo'] = lbl_b

        df_comp_upres_simple = pd.concat([df_u_comp_a, df_u_comp_b])
        df_comp_upres_simple = df_comp_upres_simple[(df_comp_upres_simple['Cantidad'] > 0) & (df_comp_upres_simple['UNIDAD DE ASIGNACIÓN'].astype(str).str.strip() != '')].copy()
        df_comp_upres_simple['UPRES_fmt'] = df_comp_upres_simple['UNIDAD DE ASIGNACIÓN'].apply(acortar_texto_abreviado)

        fig_comp_upres_simple = px.bar(
            df_comp_upres_simple, x='UPRES_fmt', y='Cantidad', color='Periodo', barmode='group',
            text_auto=',d', color_discrete_map=mapa_color_comp
        )
        fig_comp_upres_simple.update_layout(xaxis_title="", yaxis_title="", height=350, margin=dict(l=5, r=5, t=10, b=10), legend=dict(orientation="h", y=1.1, x=0.3))
        st.plotly_chart(aplicar_touch_safe(fig_comp_upres_simple), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

        # COMPARATIVOS DISTRIBUCIÓN POR UPRES TOP 5
        st.markdown("---")
        generar_grafico_upres_comparativo_top5(
            df_a, df_b, 
            'ESPECIALIDAD_CATEGORIA', 
            f"Comparativo Distribución por UPRES - Categoría Salud (Top 5) ({vs_header})",
            lbl_a=lbl_a,
            lbl_b=lbl_b
        )
        generar_grafico_upres_comparativo_top5(
            df_a, df_b, 
            col_mot_esp, 
            f"Comparativo Distribución por UPRES - Motivo Específico (Top 5) ({vs_header})",
            lbl_a=lbl_a,
            lbl_b=lbl_b
        )

# -----------------------------------------------------------------------------
# 4. AUTENTICACIÓN Y CARGA PRINCIPAL
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
    try:
        DB_USER = st.secrets["postgres"]["user"]
        DB_PASS = st.secrets["postgres"]["password"]
        DB_HOST = st.secrets["postgres"]["host"]
        DB_PORT = st.secrets["postgres"]["port"]
        DB_NAME = st.secrets["postgres"]["dbname"]
    except Exception:
        DB_USER = os.getenv("DB_USER")
        DB_PASS = os.getenv("DB_PASS")
        DB_HOST = os.getenv("DB_HOST")
        DB_PORT = os.getenv("DB_PORT", "6543")
        DB_NAME = os.getenv("DB_NAME", "postgres")

    if not DB_USER or not DB_PASS or not DB_HOST:
        st.error("❌ Faltan las credenciales de conexión en la configuración del servidor.")
        st.stop()

    pass_encoded = urllib.parse.quote_plus(DB_PASS)
    engine = create_engine(f"postgresql://{DB_USER}:{pass_encoded}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

    @st.cache_data(ttl=43200, show_spinner="Cargando datos optimizados...")
    def cargar_datos_consolidados():
        query = '''
            SELECT 
                "Consecutivo Ticket",
                "Ticket",
                "fecha_dt",
                "RASES",
                "UNIDAD DE ASIGNACIÓN",
                "ESPECIALIDAD_CATEGORIA",
                "MOTIVO ESPECÍFICO",
                "MOTIVO GENERAL",
                "Tipo de Solicitud",
                "Medio de Recepción"
            FROM "V_SIPQR2S_CONSOLIDADO";
        '''
        df = pd.read_sql(query, con=engine)
        
        df['fecha_dt'] = pd.to_datetime(df['fecha_dt'])
        df['fecha_corta'] = df['fecha_dt'].dt.strftime('%Y-%m-%d')
        
        cols_cat = [
            'RASES', 
            'UNIDAD DE ASIGNACIÓN', 
            'ESPECIALIDAD_CATEGORIA', 
            'MOTIVO ESPECÍFICO', 
            'MOTIVO GENERAL', 
            'Tipo de Solicitud', 
            'Medio de Recepción'
        ]
        for col in cols_cat:
            if col in df.columns:
                df[col] = df[col].astype('category')
                
        return df

    try:
        df_raw = cargar_datos_consolidados()
    except Exception as e:
        st.error(f"Error conectando a la base de datos: {e}")
        st.stop()

    # Gestión de Filtros en Sidebar
    prefs = cargar_preferencias()

    def restablecer_filtros_callback():
        st.session_state["sel_rases"] = []
        st.session_state["sel_unidades"] = []
        st.session_state["sel_cat"] = []
        st.session_state["sel_motivos"] = []
        st.session_state["sel_tipos"] = []
        st.session_state["sel_medios"] = []
        guardar_preferencias({})

    if "sel_rases" not in st.session_state:
        st.session_state["sel_rases"] = prefs.get("sel_rases", [])
    if "sel_unidades" not in st.session_state:
        st.session_state["sel_unidades"] = prefs.get("sel_unidades", [])
    if "sel_cat" not in st.session_state:
        st.session_state["sel_cat"] = prefs.get("sel_cat", [])
    if "sel_motivos" not in st.session_state:
        st.session_state["sel_motivos"] = prefs.get("sel_motivos", [])
    if "sel_tipos" not in st.session_state:
        st.session_state["sel_tipos"] = prefs.get("sel_tipos", [])
    if "sel_medios" not in st.session_state:
        st.session_state["sel_medios"] = prefs.get("sel_medios", [])

    st.sidebar.write(f"👤 **{name}**")
    authenticator.logout('Cerrar Sesión', 'sidebar')
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filtros Globales de Control")

    lista_rases = sorted([x for x in df_raw['RASES'].dropna().unique() if str(x).strip() != ''])
    sel_rases = st.sidebar.multiselect("RASES", options=lista_rases, key="sel_rases")

    lista_unidades = sorted([x for x in df_raw['UNIDAD DE ASIGNACIÓN'].dropna().unique() if str(x).strip() != ''])
    sel_unidades = st.sidebar.multiselect("UPRES", options=lista_unidades, key="sel_unidades")

    cat_ordenadas = df_raw['ESPECIALIDAD_CATEGORIA'].dropna().value_counts().index.tolist()
    cat_ordenadas = [c for c in cat_ordenadas if str(c).strip() != '']
    sel_cat = st.sidebar.multiselect("Categoría Salud", options=cat_ordenadas, placeholder="Seleccione categoría...", key="sel_cat")

    col_mot_esp = 'MOTIVO ESPECÍFICO' if 'MOTIVO ESPECÍFICO' in df_raw.columns else 'MOTIVO GENERAL'
    motivos_ordenados = df_raw[col_mot_esp].dropna().value_counts().index.tolist()
    motivos_ordenados = [m for m in motivos_ordenados if str(m).strip() != '']
    sel_motivos = st.sidebar.multiselect("Motivo Específico", options=motivos_ordenados, placeholder="Seleccione motivo...", key="sel_motivos")

    lista_tipos = sorted([x for x in df_raw['Tipo de Solicitud'].dropna().unique() if str(x).strip() != ''])
    sel_tipos = st.sidebar.multiselect("Tipo de Solicitud", options=lista_tipos, key="sel_tipos")

    lista_medios = sorted([x for x in df_raw['Medio de Recepción'].dropna().unique() if str(x).strip() != ''])
    sel_medios = st.sidebar.multiselect("Medio de Recepción", options=lista_medios, key="sel_medios")

    st.sidebar.markdown("---")
    col_btn1, col_btn2 = st.sidebar.columns(2)

    with col_btn1:
        if st.button("💾 Guardar", use_container_width=True, help="Guarda la configuración actual de filtros"):
            data_to_save = {
                "sel_rases": st.session_state.get("sel_rases", []),
                "sel_unidades": st.session_state.get("sel_unidades", []),
                "sel_cat": st.session_state.get("sel_cat", []),
                "sel_motivos": st.session_state.get("sel_motivos", []),
                "sel_tipos": st.session_state.get("sel_tipos", []),
                "sel_medios": st.session_state.get("sel_medios", [])
            }
            if guardar_preferencias(data_to_save):
                st.sidebar.success("¡Filtros guardados!")
            else:
                st.sidebar.error("Error al guardar.")

    with col_btn2:
        st.button(
            "🔄 Restablecer", 
            use_container_width=True, 
            help="Limpia todos los filtros",
            on_click=restablecer_filtros_callback
        )

    df_base_global = df_raw.copy()
    if sel_rases:
        df_base_global = df_base_global[df_base_global['RASES'].isin(sel_rases)]
    if sel_unidades:
        df_base_global = df_base_global[df_base_global['UNIDAD DE ASIGNACIÓN'].isin(sel_unidades)]
    if sel_cat:
        df_base_global = df_base_global[df_base_global['ESPECIALIDAD_CATEGORIA'].isin(sel_cat)]
    if sel_motivos:
        df_base_global = df_base_global[df_base_global[col_mot_esp].isin(sel_motivos)]
    if sel_tipos:
        df_base_global = df_base_global[df_base_global['Tipo de Solicitud'].isin(sel_tipos)]
    if sel_medios:
        df_base_global = df_base_global[df_base_global['Medio de Recepción'].isin(sel_medios)]

    # Renderizado Principal
    st.title("🛡️ SIPQR2S Sanidad")
    
    tab_ind, tab_comp = st.tabs(["📊 Análisis Individual", "🔄 Comparativo"])

    with tab_ind:
        render_tab_individual(df_base_global, col_mot_esp)

    with tab_comp:
        render_tab_comparativo(df_base_global, col_mot_esp)