import os
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

# Cargar variables de entorno desde el archivo .env local
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

# -----------------------------------------------------------------------------
# 2. FUNCIONES AUXILIARES Y FORMATO
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# 3. MÓDULOS DE RENDERIZADO (VISTAS MODULARES)
# -----------------------------------------------------------------------------
def render_tab_individual(df_base_global, col_mot_esp):
    st.caption("Consola Ejecutiva de Atención al Usuario - Periodo Único")

    min_f = df_base_global['fecha_dt'].min().date() if not df_base_global.empty else None
    max_f = df_base_global['fecha_dt'].max().date() if not df_base_global.empty else None
    rango_fechas_ind = st.date_input("Rango de Fecha de Creación (Análisis Individual)", value=(min_f, max_f), min_value=min_f, max_value=max_f) if min_f else []

    df_base = df_base_global.copy()
    if len(rango_fechas_ind) == 2:
        df_base = df_base[(df_base['fecha_dt'].dt.date >= rango_fechas_ind[0]) & (df_base['fecha_dt'].dt.date <= rango_fechas_ind[1])]

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

    st.subheader("📍 SIPQR2S por RASES")
    df_g1 = df_base['RASES'].value_counts().reset_index()
    df_g1.columns = ['RASES', 'Cantidad']
    df_g1['RASES_fmt'] = df_g1['RASES'].apply(acortar_texto_abreviado)
    fig1 = px.bar(df_g1, x='RASES_fmt', y='Cantidad', text_auto=True, color_discrete_sequence=['#2e7d32'])
    fig1.update_layout(xaxis_title="", yaxis_title="", height=300, margin=dict(l=5, r=5, t=10, b=10))
    st.plotly_chart(aplicar_touch_safe(fig1), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

    st.subheader("🏢 Distribución por UPRES (Top 10)")
    dim_apilamiento = st.radio(
        "Seleccione dimensión de apilamiento:",
        ["Categoría Salud", "Motivo Específico"],
        horizontal=True,
        key="rad_ind"
    )

    top_10_upres = df_base['UNIDAD DE ASIGNACIÓN'].value_counts().head(10).index
    df_g2 = df_base[df_base['UNIDAD DE ASIGNACIÓN'].isin(top_10_upres)].copy()
    col_target = 'ESPECIALIDAD_CATEGORIA' if dim_apilamiento == "Categoría Salud" else col_mot_esp

    conteo_local = df_g2.groupby(['UNIDAD DE ASIGNACIÓN', col_target]).size().reset_index(name='Cant_Local')
    conteo_local['Rank_Local'] = conteo_local.groupby('UNIDAD DE ASIGNACIÓN')['Cant_Local'].rank(method='first', ascending=False)
    top_3_locales = conteo_local[conteo_local['Rank_Local'] <= 3].copy()
    top_3_locales['Es_Top3_Local'] = True

    df_g2 = pd.merge(df_g2, top_3_locales[['UNIDAD DE ASIGNACIÓN', col_target, 'Es_Top3_Local']], on=['UNIDAD DE ASIGNACIÓN', col_target], how='left')
    df_g2['Grupo_Consolidado'] = df_g2.apply(lambda r: r[col_target] if r['Es_Top3_Local'] == True else "OTROS", axis=1)

    df_stack = df_g2.groupby(['UNIDAD DE ASIGNACIÓN', 'Grupo_Consolidado']).size().reset_index(name='Cantidad')
    df_stack['UPRES_fmt'] = df_stack['UNIDAD DE ASIGNACIÓN'].apply(acortar_texto_abreviado)
    df_stack['Grupo_fmt'] = df_stack['Grupo_Consolidado'].apply(lambda x: "OTROS" if x == "OTROS" else acortar_texto_abreviado(x))
    df_totales = df_stack.groupby('UPRES_fmt')['Cantidad'].sum().reset_index(name='Total')

    categorias_unicas = [c for c in df_stack['Grupo_fmt'].unique() if c != "OTROS"]
    orden_apilado = ["OTROS"] + categorias_unicas

    fig_stack = px.bar(df_stack, y='UPRES_fmt', x='Cantidad', color='Grupo_fmt', orientation='h', category_orders={'Grupo_fmt': orden_apilado})
    fig_stack.add_trace(go.Scatter(y=df_totales['UPRES_fmt'], x=df_totales['Total'], mode='text', text=df_totales['Total'].apply(lambda v: f" <b>{v:,}</b>"), textposition='middle right', showlegend=False, hoverinfo='skip'))
    fig_stack.update_layout(barmode='stack', yaxis=dict(autorange="reversed"), xaxis_title="", yaxis_title="", height=460, margin=dict(l=5, r=40, t=10, b=10), legend=dict(orientation="h", y=-0.25, x=0, title=None, font=dict(size=10)))
    st.plotly_chart(aplicar_touch_safe(fig_stack), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

    st.markdown("---")
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


def render_tab_comparativo(df_base_global):
    st.caption("Comparación Analítica Cruzada entre dos Ventanas de Tiempo")

    min_hist = df_base_global['fecha_dt'].min().date() if not df_base_global.empty else None
    max_hist = df_base_global['fecha_dt'].max().date() if not df_base_global.empty else None

    # Controladores de Fecha Independientes (Periodo A vs Periodo B)
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.markdown("### 🅰️ Periodo A (Base)")
        rango_a = st.date_input("Seleccione Rango A", value=(min_hist, min_hist + pd.Timedelta(days=30)) if min_hist else [], min_value=min_hist, max_value=max_hist, key="rango_a")
    with col_p2:
        st.markdown("### 🅱️ Periodo B (Comparado)")
        rango_b = st.date_input("Seleccione Rango B", value=(max_hist - pd.Timedelta(days=30), max_hist) if max_hist else [], min_value=min_hist, max_value=max_hist, key="rango_b")

    if len(rango_a) == 2 and len(rango_b) == 2:
        df_a = df_base_global[(df_base_global['fecha_dt'].dt.date >= rango_a[0]) & (df_base_global['fecha_dt'].dt.date <= rango_a[1])].copy()
        df_b = df_base_global[(df_base_global['fecha_dt'].dt.date >= rango_b[0]) & (df_base_global['fecha_dt'].dt.date <= rango_b[1])].copy()

        tot_a, tot_b = len(df_a), len(df_b)
        diff_abs = tot_b - tot_a
        diff_pct = ((diff_abs / tot_a) * 100) if tot_a > 0 else 0.0

        st.markdown("---")
        st.subheader("📊 Indicadores Comparativos Generales")
        kc1, kc2, kc3 = st.columns(3)
        kc1.metric("Total Periodo A", f"{tot_a:,}")
        kc2.metric("Total Periodo B", f"{tot_b:,}")
        kc3.metric(
            "Variación Periodo B vs A",
            f"{tot_b:,}",
            delta=f"{diff_abs:+,} tickets ({diff_pct:+.1f}%)",
            delta_color="inverse"
        )

        st.markdown("---")

        # 1. Comportamiento Diario Comparado
        st.subheader("📈 Comparativo de Tendencia Diario")
        df_dia_a = df_a.groupby('fecha_corta').size().reset_index(name='Periodo A')
        df_dia_b = df_b.groupby('fecha_corta').size().reset_index(name='Periodo B')

        fig_comp_dia = go.Figure()
        fig_comp_dia.add_trace(go.Scatter(x=df_dia_a['fecha_corta'], y=df_dia_a['Periodo A'], mode='lines+markers', name='Periodo A', line=dict(color='#1b5e20', width=2)))
        fig_comp_dia.add_trace(go.Scatter(x=df_dia_b['fecha_corta'], y=df_dia_b['Periodo B'], mode='lines+markers', name='Periodo B', line=dict(color='#d32f2f', width=2)))
        fig_comp_dia.update_layout(xaxis_title="", yaxis_title="Cantidad de Tickets", height=320, margin=dict(l=5, r=5, t=10, b=10), legend=dict(orientation="h", y=1.1, x=0.3))
        st.plotly_chart(aplicar_touch_safe(fig_comp_dia), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

        # 2. Comparativo por RASES
        st.subheader("📍 Comparativo por RASES")
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
            text_auto=True, color_discrete_map={'Periodo A': '#2e7d32', 'Periodo B': '#c62828'}
        )
        fig_comp_rases.update_layout(xaxis_title="", yaxis_title="", height=320, margin=dict(l=5, r=5, t=10, b=10), legend=dict(orientation="h", y=1.1, x=0.3))
        st.plotly_chart(aplicar_touch_safe(fig_comp_rases), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

        # 3. Comparativo por UPRES (Top 10)
        st.subheader("🏢 Comparativo Top 10 UPRES")
        top_upres_comp = pd.concat([df_a, df_b])['UNIDAD DE ASIGNACIÓN'].value_counts().head(10).index
        df_u_a = df_a[df_a['UNIDAD DE ASIGNACIÓN'].isin(top_upres_comp)].groupby('UNIDAD DE ASIGNACIÓN').size().reset_index(name='Cantidad')
        df_u_a['Periodo'] = 'Periodo A'

        df_u_b = df_b[df_b['UNIDAD DE ASIGNACIÓN'].isin(top_upres_comp)].groupby('UNIDAD DE ASIGNACIÓN').size().reset_index(name='Cantidad')
        df_u_b['Periodo'] = 'Periodo B'

        df_comp_upres = pd.concat([df_u_a, df_u_b])
        df_comp_upres['UPRES_fmt'] = df_comp_upres['UNIDAD DE ASIGNACIÓN'].apply(acortar_texto_abreviado)

        fig_comp_upres = px.bar(
            df_comp_upres, y='UPRES_fmt', x='Cantidad', color='Periodo', barmode='group', orientation='h',
            text_auto=True, color_discrete_map={'Periodo A': '#388e3c', 'Periodo B': '#e53935'}
        )
        fig_comp_upres.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="", yaxis_title="", height=420, margin=dict(l=5, r=5, t=10, b=10), legend=dict(orientation="h", y=-0.15, x=0.3))
        st.plotly_chart(aplicar_touch_safe(fig_comp_upres), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

        # 4. Comparativo por Categoría Salud
        st.subheader("🩺 Comparativo por Categoría Salud")
        top_cat_comp = pd.concat([df_a, df_b])['ESPECIALIDAD_CATEGORIA'].value_counts().head(10).index
        df_c_a = df_a[df_a['ESPECIALIDAD_CATEGORIA'].isin(top_cat_comp)].groupby('ESPECIALIDAD_CATEGORIA').size().reset_index(name='Cantidad')
        df_c_a['Periodo'] = 'Periodo A'

        df_c_b = df_b[df_b['ESPECIALIDAD_CATEGORIA'].isin(top_cat_comp)].groupby('ESPECIALIDAD_CATEGORIA').size().reset_index(name='Cantidad')
        df_c_b['Periodo'] = 'Periodo B'

        df_comp_cat = pd.concat([df_c_a, df_c_b])
        df_comp_cat['Cat_fmt'] = df_comp_cat['ESPECIALIDAD_CATEGORIA'].apply(acortar_texto_abreviado)

        fig_comp_cat = px.bar(
            df_comp_cat, y='Cat_fmt', x='Cantidad', color='Periodo', barmode='group', orientation='h',
            text_auto=True, color_discrete_map={'Periodo A': '#43a047', 'Periodo B': '#ef5350'}
        )
        fig_comp_cat.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="", yaxis_title="", height=420, margin=dict(l=5, r=5, t=10, b=10), legend=dict(orientation="h", y=-0.15, x=0.3))
        st.plotly_chart(aplicar_touch_safe(fig_comp_cat), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

        # 5. Comparativo por Tipo de Solicitud y Medio de Recepción
        col_cp1, col_cp2 = st.columns(2)
        with col_cp1:
            st.subheader("🍰 Tipo de Solicitud")
            df_ts_a = df_a['Tipo de Solicitud'].value_counts().reset_index(name='Periodo A').rename(columns={'index': 'Tipo'})
            df_ts_b = df_b['Tipo de Solicitud'].value_counts().reset_index(name='Periodo B').rename(columns={'index': 'Tipo'})
            df_ts_comp = pd.merge(df_ts_a, df_ts_b, on='Tipo', how='outer').fillna(0)
            df_ts_melt = df_ts_comp.melt(id_vars=['Tipo'], value_vars=['Periodo A', 'Periodo B'], var_name='Periodo', value_name='Cantidad')
            fig_comp_ts = px.bar(df_ts_melt, x='Cantidad', y='Tipo', color='Periodo', barmode='group', orientation='h', text_auto=True, color_discrete_map={'Periodo A': '#66bb6a', 'Periodo B': '#ff7043'})
            fig_comp_ts.update_layout(yaxis=dict(autorange="reversed"), height=300, margin=dict(l=5, r=5, t=10, b=10), legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(aplicar_touch_safe(fig_comp_ts), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

        with col_cp2:
            st.subheader("🍩 Medio de Recepción")
            df_mr_a = df_a['Medio de Recepción'].value_counts().reset_index(name='Periodo A').rename(columns={'index': 'Medio'})
            df_mr_b = df_b['Medio de Recepción'].value_counts().reset_index(name='Periodo B').rename(columns={'index': 'Medio'})
            df_mr_comp = pd.merge(df_mr_a, df_mr_b, on='Medio', how='outer').fillna(0)
            df_mr_melt = df_mr_comp.melt(id_vars=['Medio'], value_vars=['Periodo A', 'Periodo B'], var_name='Periodo', value_name='Cantidad')
            fig_comp_mr = px.bar(df_mr_melt, x='Cantidad', y='Medio', color='Periodo', barmode='group', orientation='h', text_auto=True, color_discrete_map={'Periodo A': '#81c784', 'Periodo B': '#ff8a65'})
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

    # Sidebar Global
    st.sidebar.write(f"👤 **{name}**")
    authenticator.logout('Cerrar Sesión', 'sidebar')
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filtros Globales de Control")

    lista_unidades = sorted([x for x in df_raw['UNIDAD DE ASIGNACIÓN'].dropna().unique() if str(x).strip() != ''])
    sel_unidades = st.sidebar.multiselect("UPRES", options=lista_unidades)

    lista_rases = sorted([x for x in df_raw['RASES'].dropna().unique() if str(x).strip() != ''])
    sel_rases = st.sidebar.multiselect("RASES", options=lista_rases)

    cat_ordenadas = df_raw['ESPECIALIDAD_CATEGORIA'].value_counts().index.tolist()
    cat_ordenadas = [c for c in cat_ordenadas if str(c).strip() != '']
    sel_cat = st.sidebar.multiselect("Categoría Salud", options=cat_ordenadas, placeholder="Seleccione categoría...")

    col_mot_esp = 'MOTIVO ESPECÍFICO' if 'MOTIVO ESPECÍFICO' in df_raw.columns else 'MOTIVO GENERAL'
    motivos_ordenados = df_raw[col_mot_esp].value_counts().index.tolist()
    motivos_ordenados = [m for m in motivos_ordenados if str(m).strip() != '']
    sel_motivos = st.sidebar.multiselect("Motivo Específico", options=motivos_ordenados, placeholder="Seleccione motivo...")

    df_base_global = df_raw.copy()
    if sel_unidades:
        df_base_global = df_base_global[df_base_global['UNIDAD DE ASIGNACIÓN'].isin(sel_unidades)]
    if sel_rases:
        df_base_global = df_base_global[df_base_global['RASES'].isin(sel_rases)]
    if sel_cat:
        df_base_global = df_base_global[df_base_global['ESPECIALIDAD_CATEGORIA'].isin(sel_cat)]
    if sel_motivos:
        df_base_global = df_base_global[df_base_global[col_mot_esp].isin(sel_motivos)]

    # Renderizado Principal
    st.title("🛡️ SIPQR2S Sanidad")
    tab_ind, tab_comp, tab_det = st.tabs(["📊 Análisis Individual", "🔄 Comparativo", "📋 Detalle"])

    with tab_ind:
        render_tab_individual(df_base_global, col_mot_esp)

    with tab_comp:
        render_tab_comparativo(df_base_global)

    with tab_det:
        st.subheader("📋 Consolidado de Datos")
        st.dataframe(df_base_global[['RASES', 'UNIDAD DE ASIGNACIÓN', 'ESPECIALIDAD_CATEGORIA', 'Tipo de Solicitud', 'Medio de Recepción']].head(100), use_container_width=True)