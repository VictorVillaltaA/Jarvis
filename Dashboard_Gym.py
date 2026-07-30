# Dashboard_Gym.py
import streamlit as st
import pandas as pd
from datetime import datetime

import firebase_admin
from firebase_admin import credentials, firestore
import os

import json

if not firebase_admin._apps:
    cred_dict = json.loads(st.secrets["firebase"]["credenciales"])
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
if not firebase_admin._apps:
    cred = credentials.Certificate(RUTA_CREDENCIALES)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="J.A.R.V.I.S. GYM",
    page_icon="🏋️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS CUSTOM (Neón oscuro: azules, rosados, morados) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;600;700&display=swap');

    .stApp {
        background: linear-gradient(135deg, #050014 0%, #0a0025 40%, #120035 100%);
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a0020 0%, #15003a 100%);
        border-right: 1px solid #FF00FF44;
    }
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown label {
        color: #E0E0E0;
    }

    /* Título principal */
    .main-title {
        font-family: 'Orbitron', monospace;
        font-size: 2.8rem;
        font-weight: 900;
        text-align: center;
        background: linear-gradient(90deg, #00FFFF, #FF00FF, #9900FF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding: 20px 0 5px 0;
        letter-spacing: 3px;
    }
    .sub-title {
        font-family: 'Inter', sans-serif;
        font-size: 1rem;
        text-align: center;
        color: #9090B0;
        margin-bottom: 30px;
    }

    /* Tarjetas de métricas */
    .metric-card {
        background: linear-gradient(145deg, #1a0040 0%, #0d0025 100%);
        border: 1px solid #FF00FF55;
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 0 20px #FF00FF22, inset 0 0 30px #00000066;
    }
    .metric-value {
        font-family: 'Orbitron', monospace;
        font-size: 2.4rem;
        font-weight: 700;
        color: #00FFFF;
    }
    .metric-label {
        font-family: 'Inter', sans-serif;
        font-size: 0.85rem;
        color: #A0A0C0;
        margin-top: 5px;
        text-transform: uppercase;
        letter-spacing: 1.5px;
    }

    /* Sección */
    .section-header {
        font-family: 'Orbitron', monospace;
        font-size: 1.3rem;
        color: #FF00FF;
        border-bottom: 2px solid #FF00FF44;
        padding-bottom: 8px;
        margin: 30px 0 15px 0;
        letter-spacing: 2px;
    }

    /* Tablas */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
    }
    .stDataFrame table {
        background-color: #120024 !important;
    }
    .stDataFrame thead th {
        background-color: #1a0040 !important;
        color: #FF00FF !important;
        font-family: 'Orbitron', monospace;
        font-size: 0.75rem;
        letter-spacing: 1px;
    }
    .stDataFrame tbody td {
        color: #E0E0E0 !important;
        border-bottom: 1px solid #330055 !important;
    }

    /* Selectbox y multiselect */
    .stSelectbox > div > div,
    .stMultiSelect > div > div {
        background-color: #1a0040;
        border: 1px solid #FF00FF55;
        color: #E0E0E0;
    }

    /* Botón de refresh */
    .stButton > button {
        background: linear-gradient(90deg, #FF00FF, #9900FF);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: bold;
        font-family: 'Inter', sans-serif;
        padding: 8px 24px;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background: linear-gradient(90deg, #00FFFF, #0088FF);
        box-shadow: 0 0 15px #00FFFF66;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1a0040;
        color: #A0A0C0;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        font-weight: bold;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2D004E;
        color: #00FFFF;
        border-bottom: 3px solid #00FFFF;
    }

    /* Gráficas */
    .stPlotlyChart {
        border-radius: 12px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)


# --- FUNCIONES DE DATOS ---
@st.cache_data(ttl=30)
def cargar_datos_gym():
    """Lee rutinas nuevas y conserva visibles los registros históricos de gimnasio."""
    docs = list(db.collection('rutina_gym').stream()) + list(db.collection('gimnasio').stream())
    filas = []
    for doc in docs:
        data = doc.to_dict()
        fecha = data.get('fecha', 'Sin fecha')
        grupo = data.get('grupo_muscular', 'N/A')
        for r in data.get('registros', []):
            filas.append({
                'Fecha': fecha,
                'Grupo Muscular': grupo,
                'Persona': str(r.get('persona', 'N/A')).upper(),
                'Ejercicio': r.get('ejercicio', 'N/A'),
                'Unidad': r.get('unidad', 'LBS'),
                'Serie': r.get('serie', 0),
                'Peso': r.get('peso', 0),
                'Reps': r.get('reps', 0),
                'Nota': r.get('nota') or ''
            })
    if not filas:
        return pd.DataFrame(columns=['Fecha','Grupo Muscular','Persona','Ejercicio','Unidad','Serie','Peso','Reps','Nota'])
    df = pd.DataFrame(filas)
    df['Peso'] = pd.to_numeric(df['Peso'], errors='coerce').fillna(0)
    df['Reps'] = pd.to_numeric(df['Reps'], errors='coerce').fillna(0).astype(int)
    df['Serie'] = pd.to_numeric(df['Serie'], errors='coerce').fillna(0).astype(int)
    df = df.sort_values(by=['Fecha', 'Ejercicio', 'Persona', 'Serie']).reset_index(drop=True)
    return df


# --- SIDEBAR ---
with st.sidebar:
    st.markdown("## ⚙️ Filtros")
    
    if st.button("🔄 Actualizar Datos", use_container_width=True):
        st.cache_data.clear()

    df_all = cargar_datos_gym()

    if df_all.empty:
        st.warning("No hay registros de gimnasio todavía. Manda tu primera rutina a Jarvis por Telegram.")
        personas_sel = []
        ejercicios_sel = []
        grupos_sel = []
    else:
        personas_disponibles = sorted(df_all['Persona'].unique().tolist())
        personas_sel = st.multiselect("Persona", personas_disponibles, default=personas_disponibles)

        grupos_disponibles = sorted(df_all['Grupo Muscular'].unique().tolist())
        grupos_sel = st.multiselect("Grupo Muscular", grupos_disponibles, default=grupos_disponibles)

        ejercicios_disponibles = sorted(df_all['Ejercicio'].unique().tolist())
        ejercicios_sel = st.multiselect("Ejercicio", ejercicios_disponibles, default=ejercicios_disponibles)

# --- CONTENIDO PRINCIPAL ---
st.markdown('<div class="main-title">🏋️ J.A.R.V.I.S. GYM</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Sistema de Análisis de Rendimiento Físico</div>', unsafe_allow_html=True)

df_all = cargar_datos_gym()

if df_all.empty:
    st.info("🔌 No hay datos en la colección **rutina_gym** de Firebase. Envíale tu primera rutina a Jarvis por Telegram para comenzar.")
    st.stop()

# Aplicar filtros
df = df_all.copy()
if personas_sel:
    df = df[df['Persona'].isin(personas_sel)]
if grupos_sel:
    df = df[df['Grupo Muscular'].isin(grupos_sel)]
if ejercicios_sel:
    df = df[df['Ejercicio'].isin(ejercicios_sel)]

if df.empty:
    st.warning("No hay resultados con los filtros seleccionados.")
    st.stop()

# --- MÉTRICAS ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f'''<div class="metric-card">
        <div class="metric-value">{df["Fecha"].nunique()}</div>
        <div class="metric-label">Sesiones</div>
    </div>''', unsafe_allow_html=True)
with col2:
    st.markdown(f'''<div class="metric-card">
        <div class="metric-value">{df["Ejercicio"].nunique()}</div>
        <div class="metric-label">Ejercicios</div>
    </div>''', unsafe_allow_html=True)
with col3:
    st.markdown(f'''<div class="metric-card">
        <div class="metric-value">{df["Peso"].max():.0f}</div>
        <div class="metric-label">Peso Máx</div>
    </div>''', unsafe_allow_html=True)
with col4:
    total_vol = (df['Peso'] * df['Reps']).sum()
    st.markdown(f'''<div class="metric-card">
        <div class="metric-value">{total_vol:,.0f}</div>
        <div class="metric-label">Volumen Total</div>
    </div>''', unsafe_allow_html=True)

st.markdown("")

# --- TABS ---
tab_progreso, tab_historial, tab_notas = st.tabs(["📈 Progreso", "📋 Historial", "📝 Notas"])

with tab_progreso:
    st.markdown('<div class="section-header">EVOLUCIÓN DE PESO MÁXIMO POR EJERCICIO</div>', unsafe_allow_html=True)

    df_progreso = df.copy()
    # 2. Convertir la fecha para ignorar la hora
    df_progreso['Fecha'] = pd.to_datetime(df_progreso['Fecha'], errors='coerce').dt.strftime('%Y-%m-%d')

    peso_max = df_progreso.groupby(['Fecha', 'Ejercicio', 'Persona'])['Peso'].max().reset_index()

    if len(personas_sel) <= 1:
        color_col = 'Ejercicio'
    else:
        color_col = 'Persona'

    import plotly.express as px

    fig = px.line(
        peso_max, x='Fecha', y='Peso', color=color_col,
        markers=True,
        title='',
        labels={'Peso': 'Peso (LBS/KG)', 'Fecha': ''},
        template='plotly_dark'
    )
    fig.update_layout(
        plot_bgcolor='#050014',
        paper_bgcolor='#050014',
        font=dict(family='Inter', color='#E0E0E0'),
        legend=dict(bgcolor='#120024', bordercolor='#FF00FF', borderwidth=1),
        xaxis=dict(gridcolor='#1a0040', type='category'), # type='category' fuerza que se vea por fecha y no por hora
        yaxis=dict(gridcolor='#1a0040'),
        margin=dict(l=20, r=20, t=30, b=20)
    )
    fig.update_traces(line=dict(width=3))
    st.plotly_chart(fig, use_container_width=True)

    # Volumen por sesión
    st.markdown('<div class="section-header">VOLUMEN POR SESIÓN (Peso × Reps)</div>', unsafe_allow_html=True)

    df_vol = df_progreso.copy()
    # 1. Convertir LBS a KG (factor de 0.453592) únicamente para el cálculo de volumen
    df_vol['Peso_KG'] = df_vol.apply(
        lambda x: x['Peso'] * 0.453592 if str(x['Unidad']).upper() == 'LBS' else x['Peso'], axis=1
    )
    df_vol['Volumen'] = df_vol['Peso_KG'] * df_vol['Reps']
    vol_sesion = df_vol.groupby(['Fecha', 'Persona'])['Volumen'].sum().reset_index()

    fig2 = px.bar(
        vol_sesion, x='Fecha', y='Volumen', color='Persona',
        barmode='group',
        template='plotly_dark',
        labels={'Volumen': 'Volumen Total (KG)', 'Fecha': ''},
        color_discrete_sequence=['#00FFFF', '#FF00FF', '#9900FF', '#FF5500', '#00FF88']
    )
    fig2.update_layout(
        plot_bgcolor='#050014',
        paper_bgcolor='#050014',
        font=dict(family='Inter', color='#E0E0E0'),
        legend=dict(bgcolor='#120024', bordercolor='#FF00FF', borderwidth=1),
        xaxis=dict(gridcolor='#1a0040', type='category'),
        yaxis=dict(gridcolor='#1a0040'),
        margin=dict(l=20, r=20, t=30, b=20)
    )
    st.plotly_chart(fig2, use_container_width=True)

with tab_historial:
    st.markdown('<div class="section-header">REGISTRO COMPLETO</div>', unsafe_allow_html=True)
    st.dataframe(
        df[['Fecha', 'Grupo Muscular', 'Persona', 'Ejercicio', 'Serie', 'Peso', 'Reps', 'Unidad']],
        use_container_width=True,
        hide_index=True,
        height=500
    )

with tab_notas:
    st.markdown('<div class="section-header">NOTAS DE ENTRENAMIENTO</div>', unsafe_allow_html=True)
    df_notas = df[df['Nota'].str.len() > 0][['Fecha', 'Persona', 'Ejercicio', 'Nota']]
    if df_notas.empty:
        st.info("No hay notas registradas con los filtros actuales.")
    else:
        for _, row in df_notas.iterrows():
            st.markdown(f"""
            <div class="metric-card" style="text-align: left; margin-bottom: 10px; padding: 15px;">
                <span style="color: #FF00FF; font-weight: bold;">{row['Fecha']}</span> · 
                <span style="color: #00FFFF;">{row['Persona']}</span> · 
                <span style="color: #A0A0C0;">{row['Ejercicio']}</span><br>
                <span style="color: #E0E0E0; font-size: 0.95rem;">💬 {row['Nota']}</span>
            </div>
            """, unsafe_allow_html=True)
