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
    
    # Seleccionar las 10 UPRES principales por cantidad
    top_10_upres = df_base['UNIDAD DE ASIGNACIÓN'].value_counts().head(10).index
    df_g2 = df_base[df_base['UNIDAD DE ASIGNACIÓN'].isin(top_10_upres)].copy()

    # Cálculo del Top 5 local para cada UPRES
    conteo_local = df_g2.groupby(['UNIDAD DE ASIGNACIÓN', col_target], observed=True).size().reset_index(name='Cant_Local')
    conteo_local['Rank_Local'] = conteo_local.groupby('UNIDAD DE ASIGNACIÓN')['Cant_Local'].rank(method='first', ascending=False)
    top_5_locales = conteo_local[conteo_local['Rank_Local'] <= 5].copy()
    top_5_locales['Es_Top5_Local'] = True

    df_g2 = pd.merge(df_g2, top_5_locales[['UNIDAD DE ASIGNACIÓN', col_target, 'Es_Top5_Local']], on=['UNIDAD DE ASIGNACIÓN', col_target], how='left')
    df_g2['Grupo_Consolidado'] = df_g2.apply(lambda r: str(r[col_target]) if r['Es_Top5_Local'] == True else "OTROS", axis=1)

    df_stack = df_g2.groupby(['UNIDAD DE ASIGNACIÓN', 'Grupo_Consolidado'], observed=True).size().reset_index(name='Cantidad')
    df_stack['UPRES_fmt'] = df_stack['UNIDAD DE ASIGNACIÓN'].apply(acortar_texto_abreviado)
    df_stack['Grupo_fmt'] = df_stack['Grupo_Consolidado'].apply(lambda x: "OTROS" if x == "OTROS" else acortar_texto_abreviado(x))
    df_totales = df_stack.groupby('UPRES_fmt', observed=True)['Cantidad'].sum().reset_index(name='Total')

    # Orden exacto de izquierda a derecha: OTROS en la punta final, seguido de Top 5 a Top 1 en la base
    categorias_unicas = (
        df_stack[df_stack['Grupo_fmt'] != "OTROS"]
        .groupby('Grupo_fmt', observed=True)['Cantidad']
        .sum()
        .sort_values(ascending=True) # Ascendente para que Plotly coloque en la base el mayor (Top 1)
        .index.tolist()
    )
    orden_apilado = ["OTROS"] + categorias_unicas

    paleta_contraste = [
        '#1b4332', '#2d6a4f', '#40916c', '#1d3557', 
        '#2b2d42', '#d4a373', '#52b788', '#003049'
    ]
    
    color_map = {'OTROS': '#a5d6a7'}
    for idx, cat in enumerate(categorias_unicas):
        color_map[cat] = paleta_contraste[idx % len(paleta_contraste)]

    fig_stack = px.bar(
        df_stack, 
        y='UPRES_fmt', 
        x='Cantidad', 
        color='Grupo_fmt', 
        orientation='h', 
        category_orders={'Grupo_fmt': orden_apilado},
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
        yaxis=dict(autorange="reversed"), 
        xaxis_title="", 
        yaxis_title="", 
        height=480, 
        margin=dict(l=5, r=40, t=10, b=10), 
        legend=dict(orientation="h", y=-0.25, x=0, title=None, font=dict(size=10))
    )
    st.plotly_chart(aplicar_touch_safe(fig_stack), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

def generar_grafico_top10_cat_apilado_upres(df_base, titulo_grafico):
    st.subheader(titulo_grafico)
    
    # Top 10 Categorías de Salud por volumen general
    top_10_cats = df_base['ESPECIALIDAD_CATEGORIA'].value_counts().head(10).index
    df_sub = df_base[df_base['ESPECIALIDAD_CATEGORIA'].isin(top_10_cats)].copy()

    # Agrupar por Categoría Salud y apilar por UPRES
    df_stack = df_sub.groupby(['ESPECIALIDAD_CATEGORIA', 'UNIDAD DE ASIGNACIÓN'], observed=True).size().reset_index(name='Cantidad')
    df_stack = df_stack[df_stack['Cantidad'] > 0]
    
    df_stack['Cat_fmt'] = df_stack['ESPECIALIDAD_CATEGORIA'].apply(acortar_texto_abreviado)
    df_stack['UPRES_fmt'] = df_stack['UNIDAD DE ASIGNACIÓN'].apply(acortar_texto_abreviado)

    # Ordenar las categorías de mayor a menor total
    orden_cats = (
        df_stack.groupby('Cat_fmt', observed=True)['Cantidad']
        .sum()
        .sort_values(ascending=False)
        .index.tolist()
    )

    df_totales = df_stack.groupby('Cat_fmt', observed=True)['Cantidad'].sum().reset_index(name='Total')

    fig_cat_stack = px.bar(
        df_stack,
        y='Cat_fmt',
        x='Cantidad',
        color='UPRES_fmt',
        orientation='h',
        category_orders={'Cat_fmt': orden_cats},
        color_discrete_sequence=px.colors.qualitative.Prism
    )

    fig_cat_stack.add_trace(go.Scatter(
        y=df_totales['Cat_fmt'],
        x=df_totales['Total'],
        mode='text',
        text=df_totales['Total'].apply(lambda v: f" <b>{v:,}</b>"),
        textposition='middle right',
        showlegend=False,
        hoverinfo='skip'
    ))

    fig_cat_stack.update_layout(
        barmode='stack',
        yaxis=dict(autorange="reversed"),
        xaxis_title="",
        yaxis_title="",
        height=500,
        margin=dict(l=5, r=40, t=10, b=10),
        legend=dict(orientation="h", y=-0.25, x=0, title=None, font=dict(size=9))
    )
    st.plotly_chart(aplicar_touch_safe(fig_cat_stack), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

# -----------------------------------------------------------------------------
# 3. MÓDULOS DE RENDERIZADO
# -----------------------------------------------------------------------------
def render_tab_individual(df_base_global, col_mot_esp, df_filtrado_fecha):
    st.caption("Consola Ejecutiva de Atención al Usuario - Periodo Único")

    df_base = df_filtrado_fecha.copy()

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
    k1.metric("Total SIPQR2S", f"{len(df_base):,}")
    k1_cat = df_base['ESPECIALIDAD_CATEGORIA'].value_counts()
    cat_top_name = k1_cat.index[0] if not k1_cat.empty else "N/A"
    k2.metric("Categoría con más SIPQR2S", acortar_texto_abreviado(cat_top_name), delta=f"{k1_cat.iloc[0] if not k1_cat.empty else 0:,} tickets", delta_color="off")

    k3, k4, k5 = st.columns(3)
    k3.metric("UPRES con más SIPQR2S", acortar_texto_abreviado(top_upres_nom), delta=f"{top_upres_val:,} tickets", delta_color="off")
    k4.metric("RASES con más SIPQR2S", acortar_texto_abreviado(top_rases_nom), delta=f"{top_rases_val:,} tickets", delta_color="off")
    k5.metric("Día con más SIPQR2S", f"{top_dia_nom}", delta=f"{top_dia_val:,} tickets", delta_color="off")

    st.markdown("---")

    st.subheader("MAPA: Distribución Geográfica SIPQR2S por UPRES")
    df_geo = df_base.groupby('UNIDAD DE ASIGNACIÓN', observed=True).size().reset_index(name='Cantidad')
    
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

    # -----------------------------------------------------------------------------
    # 1. GRÁFICO DE COMPORTAMIENTO DIARIO (INHABILITADO)
    # -----------------------------------------------------------------------------
    # st.subheader("Comportamiento Diario de SIPQR2S")
    # df_dia = df_base.groupby(['fecha_dt', 'fecha_corta'], observed=True).size().reset_index(name='Cantidad').sort_values('fecha_dt')
    # if not df_dia.empty:
    #     fig_dia = go.Figure()
    #     fig_dia.add_trace(go.Scatter(
    #         x=df_dia['fecha_corta'],
    #         y=df_dia['Cantidad'],
    #         mode='lines+markers',
    #         name='Tickets Diarios',
    #         line=dict(color=COLOR_PERIODO_A, width=1, dash='dot'),
    #         marker=dict(size=5, color='#1b5e20')
    #     ))
    #     if len(df_dia) > 1:
    #         x_vals = np.arange(len(df_dia))
    #         y_vals = df_dia['Cantidad'].values
    #         m, b = np.polyfit(x_vals, y_vals, 1)
    #         trend_line = m * x_vals + b
    #         fig_dia.add_trace(go.Scatter(
    #             x=df_dia['fecha_corta'],
    #             y=trend_line,
    #             mode='lines',
    #             name='Tendencia Periodo',
    #             line=dict(color=COLOR_PERIODO_B, width=3.5)
    #         ))
    #     fig_dia.update_layout(
    #         xaxis_title="", yaxis_title="", height=300,
    #         margin=dict(l=5, r=5, t=10, b=10),
    #         legend=dict(orientation="h", y=1.1, x=0.8)
    #     )
    #     st.plotly_chart(aplicar_touch_safe(fig_dia), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

    st.subheader("SIPQR2S por RASES")
    df_g1 = df_base['RASES'].value_counts().reset_index()
    df_g1.columns = ['RASES', 'Cantidad']
    df_g1['RASES_fmt'] = df_g1['RASES'].apply(acortar_texto_abreviado)
    fig1 = px.bar(df_g1, x='RASES_fmt', y='Cantidad', text_auto=True, color_discrete_sequence=[COLOR_PERIODO_A])
    fig1.update_layout(xaxis_title="", yaxis_title="", height=300, margin=dict(l=5, r=5, t=10, b=10))
    st.plotly_chart(aplicar_touch_safe(fig1), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

    # NUEVO GRÁFICO: Top 10 Categorías de Salud apiladas por UPRES en Individual
    generar_grafico_top10_cat_apilado_upres(df_base, "Top 10 Categoría Salud apilada por UPRES")

    generar_grafico_upres_apilado(df_base, 'ESPECIALIDAD_CATEGORIA', "Distribución por UPRES - Categoría Salud (Top 5)")
    generar_grafico_upres_apilado(df_base, col_mot_esp, "Distribución por UPRES - Motivo Específico (Top 5)")

    st.markdown("---")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.subheader("Porcentaje (%) por Tipo de Solicitud")
        df_pie_sol = df_base['Tipo de Solicitud'].value_counts().reset_index()
        df_pie_sol.columns = ['Tipo', 'Cantidad']
        fig_pie1 = px.pie(df_pie_sol, values='Cantidad', names='Tipo', hole=0.4, color_discrete_sequence=px.colors.sequential.Greens_r)
        fig_pie1.update_layout(height=300, margin=dict(l=5, r=5, t=10, b=10), legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(aplicar_touch_safe(fig_pie1), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

    with col_t2:
        st.subheader("Porcentaje (%) por Medio de Recepción")
        df_pie_med = df_base['Medio de Recepción'].value_counts().reset_index()
        df_pie_med.columns = ['Medio', 'Cantidad']
        fig_pie2 = px.pie(df_pie_med, values='Cantidad', names='Medio', hole=0.4, color_discrete_sequence=px.colors.sequential.YlGn_r)
        fig_pie2.update_layout(height=300, margin=dict(l=5, r=5, t=10, b=10), legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(aplicar_touch_safe(fig_pie2), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)


def render_tab_comparativo(df_base_global, col_mot_esp):
    st.caption("Comparación Analítica Cruzada entre dos Ventanas de Tiempo")

    min_hist = df_base_global['fecha_dt'].min().date() if not df_base_global.empty else None
    max_hist = df_base_global['fecha_dt'].max().date() if not df_base_global.empty else None

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.markdown("### Periodo A (Base)")
        rango_a = st.date_input("Seleccione Rango A", value=(min_hist, min_hist + pd.Timedelta(days=30)) if min_hist else [], min_value=min_hist, max_value=max_hist, key="rango_a")
    with col_p2:
        st.markdown("### Periodo B (Comparado)")
        rango_b = st.date_input("Seleccione Rango B", value=(max_hist - pd.Timedelta(days=30), max_hist) if max_hist else [], min_value=min_hist, max_value=max_hist, key="rango_b")

    if len(rango_a) == 2 and len(rango_b) == 2:
        df_a = df_base_global[(df_base_global['fecha_dt'].dt.date >= rango_a[0]) & (df_base_global['fecha_dt'].dt.date <= rango_a[1])].copy()
        df_b = df_base_global[(df_base_global['fecha_dt'].dt.date >= rango_b[0]) & (df_base_global['fecha_dt'].dt.date <= rango_b[1])].copy()

        tot_a, tot_b = len(df_a), len(df_b)
        diff_abs = tot_b - tot_a
        diff_pct = ((diff_abs / tot_a) * 100) if tot_a > 0 else 0.0

        st.markdown("---")
        st.subheader("Indicadores Comparativos Generales")
        kc1, kc2, kc3 = st.columns(3)
        kc1.metric("Total Periodo A", f"{tot_a:,}")
        kc2.metric("Total Periodo B", f"{tot_b:,}")
        
        kc3.metric(
            "Variación Periodo B vs A",
            f"{diff_abs:+,}",
            delta=f"{diff_abs:+,} tickets ({diff_pct:+.1f}%)",
            delta_color="inverse"
        )

        st.markdown("---")

        mapa_color_comp = {'Periodo A': COLOR_PERIODO_A, 'Periodo B': COLOR_PERIODO_B}

        st.subheader("Comparativo por RASES")
        df_r_a = df_a['RASES'].value_counts().reset_index()
        df_r_a.columns = ['RASES', 'Cantidad']
        df_r_a['Periodo'] = 'Periodo A'

        df_r_b = df_b['RASES'].value_counts().reset_index()
        df_r_b.columns = ['RASES', 'Cantidad']
        df_r_b['Periodo'] = 'Periodo B'

        df_comp_rases = pd.concat([df_r_a, df_r_b])
        df_comp_rases['RASES_fmt'] = df_comp_rases['RASES'].apply(acortar_texto_abreviado)

        fig_comp_rases = px.bar(
            df_comp_rases, x='RASES_fmt', y='Cantidad', color='Periodo', barmode='group',
            text_auto=True, color_discrete_map=mapa_color_comp
        )
        fig_comp_rases.update_layout(xaxis_title="", yaxis_title="", height=320, margin=dict(l=5, r=5, t=10, b=10), legend=dict(orientation="h", y=1.1, x=0.3))
        st.plotly_chart(aplicar_touch_safe(fig_comp_rases), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

        st.subheader("Comparativo Top 10 UPRES")
        top_upres_comp = pd.concat([df_a, df_b])['UNIDAD DE ASIGNACIÓN'].value_counts().head(10).index
        df_u_a = df_a[df_a['UNIDAD DE ASIGNACIÓN'].isin(top_upres_comp)].groupby('UNIDAD DE ASIGNACIÓN', observed=True).size().reset_index(name='Cantidad')
        df_u_a['Periodo'] = 'Periodo A'

        df_u_b = df_b[df_b['UNIDAD DE ASIGNACIÓN'].isin(top_upres_comp)].groupby('UNIDAD DE ASIGNACIÓN', observed=True).size().reset_index(name='Cantidad')
        df_u_b['Periodo'] = 'Periodo B'

        df_comp_upres = pd.concat([df_u_a, df_u_b])
        df_comp_upres['UPRES_fmt'] = df_comp_upres['UNIDAD DE ASIGNACIÓN'].apply(acortar_texto_abreviado)

        fig_comp_upres = px.bar(
            df_comp_upres, y='UPRES_fmt', x='Cantidad', color='Periodo', barmode='group', orientation='h',
            text_auto=True, color_discrete_map=mapa_color_comp,
            category_orders={'UPRES_fmt': [acortar_texto_abreviado(u) for u in top_upres_comp]}
        )
        fig_comp_upres.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="", yaxis_title="", height=420, margin=dict(l=5, r=5, t=10, b=10), legend=dict(orientation="h", y=-0.15, x=0.3))
        st.plotly_chart(aplicar_touch_safe(fig_comp_upres), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

        # NUEVO GRÁFICO: Top 10 Categorías de Salud apiladas por UPRES en Comparativo
        generar_grafico_top10_cat_apilado_upres(pd.concat([df_a, df_b]), "Top 10 Categoría Salud apilada por UPRES (Muestra Consolidada)")

        st.subheader("Comparativo por Categoría Salud")
        top_cat_comp = pd.concat([df_a, df_b])['ESPECIALIDAD_CATEGORIA'].value_counts().head(10).index
        df_c_a = df_a[df_a['ESPECIALIDAD_CATEGORIA'].isin(top_cat_comp)].groupby('ESPECIALIDAD_CATEGORIA', observed=True).size().reset_index(name='Cantidad')
        df_c_a['Periodo'] = 'Periodo A'

        df_c_b = df_b[df_b['ESPECIALIDAD_CATEGORIA'].isin(top_cat_comp)].groupby('ESPECIALIDAD_CATEGORIA', observed=True).size().reset_index(name='Cantidad')
        df_c_b['Periodo'] = 'Periodo B'

        df_comp_cat = pd.concat([df_c_a, df_c_b])
        df_comp_cat['Cat_fmt'] = df_comp_cat['ESPECIALIDAD_CATEGORIA'].apply(acortar_texto_abreviado)

        fig_comp_cat = px.bar(
            df_comp_cat, y='Cat_fmt', x='Cantidad', color='Periodo', barmode='group', orientation='h',
            text_auto=True, color_discrete_map=mapa_color_comp,
            category_orders={'Cat_fmt': [acortar_texto_abreviado(c) for c in top_cat_comp]}
        )
        fig_comp_cat.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="", yaxis_title="", height=420, margin=dict(l=5, r=5, t=10, b=10), legend=dict(orientation="h", y=-0.15, x=0.3))
        st.plotly_chart(aplicar_touch_safe(fig_comp_cat), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

        st.subheader("Comparativo por Motivo Específico")
        top_mot_comp = pd.concat([df_a, df_b])[col_mot_esp].value_counts().head(10).index
        df_m_a = df_a[df_a[col_mot_esp].isin(top_mot_comp)].groupby(col_mot_esp, observed=True).size().reset_index(name='Cantidad')
        df_m_a['Periodo'] = 'Periodo A'

        df_m_b = df_b[df_b[col_mot_esp].isin(top_mot_comp)].groupby(col_mot_esp, observed=True).size().reset_index(name='Cantidad')
        df_m_b['Periodo'] = 'Periodo B'

        df_comp_mot = pd.concat([df_m_a, df_m_b])
        df_comp_mot['Mot_fmt'] = df_comp_mot[col_mot_esp].apply(acortar_texto_abreviado)

        fig_comp_mot = px.bar(
            df_comp_mot, y='Mot_fmt', x='Cantidad', color='Periodo', barmode='group', orientation='h',
            text_auto=True, color_discrete_map=mapa_color_comp,
            category_orders={'Mot_fmt': [acortar_texto_abreviado(m) for m in top_mot_comp]}
        )
        fig_comp_mot.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="", yaxis_title="", height=420, margin=dict(l=5, r=5, t=10, b=10), legend=dict(orientation="h", y=-0.15, x=0.3))
        st.plotly_chart(aplicar_touch_safe(fig_comp_mot), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

        st.subheader("Comparativo por Tipo de Solicitud")
        df_ts_a = df_a['Tipo de Solicitud'].value_counts().reset_index()
        df_ts_a.columns = ['Tipo', 'Periodo A']
        
        df_ts_b = df_b['Tipo de Solicitud'].value_counts().reset_index()
        df_ts_b.columns = ['Tipo', 'Periodo B']
        
        df_ts_comp = pd.merge(df_ts_a, df_ts_b, on='Tipo', how='outer').fillna(0)
        df_ts_melt = df_ts_comp.melt(id_vars=['Tipo'], value_vars=['Periodo A', 'Periodo B'], var_name='Periodo', value_name='Cantidad')
        
        fig_comp_ts = px.bar(df_ts_melt, x='Cantidad', y='Tipo', color='Periodo', barmode='group', orientation='h', text_auto=True, color_discrete_map=mapa_color_comp)
        fig_comp_ts.update_layout(yaxis=dict(autorange="reversed"), height=300, margin=dict(l=5, r=5, t=10, b=10), legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(aplicar_touch_safe(fig_comp_ts), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

        st.subheader("Comparativo por Medio de Recepción")
        df_mr_a = df_a['Medio de Recepción'].value_counts().reset_index()
        df_mr_a.columns = ['Medio', 'Periodo A']
        
        df_mr_b = df_b['Medio de Recepción'].value_counts().reset_index()
        df_mr_b.columns = ['Medio', 'Periodo B']
        
        df_mr_comp = pd.merge(df_mr_a, df_mr_b, on='Medio', how='outer').fillna(0)
        df_mr_melt = df_mr_comp.melt(id_vars=['Medio'], value_vars=['Periodo A', 'Periodo B'], var_name='Periodo', value_name='Cantidad')
        
        fig_comp_mr = px.bar(df_mr_melt, x='Cantidad', y='Medio', color='Periodo', barmode='group', orientation='h', text_auto=True, color_discrete_map=mapa_color_comp)
        fig_comp_mr.update_layout(yaxis=dict(autorange="reversed"), height=300, margin=dict(l=5, r=5, t=10, b=10), legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(aplicar_touch_safe(fig_comp_mr), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)
    else:
        st.warning("Seleccione dos fechas válidas para el Periodo A y el Periodo B.")

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

    @st.cache_data(ttl=3600, show_spinner="Cargando datos optimizados...")
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

    # -----------------------------------------------------------------------------
    # GESTIÓN DE ESTADO Y PREFERENCIAS
    # -----------------------------------------------------------------------------
    prefs = cargar_preferencias()

    def restablecer_filtros_callback():
        st.session_state["sel_unidades"] = []
        st.session_state["sel_rases"] = []
        st.session_state["sel_cat"] = []
        st.session_state["sel_motivos"] = []
        st.session_state["sel_tipos"] = []
        st.session_state["sel_medios"] = []
        guardar_preferencias({})

    if "sel_unidades" not in st.session_state:
        st.session_state["sel_unidades"] = prefs.get("sel_unidades", [])
    if "sel_rases" not in st.session_state:
        st.session_state["sel_rases"] = prefs.get("sel_rases", [])
    if "sel_cat" not in st.session_state:
        st.session_state["sel_cat"] = prefs.get("sel_cat", [])
    if "sel_motivos" not in st.session_state:
        st.session_state["sel_motivos"] = prefs.get("sel_motivos", [])
    if "sel_tipos" not in st.session_state:
        st.session_state["sel_tipos"] = prefs.get("sel_tipos", [])
    if "sel_medios" not in st.session_state:
        st.session_state["sel_medios"] = prefs.get("sel_medios", [])

    # Sidebar Global
    st.sidebar.write(f"👤 **{name}**")
    authenticator.logout('Cerrar Sesión', 'sidebar')
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filtros Globales de Control")

    # 1. Segmentador Rango de Fechas
    min_f = df_raw['fecha_dt'].min().date() if not df_raw.empty else None
    max_f = df_raw['fecha_dt'].max().date() if not df_raw.empty else None
    rango_fechas_ind = st.sidebar.date_input("Rango de Fecha de Creación", value=(min_f, max_f), min_value=min_f, max_value=max_f) if min_f else []

    # Filtrado intermedio base para calcular los segmentadores dependientes del tiempo
    df_filtrado_fecha = df_raw.copy()
    if len(rango_fechas_ind) == 2:
        df_filtrado_fecha = df_filtrado_fecha[(df_filtrado_fecha['fecha_dt'].dt.date >= rango_fechas_ind[0]) & (df_filtrado_fecha['fecha_dt'].dt.date <= rango_fechas_ind[1])]

    # 2. Segmentador UPRES
    lista_unidades = sorted([x for x in df_raw['UNIDAD DE ASIGNACIÓN'].dropna().unique() if str(x).strip() != ''])
    sel_unidades = st.sidebar.multiselect("UPRES", options=lista_unidades, key="sel_unidades")

    # 3. Segmentador RASES
    lista_rases = sorted([x for x in df_raw['RASES'].dropna().unique() if str(x).strip() != ''])
    sel_rases = st.sidebar.multiselect("RASES", options=lista_rases, key="sel_rases")

    # 4. Segmentador Categoría Salud (Ordenado dinámicamente de mayor a menor sin datos adicionales)
    cat_ordenadas = df_filtrado_fecha['ESPECIALIDAD_CATEGORIA'].value_counts().index.tolist()
    cat_ordenadas = [c for c in cat_ordenadas if str(c).strip() != '']
    sel_cat = st.sidebar.multiselect("Categoría Salud", options=cat_ordenadas, placeholder="Seleccione categoría...", key="sel_cat")

    # 5. Segmentador Motivo Específico (Ordenado dinámicamente de mayor a menor sin datos adicionales)
    col_mot_esp = 'MOTIVO ESPECÍFICO' if 'MOTIVO ESPECÍFICO' in df_raw.columns else 'MOTIVO GENERAL'
    motivos_ordenados = df_filtrado_fecha[col_mot_esp].value_counts().index.tolist()
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
                "sel_unidades": st.session_state.get("sel_unidades", []),
                "sel_rases": st.session_state.get("sel_rases", []),
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

    df_base_global = df_filtrado_fecha.copy()
    if sel_unidades:
        df_base_global = df_base_global[df_base_global['UNIDAD DE ASIGNACIÓN'].isin(sel_unidades)]
    if sel_rases:
        df_base_global = df_base_global[df_base_global['RASES'].isin(sel_rases)]
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
    tab_ind, tab_comp, tab_det = st.tabs(["📊 Análisis Individual", "🔄 Comparativo", "📋 Detalle"])

    with tab_ind:
        render_tab_individual(df_raw, col_mot_esp, df_base_global)

    with tab_comp:
        render_tab_comparativo(df_raw, col_mot_esp)

    with tab_det:
        st.subheader("📋 Consolidado de Datos")
        
        col_ticket = 'Ticket' if 'Ticket' in df_base_global.columns else 'Consecutivo Ticket'
        cols_detalle = [
            col_ticket,
            'fecha_corta',
            'RASES', 
            'UNIDAD DE ASIGNACIÓN', 
            'ESPECIALIDAD_CATEGORIA', 
            col_mot_esp,
            'Tipo de Solicitud', 
            'Medio de Recepción'
        ]
        
        cols_validas = [c for c in cols_detalle if c in df_base_global.columns]
        
        st.dataframe(
            df_base_global[cols_validas].head(100), 
            use_container_width=True,
            hide_index=True
        )