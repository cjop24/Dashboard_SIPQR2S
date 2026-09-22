import json
import os
import re
import urllib.parse
import urllib.request
from dotenv import load_dotenv
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit_authenticator as stauth
from sqlalchemy import create_engine
import yaml
from yaml.loader import SafeLoader

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN INICIAL DE STREAMLIT Y ESTILOS
# -----------------------------------------------------------------------------
load_dotenv()

st.set_page_config(
    page_title="Dashboard SIPQR2S",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Inyección CSS: Font Awesome y Google Fonts (Poppins)
st.markdown("""
    <!-- Font Awesome CDN -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');

    html, body, p, h1, h2, h3, h4, h5, h6, label, input, button, select {
        font-family: 'Poppins', sans-serif !important;
    }

    .stApp, .main, div[data-testid="stSidebarContent"] {
        font-family: 'Poppins', sans-serif !important;
    }

    /* Restaurar fuente nativa para iconos de Streamlit */
    [data-testid="stHeader"] *,
    [data-testid="stSidebarCollapseButton"] *,
    [data-testid="stSidebarNav"] *,
    .material-symbols-sharp,
    .material-symbols-outlined,
    .material-icons {
        font-family: 'Material Symbols Rounded', 'Material Symbols Sharp', 'Material Icons' !important;
    }

    .main { padding: 0.5rem; }
    
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 12px 14px;
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

    h1 { font-size: 1.6rem !important; font-weight: 800; color: #0f172a; }
    h3 { font-size: 1.05rem !important; font-weight: 700; color: #1e293b; margin-top: 0.8rem; }

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
    
    div[data-testid="stRadio"] > label {
        display: none;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. CONSTANTES, MAPEOS Y FUNCIONES AUXILIARES
# -----------------------------------------------------------------------------
ARCH_PREFERENCIAS = "preferencias_usuario.json"
COLOR_PERIODO_A = '#2e7d32'  # Verde RASES
COLOR_PERIODO_B = '#c62828'  # Rojo RASES

CONFIG_PLOTLY_TOUCH = {
    'displayModeBar': False,
    'scrollZoom': False,
    'doubleClick': False,
    'showAxisDragHandles': False
}

CONFIG_PLOTLY_MAPA = {
    'displayModeBar': True,
    'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
    'scrollZoom': False,
    'doubleClick': 'reset+pan',
    'showAxisDragHandles': False
}

MAPEO_UPRES_CODIGO_DANE = {
    'BOGOTA': '11', 'BOGOTÁ': '11', 'BOGOTÁ D.C.': '11', 'BOGOTA D.C.': '11', 
    'BOGOTÁ, D.C.': '11', 'BOGOTA, D.C.': '11', 'SANTAFE': '11', 'MEBOG': '11',
    'ANTIOQUIA': '05', 'URABA': '05', 'URABÁ': '05', 'DEAMA': '05', 'DEURA': '05',
    'ATLANTICO': '08', 'ATLÁNTICO': '08', 'DEATA': '08',
    'BOLIVAR': '13', 'BOLÍVAR': '13', 'DEMAM': '13',
    'BOYACA': '15', 'BOYACÁ': '15', 'DEBOY': '15',
    'CALDAS': '17', 'DECAL': '17',
    'CAQUETA': '18', 'CAQUETÁ': '18', 'DECAQ': '18',
    'CAUCA': '19', 'DECAU': '19',
    'CESAR': '20', 'DECES': '20',
    'CORDOBA': '23', 'CÓRDOBA': '23', 'DECOR': '23',
    'CUNDINAMARCA': '25', 'DECUN': '25',
    'CHOCO': '27', 'CHOCÓ': '27',
    'HUILA': '41', 'DEHUI': '41',
    'LA GUAJIRA': '44', 'GUAJIRA': '44', 'DEGUA': '44',
    'MAGDALENA': '47', 'DEMAG': '47',
    'META': '50', 'DEMET': '50',
    'NARIÑO': '52', 'DENAR': '52',
    'NORTE DE SANTANDER': '54', 'DENOR': '54',
    'QUINDIO': '63', 'QUINDÍO': '63', 'DEQUI': '63',
    'RISARALDA': '66', 'DERIS': '66',
    'SANTANDER': '68', 'DESAN': '68',
    'SUCRE': '70', 'DESUC': '70',
    'TOLIMA': '73', 'DETOL': '73',
    'VALLE': '76', 'VALLE DEL CAUCA': '76', 'VALLE CAUCA': '76', 'DEVAL': '76', 
    'ARAUCA': '81', 'DEARA': '81',
    'CASANARE': '85', 'DECAS': '85',
    'PUTUMAYO': '86', 'DEPUT': '86',
    'SAN ANDRES': '88', 'SAN ANDRÉS': '88', 'DESAN_ANDRES': '88',
    'AMAZONAS': '91', 'DEAMA_ZONAS': '91',
    'GUAINIA': '94', 'GUAINÍA': '94',
    'GUAVIARE': '95', 'DEGUAV': '95',
    'VAUPES': '97', 'VAUPÉS': '97',
    'VICHADA': '99', 'DEVIC': '99'
}

NOMBRES_DEPARTAMENTOS_MOSTRAR = {
    '11': 'Bogotá D.C.', '05': 'Antioquia', '08': 'Atlántico', '13': 'Bolívar',
    '15': 'Boyacá', '17': 'Caldas', '18': 'Caquetá', '19': 'Cauca', '20': 'Cesar',
    '23': 'Córdoba', '25': 'Cundinamarca', '27': 'Chocó', '41': 'Huila',
    '44': 'La Guajira', '47': 'Magdalena', '50': 'Meta', '52': 'Nariño',
    '54': 'Norte de Santander', '63': 'Quindío', '66': 'Risaralda', '68': 'Santander',
    '70': 'Sucre', '73': 'Tolima', '76': 'Valle del Cauca', '81': 'Arauca',
    '85': 'Casanare', '86': 'Putumayo', '88': 'San Andrés y Providencia',
    '91': 'Amazonas', '94': 'Guainía', '95': 'Guaviare', '97': 'Vaupés', '99': 'Vichada'
}

@st.cache_data(ttl="24h")
def cargar_geojson_colombia():
    ruta_local = "Colombia.geo_2.json"
    if not os.path.exists(ruta_local):
        ruta_local = "colombia.geo.json"

    if os.path.exists(ruta_local):
        with open(ruta_local, "r", encoding="utf-8") as f:
            geojson = json.load(f)
    else:
        url = "https://gist.githubusercontent.com/john-guerra/43c7656821069d00dcbc/raw/be6a6e239cd5b5b803c6e7c2ec405b793a9064dd/Colombia.geo.json"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            geojson = json.loads(response.read().decode())
    
    for feature in geojson.get('features', []):
        props = feature.get('properties', {})
        code_val = str(props.get('DPTO', props.get('DPTO_CODE', ''))).zfill(2)
        props['DPTO_CODE'] = code_val
        feature['properties'] = props
        
    return geojson

def obtener_codigo_dane(u):
    if pd.isna(u) or not u:
        return None
    u_str = str(u).upper().strip()
    
    if u_str in MAPEO_UPRES_CODIGO_DANE:
        return MAPEO_UPRES_CODIGO_DANE[u_str]
        
    for clave, codigo in MAPEO_UPRES_CODIGO_DANE.items():
        if clave in u_str:
            return codigo
    return None

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
    
    if "BOGOTA" in s or "BOGOTÁ" in s:
        return "BOGOTÁ D.C."

    frases_especificas = {
        'RECONOCIMIENTOS DEL SERVICIO DE POLICÍA': 'FELICITACIÓN',
        'RECONOCIMIENTOS DEL SERVICIO DE POLICIA': 'FELICITACIÓN',
        'SISTEMA SGDEA MINDEFENSA': 'MINDEFENSA',
        'SGDEA MINDEFENSA': 'MINDEFENSA',
        'LÍNEA DIRECTOR GENERAL': 'LÍNEA DIRECTOR',
        'LINEA DIRECTOR GENERAL': 'LÍNEA DIRECTOR',
        'INFORMACIÓN SEGURIDAD CIUDADANA': 'SEG. CIUDADANA',
        'INFORMACION SEGURIDAD CIUDADANA': 'SEG. CIUDADANA'
    }
    if s in frases_especificas:
        return frases_especificas[s]

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

# -----------------------------------------------------------------------------
# CÁLCULO DINÁMICO DE USUARIOS POR PERÍODO / MES
# -----------------------------------------------------------------------------
def obtener_usuarios_dinamicos(df_periodo, df_users_mensual, df_maestro_upres_rases):
    if df_periodo.empty or df_users_mensual.empty:
        return {}, {}

    anios_meses = df_periodo['fecha_dt'].dt.to_period('M').unique()
    
    df_u_filtrado = df_users_mensual[
        df_users_mensual.apply(lambda r: pd.Period(f"{int(r['ANIO'])}-{int(r['MES']):02d}", 'M') in anios_meses, axis=1)
    ]

    if df_u_filtrado.empty:
        return {}, {}

    dict_upres_users = df_u_filtrado.groupby('UNIDAD')['USUARIOS'].sum().to_dict()

    df_u_con_rases = pd.merge(
        df_u_filtrado,
        df_maestro_upres_rases[['UNIDAD', 'RASES']].drop_duplicates(),
        on='UNIDAD',
        how='left'
    )
    dict_rases_users = df_u_con_rases.groupby('RASES')['USUARIOS'].sum().to_dict()

    return dict_rases_users, dict_upres_users

# -----------------------------------------------------------------------------
# 3. GENERACIÓN DE GRÁFICOS COMPLEJOS
# -----------------------------------------------------------------------------
def generar_grafico_mariposa(df_a, df_b, col_target, titulo_grafico, lbl_a="Periodo A", lbl_b="Periodo B"):
    st.markdown(f"### {titulo_grafico}")
    
    df_a_cat = df_a[col_target].dropna().value_counts().reset_index()
    df_a_cat.columns = ['Categoria', 'Cant_A']
    
    df_b_cat = df_b[col_target].dropna().value_counts().reset_index()
    df_b_cat.columns = ['Categoria', 'Cant_B']
    
    df_comp = pd.merge(df_a_cat, df_b_cat, on='Categoria', how='outer').fillna(0)
    if df_comp.empty:
        st.info("No hay datos disponibles para la comparación.")
        return

    df_comp['Cat_fmt'] = df_comp['Categoria'].apply(acortar_texto_abreviado)
    df_comp['Total_Vol'] = df_comp['Cant_A'] + df_comp['Cant_B']
    df_comp = df_comp.sort_values('Total_Vol', ascending=True)

    tot_a = df_comp['Cant_A'].sum()
    tot_b = df_comp['Cant_B'].sum()

    df_comp['Pct_A'] = (df_comp['Cant_A'] / tot_a * 100) if tot_a > 0 else 0
    df_comp['Pct_B'] = (df_comp['Cant_B'] / tot_b * 100) if tot_b > 0 else 0

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df_comp['Cat_fmt'],
        x=-df_comp['Pct_A'],
        name=lbl_a,
        orientation='h',
        marker=dict(color=COLOR_PERIODO_A),
        text=df_comp['Pct_A'].apply(lambda v: f"{v:.1f}%"),
        textposition='inside',
        hovertemplate="<b>%{y} (" + lbl_a + ")</b><br>Porcentaje: %{text}<br>Cantidad: %{customdata:,}<extra></extra>",
        customdata=df_comp['Cant_A']
    ))

    fig.add_trace(go.Bar(
        y=df_comp['Cat_fmt'],
        x=df_comp['Pct_B'],
        name=lbl_b,
        orientation='h',
        marker=dict(color=COLOR_PERIODO_B),
        text=df_comp['Pct_B'].apply(lambda v: f"{v:.1f}%"),
        textposition='inside',
        hovertemplate="<b>%{y} (" + lbl_b + ")</b><br>Porcentaje: %{text}<br>Cantidad: %{customdata:,}<extra></extra>",
        customdata=df_comp['Cant_B']
    ))

    max_pct = max(df_comp['Pct_A'].max(), df_comp['Pct_B'].max()) * 1.15
    if max_pct == 0: 
        max_pct = 100

    fig.update_layout(
        font=dict(family="Poppins, sans-serif"),
        barmode='overlay',
        bargap=0.2,
        height=340,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", y=1.15, x=0, title=None, font=dict(size=10)),
        xaxis=dict(
            range=[-max_pct, max_pct],
            showticklabels=False,
            zeroline=True,
            zerolinecolor='#e5e7eb',
            zerolinewidth=2
        ),
        yaxis=dict(showgrid=False)
    )

    st.plotly_chart(aplicar_touch_safe(fig), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

def generar_grafico_upres_apilado(df_base, col_target, titulo_grafico):
    st.markdown(f"### {titulo_grafico}")
    
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
    top_5_locales['Rank_Local'] = top_5_locales['Rank_Local'].astype(int)
    top_5_locales['UPRES_fmt'] = top_5_locales['UNIDAD DE ASIGNACIÓN'].apply(acortar_texto_abreviado)
    top_5_locales['Grupo_fmt'] = top_5_locales[col_target].apply(acortar_texto_abreviado)

    upres_ordenadas_fmt = [acortar_texto_abreviado(u) for u in reversed(top_10_upres)]
    df_totales = top_5_locales.groupby('UPRES_fmt', observed=True)['Cant_Local'].sum().reset_index(name='Total')

    paleta_contraste = [
        '#1b4332', '#1d3557', '#d4a373', '#e07a5f', '#2b2d42', 
        '#2d6a4f', '#003049', '#52b788', '#3d405b', '#40916c',
        '#bc4749', '#a5a58d', '#6b705c', '#386641', '#6a040f'
    ]
    
    categorias_unicas = top_5_locales['Grupo_fmt'].unique().tolist()
    color_map = {cat: paleta_contraste[i % len(paleta_contraste)] for i, cat in enumerate(categorias_unicas)}

    fig_stack = go.Figure()

    for rank in range(1, 6):
        sub_rank = top_5_locales[top_5_locales['Rank_Local'] == rank]
        if sub_rank.empty:
            continue
            
        for _, row in sub_rank.iterrows():
            item_nombre = row['Grupo_fmt']
            fig_stack.add_trace(go.Bar(
                y=[row['UPRES_fmt']],
                x=[row['Cant_Local']],
                name=item_nombre,
                legendgroup=item_nombre,
                showlegend=True if item_nombre not in [t.name for t in fig_stack.data] else False,
                orientation='h',
                text=[row['Cant_Local']],
                textposition='inside',
                insidetextanchor='middle',
                customdata=[(rank, item_nombre)],
                hovertemplate="<b>%{y}</b><br>Top %{customdata[0]}: %{customdata[1]}<br>Cantidad: %{x} PQRS<extra></extra>",
                marker=dict(
                    color=color_map.get(item_nombre, '#2e7d32'),
                    line=dict(color='#ffffff', width=1)
                )
            ))

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
        font=dict(family="Poppins, sans-serif"),
        barmode='stack', 
        yaxis=dict(categoryorder='array', categoryarray=upres_ordenadas_fmt),
        xaxis_title="", 
        yaxis_title="", 
        height=500, 
        margin=dict(l=5, r=40, t=10, b=10), 
        legend=dict(orientation="h", y=-0.2, x=0, title=None, font=dict(size=10))
    )
    
    st.plotly_chart(aplicar_touch_safe(fig_stack), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

def generar_barras_100pct_comparativo(df_a, df_b, col_target, titulo_grafico, lbl_a="Periodo A", lbl_b="Periodo B"):
    st.markdown(f"### {titulo_grafico}")

    df_a_clean = df_a.dropna(subset=['UNIDAD DE ASIGNACIÓN', col_target]).copy()
    df_b_clean = df_b.dropna(subset=['UNIDAD DE ASIGNACIÓN', col_target]).copy()

    if df_a_clean.empty and df_b_clean.empty:
        st.info("No hay datos disponibles para la comparación.")
        return

    tot_b_absoluto = df_b_clean['UNIDAD DE ASIGNACIÓN'].value_counts()
    tot_a_absoluto = df_a_clean['UNIDAD DE ASIGNACIÓN'].value_counts()
    
    tot_combinado = tot_b_absoluto.add(tot_a_absoluto * 0, fill_value=0)
    upres_ordenadas_b = tot_combinado.sort_values(ascending=False).head(5).index.tolist()

    df_a_sub = df_a_clean[df_a_clean['UNIDAD DE ASIGNACIÓN'].isin(upres_ordenadas_b)].copy()
    df_b_sub = df_b_clean[df_b_clean['UNIDAD DE ASIGNACIÓN'].isin(upres_ordenadas_b)].copy()

    def procesar_periodo_dinamico(df_in, lbl):
        if df_in.empty:
            return pd.DataFrame(), pd.DataFrame()

        registros_agrupados = []
        totales_absolutos = []

        for upres in upres_ordenadas_b:
            df_u = df_in[df_in['UNIDAD DE ASIGNACIÓN'] == upres]
            if df_u.empty:
                continue

            total_real = len(df_u)
            totales_absolutos.append({
                'UNIDAD DE ASIGNACIÓN': upres,
                'UPRES_fmt': acortar_texto_abreviado(upres),
                'Periodo': lbl,
                'Total_Abs': total_real
            })

            top_5_locales = df_u[col_target].value_counts().head(5).index.tolist()

            df_u_mod = df_u.copy()
            df_u_mod['Cat_Group'] = df_u_mod[col_target].apply(
                lambda c: c if c in top_5_locales else 'Otros'
            )

            g_u = df_u_mod.groupby('Cat_Group', observed=True).size().reset_index(name='Cant')
            g_u['UNIDAD DE ASIGNACIÓN'] = upres
            g_u['UPRES_fmt'] = acortar_texto_abreviado(upres)
            g_u['Periodo'] = lbl
            g_u['Tot_UPRES'] = total_real
            g_u['Pct'] = (g_u['Cant'] / total_real) * 100
            
            rank_map = {cat: i+1 for i, cat in enumerate(top_5_locales)}
            rank_map['Otros'] = 99
            
            g_u['Rank_Local'] = g_u['Cat_Group'].map(rank_map)
            g_u['Cat_fmt'] = g_u['Cat_Group'].apply(lambda c: 'Otros' if c == 'Otros' else acortar_texto_abreviado(c))

            registros_agrupados.append(g_u)

        if not registros_agrupados:
            return pd.DataFrame(), pd.DataFrame()

        df_res = pd.concat(registros_agrupados, ignore_index=True)
        df_tot = pd.DataFrame(totales_absolutos)
        return df_res, df_tot

    df_p1, tot_p1 = procesar_periodo_dinamico(df_a_sub, lbl_a)
    df_p2, tot_p2 = procesar_periodo_dinamico(df_b_sub, lbl_b)

    df_total = pd.concat([df_p1, df_p2], ignore_index=True)
    df_totales_absolutos = pd.concat([tot_p1, tot_p2], ignore_index=True)

    if df_total.empty:
        st.info("No hay datos suficientes en los rangos seleccionados.")
        return

    categorias_unicas_todas = [c for c in df_total['Cat_fmt'].unique() if c != 'Otros']
    paleta_amplia = [
        '#1b4332', '#1d3557', '#d4a373', '#e07a5f', '#2b2d42', 
        '#2d6a4f', '#003049', '#52b788', '#3d405b', '#40916c',
        '#bc4749', '#a5a58d', '#6b705c', '#386641', '#6a040f'
    ]
    color_map = {cat: paleta_amplia[i % len(paleta_amplia)] for i, cat in enumerate(categorias_unicas_todas)}
    color_map['Otros'] = '#8d99ae'

    top_5_upres_fmt = [acortar_texto_abreviado(u) for u in upres_ordenadas_b]
    upres_orden_ascendente = list(reversed(top_5_upres_fmt))

    df_total['UPRES_fmt'] = pd.Categorical(df_total['UPRES_fmt'], categories=upres_orden_ascendente, ordered=True)
    df_total = df_total.sort_values(['UPRES_fmt', 'Periodo', 'Rank_Local'])

    if not df_totales_absolutos.empty:
        df_totales_absolutos['UPRES_fmt'] = pd.Categorical(df_totales_absolutos['UPRES_fmt'], categories=upres_orden_ascendente, ordered=True)
        df_totales_absolutos = df_totales_absolutos.sort_values(['UPRES_fmt', 'Periodo'])

    fig = go.Figure()

    anchor_upres, anchor_periodo = [], []
    for u in upres_orden_ascendente:
        for periodo in (lbl_a, lbl_b):
            anchor_upres.append(u)
            anchor_periodo.append(periodo)

    fig.add_trace(go.Bar(
        y=[anchor_upres, anchor_periodo],
        x=[0] * len(anchor_upres),
        orientation='h',
        marker=dict(color='rgba(0,0,0,0)'),
        showlegend=False,
        hoverinfo='skip',
        width=0.001
    ))

    rangos_locales_existentes = sorted(df_total['Rank_Local'].unique())

    for rank in rangos_locales_existentes:
        df_rank = df_total[df_total['Rank_Local'] == rank]
        if df_rank.empty:
            continue

        for cat_nombre in df_rank['Cat_fmt'].unique():
            df_sub_cat = df_rank[df_rank['Cat_fmt'] == cat_nombre]
            
            fig.add_trace(go.Bar(
                y=[df_sub_cat['UPRES_fmt'].astype(str), df_sub_cat['Periodo']],
                x=df_sub_cat['Pct'],
                name=cat_nombre,
                legendgroup=cat_nombre,
                showlegend=True if cat_nombre not in [t.name for t in fig.data] else False,
                orientation='h',
                marker=dict(color=color_map.get(cat_nombre, '#8d99ae')),
                text=df_sub_cat['Pct'].apply(lambda v: f"{v:.0f}%" if v >= 5 else ""),
                textposition='inside',
                insidetextanchor='middle',
                customdata=df_sub_cat[['Cat_fmt', 'Cant']],
                hovertemplate="<b>%{y[0]} - %{y[1]}</b><br>Categoría: %{customdata[0]}<br>Proporción: %{x:.1f}%<br>Cantidad: %{customdata[1]:,} PQRS<extra></extra>"
            ))

    if not df_totales_absolutos.empty:
        fig.add_trace(go.Scatter(
            y=[df_totales_absolutos['UPRES_fmt'].astype(str), df_totales_absolutos['Periodo']],
            x=[101.5] * len(df_totales_absolutos),
            mode='text',
            text=df_totales_absolutos['Total_Abs'].apply(lambda v: f"<b>{v:,}</b>"),
            textposition='middle right',
            showlegend=False,
            hoverinfo='skip'
        ))

    fig.update_layout(
        font=dict(family="Poppins, sans-serif"),
        barmode='stack',
        bargap=0.45,
        bargroupgap=0.02,
        yaxis=dict(
            title="",
            tickfont=dict(size=11),
            categoryorder='trace'
        ),
        xaxis=dict(title="Proporción Relativa (%)", range=[0, 110]),
        height=580,
        margin=dict(l=10, r=40, t=10, b=10),
        legend=dict(orientation="h", y=-0.18, x=0, title=None, font=dict(size=10))
    )

    st.plotly_chart(aplicar_touch_safe(fig), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

# -----------------------------------------------------------------------------
# 4. MÓDULOS DE RENDERIZADO DE PESTAÑAS
# -----------------------------------------------------------------------------
def render_tab_individual(df_base_global, col_mot_esp, min_f, max_f, df_users_mensual, df_maestro_upres_rases):
    st.caption("Consola Ejecutiva de Atención al Usuario - Periodo Único")

    if "fecha_ind_inicio" not in st.session_state:
        st.session_state["fecha_ind_inicio"] = min_f
    if "fecha_ind_fin" not in st.session_state:
        st.session_state["fecha_ind_fin"] = max_f

    col_fi1, col_fi2 = st.columns(2)
    with col_fi1:
        fecha_ind_inicio = st.date_input("Fecha Inicio", min_value=min_f, max_value=max_f, key="fecha_ind_inicio")
    with col_fi2:
        fecha_ind_fin = st.date_input("Fecha Fin", min_value=min_f, max_value=max_f, key="fecha_ind_fin")

    df_base = df_base_global.copy()
    if fecha_ind_inicio and fecha_ind_fin:
        if fecha_ind_inicio <= fecha_ind_fin:
            df_base = df_base[(df_base['fecha_dt'].dt.date >= fecha_ind_inicio) & (df_base['fecha_dt'].dt.date <= fecha_ind_fin)]
        else:
            st.warning("⚠️ La Fecha Inicio no puede ser posterior a la Fecha Fin.")

    # Obtener usuarios amarrados dinámicamente al mes seleccionado
    dict_rases_users, dict_upres_users = obtener_usuarios_dinamicos(df_base, df_users_mensual, df_maestro_upres_rases)

    top_upres_s = df_base['UNIDAD DE ASIGNACIÓN'].dropna().value_counts()
    top_upres_nom = top_upres_s.index[0] if not top_upres_s.empty else "N/A"
    top_upres_val = top_upres_s.iloc[0] if not top_upres_s.empty else 0

    top_rases_s = df_base[~df_base['RASES'].astype(str).str.upper().str.contains('NIVEL CENTRAL')]['RASES'].dropna().value_counts()
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

    # MAPA DE CALOR POR DEPARTAMENTOS POR CÓDIGO DANE
    st.markdown("""
        <h3 style='display: flex; align-items: center; gap: 8px;'>
            <i class="fa-solid fa-map-location-dot" style="color: #2e7d32;"></i>
            MAPA DE CALOR: Distribución Geográfica PQRS por Departamento
        </h3>
    """, unsafe_allow_html=True)
    
    try:
        colombia_geojson = cargar_geojson_colombia()
    except Exception:
        colombia_geojson = None

    if colombia_geojson:
        df_geo_base = df_base.dropna(subset=['UNIDAD DE ASIGNACIÓN']).copy()
        df_geo_base['CODIGO_DANE'] = df_geo_base['UNIDAD DE ASIGNACIÓN'].apply(obtener_codigo_dane)
        
        df_geo = df_geo_base.dropna(subset=['CODIGO_DANE']).groupby('CODIGO_DANE', observed=True).size().reset_index(name='Cantidad')
        df_geo['CODIGO_DANE'] = df_geo['CODIGO_DANE'].astype(str).str.zfill(2)
        df_geo['Nombre_Dept'] = df_geo['CODIGO_DANE'].map(NOMBRES_DEPARTAMENTOS_MOSTRAR)

        has_choropleth_map = hasattr(px, "choropleth_map")
        
        kwargs_mapa = {
            'data_frame': df_geo,
            'geojson': colombia_geojson,
            'locations': 'CODIGO_DANE',
            'featureidkey': "properties.DPTO_CODE",
            'color': 'Cantidad',
            'color_continuous_scale': "Greens",
            'range_color': (0, df_geo['Cantidad'].max() if not df_geo.empty else 100),
            'zoom': 4.5,
            'center': {"lat": 4.5709, "lon": -74.2973},
            'opacity': 0.85,
            'hover_data': {'CODIGO_DANE': False, 'Nombre_Dept': True, 'Cantidad': True},
            'labels': {'Cantidad': 'PQRS Recepcionadas', 'Nombre_Dept': 'Departamento'}
        }

        if has_choropleth_map:
            kwargs_mapa['map_style'] = "carto-positron"
            fig_mapa = px.choropleth_map(**kwargs_mapa)
        else:
            kwargs_mapa['mapbox_style'] = "carto-positron"
            fig_mapa = px.choropleth_mapbox(**kwargs_mapa)

        fig_mapa.update_layout(
            font=dict(family="Poppins, sans-serif"), 
            height=580, 
            margin=dict(l=0, r=0, t=10, b=0),
            dragmode=False,
            coloraxis_colorbar=dict(
                title="PQRS",
                thicknessmode="pixels", thickness=15,
                lenmode="pixels", len=300
            )
        )
        st.plotly_chart(fig_mapa, use_container_width=True, config=CONFIG_PLOTLY_MAPA)
    else:
        st.info("Visualización del mapa de calor no disponible temporalmente.")

    st.markdown("---")

    st.markdown("""
        <h3 style='display: flex; align-items: center; gap: 8px; margin-bottom: 0px;'>
            <i class="fa-solid fa-chart-pie" style="color: #2e7d32;"></i>
            Porcentaje (%) por Tipo de Solicitud
        </h3>
    """, unsafe_allow_html=True)
    df_pie_sol = df_base['Tipo de Solicitud'].dropna().value_counts().reset_index()
    df_pie_sol.columns = ['Tipo de Solicitud', 'Cantidad']
    df_pie_sol = df_pie_sol[df_pie_sol['Cantidad'] > 0]
    df_pie_sol['Tipo_fmt'] = df_pie_sol['Tipo de Solicitud'].apply(acortar_texto_abreviado)
    
    fig_pie1 = px.pie(
        df_pie_sol, 
        values='Cantidad', 
        names='Tipo_fmt', 
        hole=0.4, 
        color_discrete_sequence=px.colors.sequential.Greens_r
    )
    fig_pie1.update_traces(
        textposition='inside',
        textinfo='percent',
        hoverinfo='label+percent+value',
        insidetextorientation='radial'
    )
    fig_pie1.update_layout(
        font=dict(family="Poppins, sans-serif"), 
        height=400, 
        showlegend=False,
        margin=dict(l=20, r=20, t=10, b=20)
    )
    st.plotly_chart(aplicar_touch_safe(fig_pie1), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

    st.markdown("---")

    st.markdown("""
        <h3 style='display: flex; align-items: center; gap: 8px; margin-bottom: 0px;'>
            <i class="fa-solid fa-inbox" style="color: #2e7d32;"></i>
            Porcentaje (%) por Medio de Recepción
        </h3>
    """, unsafe_allow_html=True)
    df_pie_med = df_base['Medio de Recepción'].dropna().value_counts().reset_index()
    df_pie_med.columns = ['Medio de Recepción', 'Cantidad']
    df_pie_med = df_pie_med[df_pie_med['Cantidad'] > 0]
    df_pie_med['Medio_fmt'] = df_pie_med['Medio de Recepción'].apply(acortar_texto_abreviado)
    
    fig_pie2 = px.pie(
        df_pie_med, 
        values='Cantidad', 
        names='Medio_fmt', 
        hole=0.4, 
        color_discrete_sequence=px.colors.sequential.YlGn_r
    )
    fig_pie2.update_traces(
        textposition='inside',
        textinfo='percent',
        hoverinfo='label+percent+value',
        insidetextorientation='radial'
    )
    fig_pie2.update_layout(
        font=dict(family="Poppins, sans-serif"), 
        height=400, 
        showlegend=False,
        margin=dict(l=20, r=20, t=10, b=20)
    )
    st.plotly_chart(aplicar_touch_safe(fig_pie2), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

    st.markdown("---")

    # -----------------------------------------------------------------------------
    # PQRS POR RASES (CON ALTERNANCIA DE TASA POR 1.000 USUARIOS ATENDIDOS - SIN NIVEL CENTRAL)
    # -----------------------------------------------------------------------------
    col_tit_r, col_btn_r = st.columns([3, 1])
    with col_tit_r:
        st.markdown("""
            <h3 style='display: flex; align-items: center; gap: 8px;'>
                <i class="fa-solid fa-sitemap" style="color: #2e7d32;"></i>
                PQRS por RASES
            </h3>
        """, unsafe_allow_html=True)
    with col_btn_r:
        ver_tasa_rases = st.toggle("PQRS por cada 1000 usuarios atendidos", key="tasa_rases_ind")

    df_g1_raw = df_base['RASES'].dropna().value_counts().reset_index()
    df_g1_raw.columns = ['RASES', 'Cantidad']

    # Filtrado estricto: Eliminar vacíos, nulos y "NIVEL CENTRAL"
    df_g1 = df_g1_raw[
        (df_g1_raw['Cantidad'] > 0) & 
        (df_g1_raw['RASES'].astype(str).str.strip() != '') &
        (~df_g1_raw['RASES'].astype(str).str.upper().str.contains('NIVEL CENTRAL'))
    ].copy()

    df_g1['RASES_fmt'] = df_g1['RASES'].apply(acortar_texto_abreviado)
    df_g1['Usuarios'] = df_g1['RASES'].map(dict_rases_users).fillna(0)

    if ver_tasa_rases:
        df_g1['Valor_Graficar'] = df_g1.apply(
            lambda r: (r['Cantidad'] / r['Usuarios'] * 1000) if r['Usuarios'] > 0 else 0, axis=1
        )
        y_label_r = "Tasa por 1.000 Usu."
        df_g1['Texto_Barra'] = df_g1['Valor_Graficar'].apply(lambda v: f"{v:.2f}")
        hovertemplate_r = "<b>%{x}</b><br>Tasa: %{y:.2f} por 1.000 usuarios<br>Cantidad PQRS: %{customdata[0]:,}<br>Usuarios: %{customdata[1]:,}<extra></extra>"
    else:
        df_g1['Valor_Graficar'] = df_g1['Cantidad']
        y_label_r = "Cantidad PQRS"
        df_g1['Texto_Barra'] = df_g1['Valor_Graficar'].apply(lambda v: f"{v:,.0f}")
        hovertemplate_r = "<b>%{x}</b><br>Cantidad: %{y:,} PQRS<br>Usuarios: %{customdata[1]:,}<extra></extra>"

    df_g1 = df_g1.sort_values(by='Valor_Graficar', ascending=False)

    fig1 = px.bar(
        df_g1, 
        x='RASES_fmt', 
        y='Valor_Graficar', 
        text='Texto_Barra', 
        color_discrete_sequence=[COLOR_PERIODO_A],
        labels={'Valor_Graficar': y_label_r, 'RASES_fmt': ''},
        custom_data=['Cantidad', 'Usuarios']
    )
    fig1.update_traces(
        textposition='outside',
        hovertemplate=hovertemplate_r
    )
    fig1.update_layout(
        font=dict(family="Poppins, sans-serif"), 
        xaxis=dict(categoryorder='array', categoryarray=df_g1['RASES_fmt'].tolist()),
        xaxis_title="", 
        yaxis_title="", 
        height=330, 
        margin=dict(l=5, r=5, t=20, b=10)
    )
    st.plotly_chart(aplicar_touch_safe(fig1), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

    # -----------------------------------------------------------------------------
    # PQRS POR UPRES (CON ALTERNANCIA DE TASA POR 1.000 USUARIOS ATENDIDOS)
    # -----------------------------------------------------------------------------
    col_tit_u, col_btn_u = st.columns([3, 1])
    with col_tit_u:
        st.markdown("""
            <h3 style='display: flex; align-items: center; gap: 8px;'>
                <i class="fa-solid fa-hospital" style="color: #2e7d32;"></i>
                PQRS por UPRES
            </h3>
        """, unsafe_allow_html=True)
    with col_btn_u:
        ver_tasa_upres = st.toggle("PQRS por cada 1000 usuarios atendidos", key="tasa_upres_ind")

    df_u1_raw = df_base['UNIDAD DE ASIGNACIÓN'].dropna().value_counts().reset_index()
    df_u1_raw.columns = ['UPRES', 'Cantidad']
    df_u1 = df_u1_raw[(df_u1_raw['Cantidad'] > 0) & (df_u1_raw['UPRES'].astype(str).str.strip() != '')].copy()
    df_u1['UPRES_fmt'] = df_u1['UPRES'].apply(acortar_texto_abreviado)
    df_u1['Usuarios'] = df_u1['UPRES'].map(dict_upres_users).fillna(0)

    if ver_tasa_upres:
        df_u1['Valor_Graficar'] = df_u1.apply(
            lambda r: (r['Cantidad'] / r['Usuarios'] * 1000) if r['Usuarios'] > 0 else 0, axis=1
        )
        y_label_u = "Tasa por 1.000 Usu."
        df_u1['Texto_Barra'] = df_u1['Valor_Graficar'].apply(lambda v: f"{v:.2f}")
        hovertemplate_u = "<b>%{x}</b><br>Tasa: %{y:.2f} por 1.000 usuarios<br>Cantidad PQRS: %{customdata[0]:,}<br>Usuarios: %{customdata[1]:,}<extra></extra>"
    else:
        df_u1['Valor_Graficar'] = df_u1['Cantidad']
        y_label_u = "Cantidad PQRS"
        df_u1['Texto_Barra'] = df_u1['Valor_Graficar'].apply(lambda v: f"{v:,.0f}")
        hovertemplate_u = "<b>%{x}</b><br>Cantidad: %{y:,} PQRS<br>Usuarios: %{customdata[1]:,}<extra></extra>"

    df_u1 = df_u1.sort_values(by='Valor_Graficar', ascending=False).head(10)

    fig_upres_simple = px.bar(
        df_u1, 
        x='UPRES_fmt', 
        y='Valor_Graficar', 
        text='Texto_Barra',
        color_discrete_sequence=[COLOR_PERIODO_A],
        labels={'Valor_Graficar': y_label_u, 'UPRES_fmt': ''},
        custom_data=['Cantidad', 'Usuarios']
    )
    fig_upres_simple.update_traces(
        textposition='outside',
        hovertemplate=hovertemplate_u
    )
    fig_upres_simple.update_layout(
        font=dict(family="Poppins, sans-serif"), 
        xaxis=dict(categoryorder='array', categoryarray=df_u1['UPRES_fmt'].tolist()),
        xaxis_title="", 
        yaxis_title="", 
        height=360, 
        margin=dict(l=5, r=5, t=20, b=10)
    )
    st.plotly_chart(aplicar_touch_safe(fig_upres_simple), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

    generar_grafico_upres_apilado(df_base, 'ESPECIALIDAD_CATEGORIA', "Distribución por UPRES - Categoría Salud (Top 5)")
    generar_grafico_upres_apilado(df_base, col_mot_esp, "Distribución por UPRES - Motivo Específico (Top 5)")

def render_tab_comparativo(df_base_global, col_mot_esp, min_hist, max_hist, df_users_mensual, df_maestro_upres_rases):
    st.caption("Comparación Analítica Cruzada entre dos Ventanas de Tiempo")

    if "fecha_a_inicio" not in st.session_state:
        st.session_state["fecha_a_inicio"] = min_hist
    if "fecha_a_fin" not in st.session_state:
        st.session_state["fecha_a_fin"] = min_hist + pd.Timedelta(days=30) if min_hist else max_hist

    if "fecha_b_inicio" not in st.session_state:
        st.session_state["fecha_b_inicio"] = max_hist - pd.Timedelta(days=30) if max_hist else min_hist
    if "fecha_b_fin" not in st.session_state:
        st.session_state["fecha_b_fin"] = max_hist

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.markdown("### Periodo A (Base)")
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            fecha_a_inicio = st.date_input("Fecha Inicio A", min_value=min_hist, max_value=max_hist, key="fecha_a_inicio")
        with col_a2:
            fecha_a_fin = st.date_input("Fecha Fin A", min_value=min_hist, max_value=max_hist, key="fecha_a_fin")

    with col_p2:
        st.markdown("### Periodo B (Comparado)")
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            fecha_b_inicio = st.date_input("Fecha Inicio B", min_value=min_hist, max_value=max_hist, key="fecha_b_inicio")
        with col_b2:
            fecha_b_fin = st.date_input("Fecha Fin B", min_value=min_hist, max_value=max_hist, key="fecha_b_fin")

    if fecha_a_inicio and fecha_a_fin and fecha_b_inicio and fecha_b_fin:
        if fecha_a_inicio > fecha_a_fin or fecha_b_inicio > fecha_b_fin:
            st.warning("⚠️ En uno de los periodos, la Fecha Inicio es mayor a la Fecha Fin.")
            return

        lbl_a_short = "Periodo A"
        lbl_b_short = "Periodo B"
        vs_header = f"{fecha_a_inicio.strftime('%d/%m/%Y')} – {fecha_a_fin.strftime('%d/%m/%Y')} 🆚 {fecha_b_inicio.strftime('%d/%m/%Y')} – {fecha_b_fin.strftime('%d/%m/%Y')}"

        df_a = df_base_global[(df_base_global['fecha_dt'].dt.date >= fecha_a_inicio) & (df_base_global['fecha_dt'].dt.date <= fecha_a_fin)].copy()
        df_b = df_base_global[(df_base_global['fecha_dt'].dt.date >= fecha_b_inicio) & (df_base_global['fecha_dt'].dt.date <= fecha_b_fin)].copy()

        dict_rases_users_a, dict_upres_users_a = obtener_usuarios_dinamicos(df_a, df_users_mensual, df_maestro_upres_rases)
        dict_rases_users_b, dict_upres_users_b = obtener_usuarios_dinamicos(df_b, df_users_mensual, df_maestro_upres_rases)

        tot_a, tot_b = len(df_a), len(df_b)
        diff_abs = tot_b - tot_a
        diff_pct = ((diff_abs / tot_a) * 100) if tot_a > 0 else 0.0

        st.markdown("---")
        st.markdown(f"### <i class='fa-solid fa-scale-balanced' style='color:#1b5e20;'></i> Indicadores Comparativos Generales ({vs_header})", unsafe_allow_html=True)
        kc1, kc2, kc3 = st.columns(3)
        kc1.metric(f"Total {lbl_a_short}", f"{tot_a:,}")
        kc2.metric(f"Total {lbl_b_short}", f"{tot_b:,}")
        
        kc3.metric(
            "Variación Periodo B vs A",
            f"{diff_abs:+,}",
            delta=f"{diff_abs:+,} tickets ({diff_pct:+.1f}%)",
            delta_color="inverse"
        )

        st.markdown("---")

        mapa_color_comp = {lbl_a_short: COLOR_PERIODO_A, lbl_b_short: COLOR_PERIODO_B}

        col_cp1, col_cp2 = st.columns(2)
        with col_cp1:
            generar_grafico_mariposa(df_a, df_b, 'Tipo de Solicitud', "Comparativo Tipo de Solicitud", lbl_a=lbl_a_short, lbl_b=lbl_b_short)

        with col_cp2:
            generar_grafico_mariposa(df_a, df_b, 'Medio de Recepción', "Comparativo Medio de Recepción", lbl_a=lbl_a_short, lbl_b=lbl_b_short)

        st.markdown("---")

        # -----------------------------------------------------------------------------
        # COMPARATIVO POR RASES (TASA VS CANTIDAD - SIN NIVEL CENTRAL)
        # -----------------------------------------------------------------------------
        col_tit_cr, col_btn_cr = st.columns([3, 1])
        with col_tit_cr:
            st.markdown("""
                <h3 style='display: flex; align-items: center; gap: 8px;'>
                    <i class="fa-solid fa-diagram-project" style="color: #2e7d32;"></i>
                    Comparativo por RASES
                </h3>
            """, unsafe_allow_html=True)
        with col_btn_cr:
            ver_tasa_comp_rases = st.toggle("PQRS por cada 1000 usuarios atendidos", key="tasa_rases_comp")

        df_r_a = df_a['RASES'].dropna().value_counts().reset_index()
        df_r_a.columns = ['RASES', 'Cantidad']
        df_r_a['Periodo'] = lbl_a_short
        df_r_a['Usuarios'] = df_r_a['RASES'].map(dict_rases_users_a).fillna(0)

        df_r_b = df_b['RASES'].dropna().value_counts().reset_index()
        df_r_b.columns = ['RASES', 'Cantidad']
        df_r_b['Periodo'] = lbl_b_short
        df_r_b['Usuarios'] = df_r_b['RASES'].map(dict_rases_users_b).fillna(0)

        df_comp_rases = pd.concat([df_r_a, df_r_b])

        # Filtrado estricto: Eliminar vacíos, nulos y "NIVEL CENTRAL"
        df_comp_rases = df_comp_rases[
            (df_comp_rases['Cantidad'] > 0) & 
            (df_comp_rases['RASES'].astype(str).str.strip() != '') &
            (~df_comp_rases['RASES'].astype(str).str.upper().str.contains('NIVEL CENTRAL'))
        ].copy()

        df_comp_rases['RASES_fmt'] = df_comp_rases['RASES'].apply(acortar_texto_abreviado)

        if ver_tasa_comp_rases:
            df_comp_rases['Valor_Graficar'] = df_comp_rases.apply(
                lambda r: (r['Cantidad'] / r['Usuarios'] * 1000) if r['Usuarios'] > 0 else 0, axis=1
            )
            df_comp_rases['Texto_Barra'] = df_comp_rases['Valor_Graficar'].apply(lambda v: f"{v:.2f}")
            hovertemplate_cr = "<b>%{x} (%{fullData.name})</b><br>Tasa: %{y:.2f} por 1.000 usuarios<br>Cantidad PQRS: %{customdata[0]:,}<br>Usuarios: %{customdata[1]:,}<extra></extra>"
        else:
            df_comp_rases['Valor_Graficar'] = df_comp_rases['Cantidad']
            df_comp_rases['Texto_Barra'] = df_comp_rases['Valor_Graficar'].apply(lambda v: f"{v:,.0f}")
            hovertemplate_cr = "<b>%{x} (%{fullData.name})</b><br>Cantidad: %{y:,} PQRS<br>Usuarios: %{customdata[1]:,}<extra></extra>"

        orden_rases_comp = df_comp_rases.groupby('RASES_fmt')['Valor_Graficar'].sum().sort_values(ascending=False).index.tolist()

        fig_comp_rases = px.bar(
            df_comp_rases, 
            x='RASES_fmt', 
            y='Valor_Graficar', 
            text='Texto_Barra',
            color='Periodo', 
            barmode='group',
            color_discrete_map=mapa_color_comp,
            custom_data=['Cantidad', 'Usuarios']
        )
        fig_comp_rases.update_traces(
            textposition='outside',
            hovertemplate=hovertemplate_cr
        )
        fig_comp_rases.update_layout(
            font=dict(family="Poppins, sans-serif"), 
            xaxis=dict(categoryorder='array', categoryarray=orden_rases_comp),
            xaxis_title="", 
            yaxis_title="", 
            height=340, 
            margin=dict(l=10, r=10, t=30, b=10), 
            legend=dict(orientation="h", y=1.15, x=0, title=None, font=dict(size=10))
        )
        st.plotly_chart(aplicar_touch_safe(fig_comp_rases), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

        # -----------------------------------------------------------------------------
        # COMPARATIVO POR UPRES (TASA VS CANTIDAD - ORDENADO SEGÚN PERIODO B)
        # -----------------------------------------------------------------------------
        col_tit_cu, col_btn_cu = st.columns([3, 1])
        with col_tit_cu:
            st.markdown("""
                <h3 style='display: flex; align-items: center; gap: 8px;'>
                    <i class="fa-solid fa-hospital-user" style="color: #2e7d32;"></i>
                    Comparativo PQRS por UPRES
                </h3>
            """, unsafe_allow_html=True)
        with col_btn_cu:
            ver_tasa_comp_upres = st.toggle("PQRS por cada 1000 usuarios atendidos", key="tasa_upres_comp")

        df_u_comp_a = df_a['UNIDAD DE ASIGNACIÓN'].dropna().value_counts().reset_index()
        df_u_comp_a.columns = ['UNIDAD DE ASIGNACIÓN', 'Cantidad']
        df_u_comp_a['Periodo'] = lbl_a_short
        df_u_comp_a['Usuarios'] = df_u_comp_a['UNIDAD DE ASIGNACIÓN'].map(dict_upres_users_a).fillna(0)

        df_u_comp_b = df_b['UNIDAD DE ASIGNACIÓN'].dropna().value_counts().reset_index()
        df_u_comp_b.columns = ['UNIDAD DE ASIGNACIÓN', 'Cantidad']
        df_u_comp_b['Periodo'] = lbl_b_short
        df_u_comp_b['Usuarios'] = df_u_comp_b['UNIDAD DE ASIGNACIÓN'].map(dict_upres_users_b).fillna(0)

        df_comp_upres_simple = pd.concat([df_u_comp_a, df_u_comp_b])
        df_comp_upres_simple = df_comp_upres_simple[(df_comp_upres_simple['Cantidad'] > 0) & (df_comp_upres_simple['UNIDAD DE ASIGNACIÓN'].astype(str).str.strip() != '')].copy()
        
        df_comp_upres_simple['UPRES_fmt'] = df_comp_upres_simple['UNIDAD DE ASIGNACIÓN'].apply(acortar_texto_abreviado)

        if ver_tasa_comp_upres:
            df_comp_upres_simple['Valor_Graficar'] = df_comp_upres_simple.apply(
                lambda r: (r['Cantidad'] / r['Usuarios'] * 1000) if r['Usuarios'] > 0 else 0, axis=1
            )
            df_comp_upres_simple['Texto_Barra'] = df_comp_upres_simple['Valor_Graficar'].apply(lambda v: f"{v:.2f}")
            hovertemplate_cu = "<b>%{x} (%{fullData.name})</b><br>Tasa: %{y:.2f} por 1.000 usuarios<br>Cantidad PQRS: %{customdata[0]:,}<br>Usuarios: %{customdata[1]:,}<extra></extra>"
        else:
            df_comp_upres_simple['Valor_Graficar'] = df_comp_upres_simple['Cantidad']
            df_comp_upres_simple['Texto_Barra'] = df_comp_upres_simple['Valor_Graficar'].apply(lambda v: f"{v:,.0f}")
            hovertemplate_cu = "<b>%{x} (%{fullData.name})</b><br>Cantidad: %{y:,} PQRS<br>Usuarios: %{customdata[1]:,}<extra></extra>"

        # ORDENAR DE MAYOR A MENOR SEGÚN EL VALOR DEL PERIODO B
        df_p_b_metrics = df_comp_upres_simple[df_comp_upres_simple['Periodo'] == lbl_b_short]
        top_10_comp_upres = df_p_b_metrics.sort_values('Valor_Graficar', ascending=False).head(10)['UNIDAD DE ASIGNACIÓN'].tolist()
        
        df_comp_upres_simple = df_comp_upres_simple[df_comp_upres_simple['UNIDAD DE ASIGNACIÓN'].isin(top_10_comp_upres)].copy()
        orden_upres_comp = [acortar_texto_abreviado(u) for u in top_10_comp_upres]

        fig_comp_upres_simple = px.bar(
            df_comp_upres_simple, 
            x='UPRES_fmt', 
            y='Valor_Graficar', 
            text='Texto_Barra',
            color='Periodo', 
            barmode='group',
            color_discrete_map=mapa_color_comp,
            category_orders={'UPRES_fmt': orden_upres_comp},
            custom_data=['Cantidad', 'Usuarios']
        )
        fig_comp_upres_simple.update_traces(
            textposition='outside',
            hovertemplate=hovertemplate_cu
        )
        fig_comp_upres_simple.update_layout(
            font=dict(family="Poppins, sans-serif"), 
            xaxis_title="", 
            yaxis_title="", 
            height=360, 
            margin=dict(l=10, r=10, t=30, b=10), 
            legend=dict(orientation="h", y=1.15, x=0, title=None, font=dict(size=10))
        )
        st.plotly_chart(aplicar_touch_safe(fig_comp_upres_simple), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)

        st.markdown("---")

        generar_barras_100pct_comparativo(
            df_a, df_b, 
            'ESPECIALIDAD_CATEGORIA', 
            "Comparativo Distribución (%) por UPRES - Categoría Salud (Top 5 por UPRES)",
            lbl_a=lbl_a_short,
            lbl_b=lbl_b_short
        )
        
        generar_barras_100pct_comparativo(
            df_a, df_b, 
            col_mot_esp, 
            "Comparativo Distribución (%) por UPRES - Motivo Específico (Top 5 por UPRES)",
            lbl_a=lbl_a_short,
            lbl_b=lbl_b_short
        )

# -----------------------------------------------------------------------------
# 5. AUTENTICACIÓN Y EJECUCIÓN
# -----------------------------------------------------------------------------
try:
    with open('config.yaml', 'r', encoding='utf-8') as file:
        config = yaml.load(file, Loader=SafeLoader)
except FileNotFoundError:
    st.error("❌ No se encontró el archivo de configuración `config.yaml`.")
    st.stop()

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

name, authentication_status, username = authenticator.login('main')

if authentication_status is False:
    st.error("Usuario o contraseña incorrectos")
elif authentication_status is None:
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

    # Funciones de Verificación e Invalidation de Caché Dinámica
    def obtener_ultimo_conteo_bd(engine):
        try:
            query = 'SELECT COUNT(*) AS total FROM "V_SIPQR2S_CONSOLIDADO";'
            df_cnt = pd.read_sql(query, con=engine)
            return int(df_cnt['total'].iloc[0])
        except Exception:
            return 0

    @st.cache_data(show_spinner="Cargando datos consolidados...")
    def cargar_datos_consolidados(total_registros_bd):
        query = '''
            SELECT 
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

    @st.cache_data(ttl="1h")
    def cargar_usuarios_mensuales():
        try:
            query = 'SELECT "UNIDAD", "ANIO", "MES", "USUARIOS" FROM "USUARIOS_ATENDIDOS_MENSUAL";'
            df_u = pd.read_sql(query, con=engine)
            df_u['USUARIOS'] = pd.to_numeric(df_u['USUARIOS'], errors='coerce').fillna(0)
            return df_u
        except Exception:
            return pd.DataFrame()

    @st.cache_data(ttl="1h")
    def cargar_maestro_upres_rases():
        try:
            query = 'SELECT DISTINCT "UNIDAD", "RASES" FROM "UPRES_RASES";'
            return pd.read_sql(query, con=engine)
        except Exception:
            return pd.DataFrame()

    try:
        conteo_actual_bd = obtener_ultimo_conteo_bd(engine)
        df_raw = cargar_datos_consolidados(conteo_actual_bd)
        df_users_mensual = cargar_usuarios_mensuales()
        df_maestro_upres_rases = cargar_maestro_upres_rases()

        min_global_date = df_raw['fecha_dt'].min().date() if not df_raw.empty else None
        max_global_date = df_raw['fecha_dt'].max().date() if not df_raw.empty else None
    except Exception as e:
        st.error(f"Error conectando a la base de datos: {e}")
        st.stop()

    prefs = cargar_preferencias()

    def restablecer_filtros_callback():
        st.session_state["sel_rases"] = []
        st.session_state["sel_unidades"] = []
        st.session_state["sel_cat"] = []
        st.session_state["sel_motivos"] = []
        st.session_state["sel_tipos"] = []
        st.session_state["sel_medios"] = []
        guardar_preferencias({})

    for clave_filtro in ["sel_rases", "sel_unidades", "sel_cat", "sel_motivos", "sel_tipos", "sel_medios"]:
        if clave_filtro not in st.session_state:
            st.session_state[clave_filtro] = prefs.get(clave_filtro, [])

    st.sidebar.markdown(f"👤 **{name}**")
    authenticator.logout('Cerrar Sesión', 'sidebar')
    st.sidebar.markdown("---")
    st.sidebar.markdown("<h3 style='font-size: 1.1rem;'><i class='fa-solid fa-filter' style='color:#1b5e20;'></i> Filtros Globales de Control</h3>", unsafe_allow_html=True)

    lista_rases = sorted([x for x in df_raw['RASES'].dropna().unique() if str(x).strip() != '' and 'NIVEL CENTRAL' not in str(x).upper()])
    sel_rases = st.sidebar.multiselect("RASES", options=lista_rases, key="sel_rases")

    lista_unidades = sorted([x for x in df_raw['UNIDAD DE ASIGNACIÓN'].dropna().unique() if str(x).strip() != ''])
    sel_unidades = st.sidebar.multiselect("UPRES", options=lista_unidades, key="sel_unidades")

    cat_ordenadas = [c for c in df_raw['ESPECIALIDAD_CATEGORIA'].dropna().value_counts().index if str(c).strip() != '']
    sel_cat = st.sidebar.multiselect("Categoría Salud", options=cat_ordenadas, placeholder="Seleccione categoría...", key="sel_cat")

    col_mot_esp = 'MOTIVO ESPECÍFICO' if 'MOTIVO ESPECÍFICO' in df_raw.columns else 'MOTIVO GENERAL'
    motivos_ordenados = [m for m in df_raw[col_mot_esp].dropna().value_counts().index if str(m).strip() != '']
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

    st.markdown("""
        <h1 style='display: flex; align-items: center; gap: 12px; margin-bottom: 0px;'>
            <i class="fa-solid fa-shield-halved" style="color: #1b5e20;"></i>
            SIPQR2S Sanidad
        </h1>
    """, unsafe_allow_html=True)
    
    if "active_tab" not in st.session_state:
        st.session_state["active_tab"] = "📊 Análisis Individual"

    tab_seleccionada = st.radio(
        "Navegación",
        options=["📊 Análisis Individual", "🔄 Comparativo"],
        index=0 if st.session_state["active_tab"] == "📊 Análisis Individual" else 1,
        horizontal=True,
        key="tab_selector"
    )
    
    st.session_state["active_tab"] = tab_seleccionada

    st.markdown("---")

    if tab_seleccionada == "📊 Análisis Individual":
        render_tab_individual(df_base_global, col_mot_esp, min_global_date, max_global_date, df_users_mensual, df_maestro_upres_rases)
    elif tab_seleccionada == "🔄 Comparativo":
        render_tab_comparativo(df_base_global, col_mot_esp, min_global_date, max_global_date, df_users_mensual, df_maestro_upres_rases)