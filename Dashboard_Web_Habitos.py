import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
import plotly.express as px
import os
import json

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="J.A.R.V.I.S. Core",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS GLASSMORPHISM (Celeste y Morado Claro) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;600;700&display=swap');

    /* Fondo principal */
    .stApp {
        background: linear-gradient(135deg, #e0f2fe 0%, #ede9fe 50%, #f3e8ff 100%);
        color: #1e1e2f;
        font-family: 'Inter', sans-serif;
    }

    /* Glassmorphism containers */
    .glass-panel {
        background: rgba(255, 255, 255, 0.45);
        border-radius: 16px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.05);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.6);
        padding: 25px;
        margin-bottom: 25px;
    }

    /* Títulos */
    .main-title {
        font-family: 'Orbitron', monospace;
        font-size: 2.8rem;
        font-weight: 900;
        text-align: center;
        background: linear-gradient(90deg, #3b82f6, #8b5cf6, #d946ef);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding: 20px 0 5px 0;
        letter-spacing: 2px;
    }
    
    .section-title {
        font-family: 'Orbitron', monospace;
        color: #6d28d9;
        font-size: 1.5rem;
        border-bottom: 2px solid rgba(139, 92, 246, 0.3);
        padding-bottom: 10px;
        margin-bottom: 20px;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(255, 255, 255, 0.3);
        padding: 10px;
        border-radius: 12px;
        backdrop-filter: blur(10px);
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: #4c1d95;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 600;
        border: 1px solid transparent;
        transition: all 0.3s ease;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(255, 255, 255, 0.8);
        color: #7c3aed;
        border: 1px solid rgba(139, 92, 246, 0.4);
        box-shadow: 0 4px 15px rgba(139, 92, 246, 0.15);
    }

    /* Tablas / Dataframes */
    .stDataFrame {
        background: rgba(255, 255, 255, 0.6);
        border-radius: 12px;
        padding: 10px;
        border: 1px solid rgba(255, 255, 255, 0.8);
    }

    /* Botones */
    .stButton > button {
        background: linear-gradient(90deg, #8b5cf6, #d946ef);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: bold;
        padding: 8px 24px;
        box-shadow: 0 4px 15px rgba(139, 92, 246, 0.3);
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background: linear-gradient(90deg, #7c3aed, #c026d3);
        box-shadow: 0 6px 20px rgba(139, 92, 246, 0.5);
        transform: translateY(-2px);
    }

</style>
""", unsafe_allow_html=True)

# --- CONFIGURACIÓN DE FIREBASE ---
@st.cache_resource
def get_firebase_db():
    if not firebase_admin._apps:
        # Intentar leer desde Streamlit Secrets primero
        if "firebase" in st.secrets:
            cred_dict = dict(st.secrets["firebase"])
            cred = credentials.Certificate(cred_dict)
        else:
            # Fallback a local
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            ruta = os.path.join(BASE_DIR, "credenciales.json")
            if os.path.exists(ruta):
                cred = credentials.Certificate(ruta)
            else:
                st.error("No se encontraron credenciales de Firebase. Configura st.secrets o crea credenciales.json.")
                st.stop()
        
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = get_firebase_db()

# --- FUNCIONES AUXILIARES ---
def to_emoji(val):
    if val is True or str(val).lower() in ['true', 'sí', 'si', 'v']: return '✅'
    elif val is False or str(val).lower() in ['false', 'no', 'f']: return '❌'
    return val

def from_emoji(val):
    if val == '✅': return True
    elif val == '❌': return False
    return val

MAPEO_HABITOS = {
    "Gym": "gym",
    "A tiempo": "desperte_a_tiempo",
    "Sueño": "dormi_8_horas",
    "Correr (km/min)": "correr",
    "Estudio (h)": "horas_estudio",
    "Redes (h)": "horas_redes"
}

# --- CARGA DE DATOS ---
def cargar_datos():
    docs = db.collection('habitos').stream()
    registros = sorted([{"id": d.id, **d.to_dict()} for d in docs], key=lambda x: x['id'])
    
    # 1. Hábitos
    filas_habitos = []
    for data in registros:
        if 'habitos' in data and data['habitos']:
            hab = data['habitos']
            filas_habitos.append({
                "Fecha": data['id'],
                "Gym": to_emoji(hab.get('gym', '')),
                "A tiempo": to_emoji(hab.get('desperte_a_tiempo', '')),
                "Sueño": to_emoji(hab.get('dormi_8_horas', '')),
                "Correr (km/min)": str(hab.get('correr', '0')),
                "Estudio (h)": float(hab.get('horas_estudio', 0)),
                "Redes (h)": float(hab.get('horas_redes', 0))
            })
    df_habitos = pd.DataFrame(filas_habitos) if filas_habitos else pd.DataFrame(columns=["Fecha"] + list(MAPEO_HABITOS.keys()))
    
    # Tomar solo los últimos 7 para la gráfica
    if not df_habitos.empty:
        df_habitos_grafica = df_habitos.tail(7)
    else:
        df_habitos_grafica = pd.DataFrame()

    # 2. Tareas
    filas_tareas = []
    for data in registros:
        for t in data.get('tareas', []):
            filas_tareas.append({
                "Doc_Fecha": data['id'],
                "Prioridad": t.get('prioridad', '-'),
                "Límite": t.get('fecha_limite', '2099-12-31'),
                "Descripción": t.get('descripcion', 'N/A')
            })
    df_tareas = pd.DataFrame(filas_tareas) if filas_tareas else pd.DataFrame(columns=["Doc_Fecha", "Prioridad", "Límite", "Descripción"])

    # 3. Notas
    filas_notas = []
    for data in registros:
        for n in data.get('notas', []):
            filas_notas.append({
                "Tipo": "Diaria",
                "Referencia": data['id'],
                "Título": n.get('titulo', 'Sin título'),
                "Contenido": n.get('contenido', '')
            })
            
    # Notas independientes
    for nota_doc in db.collection('notas').stream():
        n = nota_doc.to_dict()
        filas_notas.append({
            "Tipo": "Independiente",
            "Referencia": nota_doc.id,
            "Título": n.get('titulo', 'Sin título'),
            "Contenido": n.get('contenido', '')
        })
    df_notas = pd.DataFrame(filas_notas) if filas_notas else pd.DataFrame(columns=["Tipo", "Referencia", "Título", "Contenido"])

    return df_habitos, df_habitos_grafica, df_tareas, df_notas

# --- GUARDADO EN FIREBASE DESDE DATA_EDITOR ---
def guardar_habitos():
    if "editor_habitos" in st.session_state:
        cambios = st.session_state["editor_habitos"].get("edited_rows", {})
        df = st.session_state["df_habitos_state"]
        for row_idx, edits in cambios.items():
            fecha = df.iloc[row_idx]["Fecha"]
            for col, val in edits.items():
                if col in MAPEO_HABITOS:
                    fb_key = MAPEO_HABITOS[col]
                    real_val = from_emoji(val)
                    try:
                        real_val = float(real_val) if col in ["Estudio (h)", "Redes (h)"] else real_val
                    except:
                        pass
                    db.collection('habitos').document(fecha).set({"habitos": {fb_key: real_val}}, merge=True)
        st.cache_data.clear()

def guardar_tareas():
    # En lugar de detectar fila por fila, tomamos el df final editado,
    # lo agrupamos por fecha y reescribimos el array de tareas en Firestore.
    df = st.session_state["editor_tareas"]
    # Limpiar tareas que el usuario borró (eliminadas en UI usando data_editor)
    agrupado = df.groupby("Doc_Fecha")
    
    # Primero, leemos todos los docs actuales para resetear los arrays de tareas
    # a los valores del dataframe editado. (Para no borrar hábitos, solo pisamos 'tareas')
    for fecha, group in agrupado:
        nuevas_tareas = []
        for _, row in group.iterrows():
            nuevas_tareas.append({
                "prioridad": str(row["Prioridad"]),
                "fecha_limite": str(row["Límite"]),
                "descripcion": str(row["Descripción"])
            })
        db.collection('habitos').document(fecha).update({"tareas": nuevas_tareas})
        
    # Si se borraron todas las tareas de una fecha, el groupby no la tendrá.
    # Necesitamos detectar cuáles fechas perdieron tareas si las eliminaron por completo.
    df_old = st.session_state["df_tareas_state"]
    fechas_old = set(df_old["Doc_Fecha"].unique())
    fechas_new = set(df["Doc_Fecha"].unique())
    fechas_borradas = fechas_old - fechas_new
    for f in fechas_borradas:
        db.collection('habitos').document(f).update({"tareas": []})
        
    st.cache_data.clear()
    st.rerun()

def guardar_notas():
    df = st.session_state["editor_notas"]
    
    # 1. Notas Diarias (Arrays en la colección 'habitos')
    df_diarias = df[df["Tipo"] == "Diaria"]
    agrupado = df_diarias.groupby("Referencia")
    for fecha, group in agrupado:
        nuevas_notas = []
        for _, row in group.iterrows():
            nuevas_notas.append({
                "titulo": str(row["Título"]),
                "contenido": str(row["Contenido"])
            })
        db.collection('habitos').document(fecha).update({"notas": nuevas_notas})
        
    df_old = st.session_state["df_notas_state"]
    fechas_old = set(df_old[df_old["Tipo"] == "Diaria"]["Referencia"].unique())
    fechas_new = set(df_diarias["Referencia"].unique())
    for f in fechas_old - fechas_new:
        db.collection('habitos').document(f).update({"notas": []})
        
    # 2. Notas Independientes (Colección 'notas')
    df_indep = df[df["Tipo"] == "Independiente"]
    for _, row in df_indep.iterrows():
        doc_id = str(row["Referencia"])
        db.collection('notas').document(doc_id).set({
            "titulo": str(row["Título"]),
            "contenido": str(row["Contenido"])
        })
        
    # Manejar borrados de notas independientes
    ids_old = set(df_old[df_old["Tipo"] == "Independiente"]["Referencia"])
    ids_new = set(df_indep["Referencia"])
    for doc_id in ids_old - ids_new:
        db.collection('notas').document(doc_id).delete()
        
    st.cache_data.clear()
    st.rerun()

# --- HEADER ---
st.markdown('<div class="main-title">💠 J.A.R.V.I.S. SYSTEM CORE</div>', unsafe_allow_html=True)
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("⟳ Sincronizar Datos Completos", use_container_width=True):
        st.rerun()

# Cargar datos
df_habitos, df_habitos_grafica, df_tareas, df_notas = cargar_datos()

# Guardamos el estado original para comparar
if "df_habitos_state" not in st.session_state or not df_habitos.equals(st.session_state.get("df_habitos_state")):
    st.session_state["df_habitos_state"] = df_habitos.copy()
if "df_tareas_state" not in st.session_state or not df_tareas.equals(st.session_state.get("df_tareas_state")):
    st.session_state["df_tareas_state"] = df_tareas.copy()
if "df_notas_state" not in st.session_state or not df_notas.equals(st.session_state.get("df_notas_state")):
    st.session_state["df_notas_state"] = df_notas.copy()


# --- PESTAÑAS ---
tab1, tab2, tab3 = st.tabs(["📊 Rendimiento & Hábitos", "✅ Tareas Activas", "📝 Archivo de Notas"])

# TABS 1: HÁBITOS
with tab1:
    col_izq, col_der = st.columns([1.2, 1])
    
    with col_izq:
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Registro Histórico</div>', unsafe_allow_html=True)
        st.markdown("Cualquier cambio se guarda automáticamente. Usa `✅`, `❌` o texto para las celdas de confirmación.")
        
        st.data_editor(
            st.session_state["df_habitos_state"], 
            key="editor_habitos",
            hide_index=True,
            use_container_width=True,
            on_change=guardar_habitos,
            disabled=["Fecha"] # No permitimos editar la fecha que sirve de ID
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_der:
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Métricas de Productividad</div>', unsafe_allow_html=True)
        if not df_habitos_grafica.empty:
            # Gráfico de barras combinadas
            fig = px.bar(
                df_habitos_grafica, 
                x="Fecha", 
                y=["Estudio (h)", "Redes (h)"], 
                barmode='group',
                color_discrete_sequence=['#3b82f6', '#d946ef']
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family='Inter', color='#4c1d95'),
                legend=dict(title="", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=20, r=20, t=30, b=20)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin datos para graficar.")
        st.markdown('</div>', unsafe_allow_html=True)


# TABS 2: TAREAS
with tab2:
    st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Línea de Tiempo - Tareas Urgentes</div>', unsafe_allow_html=True)
    
    # Procesar timeline
    hoy = datetime.now()
    tareas_timeline = []
    for _, row in df_tareas.iterrows():
        try: dt_limite = datetime.strptime(row["Límite"], '%Y-%m-%d')
        except: dt_limite = datetime(2099, 12, 31)
        tareas_timeline.append({"dt": dt_limite, "limite_str": row["Límite"], "desc": row["Descripción"]})
        
    tareas_timeline.sort(key=lambda x: x['dt'])
    
    html_cards = "<div style='display: flex; overflow-x: auto; padding: 10px; gap: 15px;'>"
    for t in tareas_timeline:
        if t['dt'].year == 2099:
            color, bg = "#4c1d95", "rgba(139, 92, 246, 0.2)" # Morado
        else:
            dias = (t['dt'] - hoy).days
            if dias < 0:
                color, bg = "#ef4444", "rgba(239, 68, 68, 0.2)" # Rojo
            elif dias <= 2:
                color, bg = "#f43f5e", "rgba(244, 63, 94, 0.2)" # Rosado
            elif dias <= 5:
                color, bg = "#f59e0b", "rgba(245, 158, 11, 0.2)" # Naranja
            elif dias <= 7:
                color, bg = "#06b6d4", "rgba(6, 182, 212, 0.2)" # Cyan
            else:
                color, bg = "#10b981", "rgba(16, 185, 129, 0.2)" # Verde
                
        html_cards += f"""
        <div style='background: {bg}; border: 1px solid {color}; border-radius: 12px; padding: 15px; min-width: 220px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);'>
            <h4 style='color: {color}; margin: 0 0 5px 0; font-family: "Inter"; font-size: 14px; font-weight: bold;'>{t["desc"]}</h4>
            <p style='color: #4c1d95; margin: 0; font-size: 12px;'>📅 {t["limite_str"]}</p>
        </div>
        """
    html_cards += "</div>"
    st.markdown(html_cards, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Protocolos Pendientes (Edición)</div>', unsafe_allow_html=True)
    st.markdown("Edita las celdas directamente. Selecciona filas y bórralas presionando `Suprimir` o la papelera. Haz clic en 'Guardar Cambios' al terminar.")
    
    st.data_editor(
        st.session_state["df_tareas_state"],
        key="editor_tareas",
        hide_index=True,
        num_rows="dynamic",
        use_container_width=True,
        disabled=["Doc_Fecha"]
    )
    if st.button("💾 Guardar Cambios de Tareas"):
        guardar_tareas()
    st.markdown('</div>', unsafe_allow_html=True)


# TABS 3: NOTAS
with tab3:
    st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Base de Datos Textual</div>', unsafe_allow_html=True)
    st.markdown("Edita los títulos y contenidos directamente. Puedes añadir o borrar filas. Haz clic en 'Guardar Cambios' al terminar.")
    
    st.data_editor(
        st.session_state["df_notas_state"],
        key="editor_notas",
        hide_index=True,
        num_rows="dynamic",
        use_container_width=True,
        disabled=["Tipo", "Referencia"],
        column_config={
            "Contenido": st.column_config.TextColumn("Contenido", width="large")
        }
    )
    if st.button("💾 Guardar Cambios de Notas"):
        guardar_notas()
    st.markdown('</div>', unsafe_allow_html=True)
