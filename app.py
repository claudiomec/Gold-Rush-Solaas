import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import numpy as np
import json
import time

# Bibliotecas do Firebase (Banco de Dados)
import firebase_admin
from firebase_admin import credentials, firestore

# Tenta importar sklearn
try:
    from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error
except ImportError:
    mean_absolute_percentage_error = None

# ======================================================
# 1. CONFIGURAÇÃO GLOBAL
# ======================================================
st.set_page_config(
    page_title="Gold Rush Analytics",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; }
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    section[data-testid="stSidebar"] { background-color: #1C1E24; }
    section[data-testid="stSidebar"] * { color: #FFFFFF !important; }
    h1, h2, h3 { color: #FFD700 !important; }
    div[data-testid="stMetric"] {
        background-color: #262730;
        border: 1px solid #444;
        border-radius: 6px;
        padding: 10px;
    }
    div[data-testid="stMetricLabel"] { color: #FFD700 !important; font-size: 0.9rem !important; }
    div[data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 1.4rem !important; }
    .stTextInput input, .stSelectbox div[data-baseweb="select"] { 
        background-color: #1C1E24 !important; color: white !important; border: 1px solid #444; 
    }
    div[data-testid="stForm"] { border: 1px solid #FFD700; background-color: #16181E; padding: 20px; border-radius: 10px; }
    div[data-testid="stDataFrame"] { background-color: #1C1E24; }
    .stRadio > label { display: none; }
    
    /* Estilo para mensagens de erro */
    .error-box { background-color: #440000; color: #FFAAAA; padding: 10px; border-radius: 5px; font-size: 0.8em; }
    </style>
    """, unsafe_allow_html=True)

# ======================================================
# 2. GERENCIADOR DE BANCO DE DADOS (COM DIAGNÓSTICO)
# ======================================================

@st.cache_resource
def get_db():
    """Conecta ao Firestore e reporta erros."""
    try:
        # Se já existe app inicializado, retorna o cliente
        if firebase_admin._apps:
            return firestore.client()
            
        # Tenta inicializar
        if "firebase" in st.secrets:
            # Detecta formato
            if "text_key" in st.secrets["firebase"]:
                key_dict = json.loads(st.secrets["firebase"]["text_key"])
            else:
                key_dict = dict(st.secrets["firebase"])
            
            # Correção de quebras de linha
            if "private_key" in key_dict:
                key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")
            
            cred = credentials.Certificate(key_dict)
            firebase_admin.initialize_app(cred)
            
            # Limpa erro anterior se conectar
            if "db_error" in st.session_state:
                del st.session_state["db_error"]
                
            return firestore.client()
        else:
            st.session_state["db_error"] = "Segredo [firebase] não encontrado no TOML."
            return None
            
    except Exception as e:
        # Salva o erro para mostrar na tela
        st.session_state["db_error"] = str(e)
        return None

def authenticate_user(username, password):
    """Verifica usuário no DB ou Backup."""
    db = get_db()
    
    # 1. Tentativa Real (DB)
    if db:
        try:
            users_ref = db.collection('users')
            query = users_ref.where('username', '==', username).where('password', '==', password).stream()
            for doc in query:
                return doc.to_dict()
        except Exception as e:
            print(f"Erro leitura DB: {e}")
    
    # 2. Fallback (Secrets Local)
    if "users" in st.secrets:
        if username in st.secrets["users"] and st.secrets["users"][username]["password"] == password:
            return st.secrets["users"][username]
    return None

def create_user_in_db(username, password, name, role):
    db = get_db()
    if not db: return False, "Banco Offline. Veja detalhes na lateral."
    try:
        db.collection('users').document(username).set({
            'username': username, 'password': password, 'name': name, 'role': role,
            'created_at': firestore.SERVER_TIMESTAMP
        })
        return True, "Usuário criado!"
    except Exception as e: return False, str(e)

def list_users_from_db():
    db = get_db()
    if not db: return []
    try: return [doc.to_dict() for doc in db.collection('users').stream()]
    except: return []

# ======================================================
# 3. SISTEMA DE LOGIN
# ======================================================

def check_password():
    if st.session_state.get("password_correct", False): return True
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br><h1 style='text-align: center;'>🔐 Gold Rush Access</h1>", unsafe_allow_html=True)
        with st.form("login"):
            u = st.text_input("Usuário"); p = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                user_data = authenticate_user(u, p)
                if user_data:
                    st.session_state.update({"password_correct": True, "user_role": user_data.get("role", "client"), "user_name": user_data.get("name", u)})
                    st.rerun()
                else: st.error("Acesso negado.")
    return False

def logout():
    st.session_state["password_correct"] = False
    st.rerun()

# ======================================================
# 4. MÓDULOS E LÓGICA
# ======================================================
@st.cache_data(ttl=3600)
def get_market_data(days_back=180):
    end = datetime.now(); start = end - timedelta(days=days_back)
    wti = yf.download("CL=F", start=start, end=end, progress=False, auto_adjust=True)['Close']
    brl = yf.download("BRL=X", start=start, end=end, progress=False, auto_adjust=True)['Close']
    df = pd.concat([wti, brl], axis=1).dropna(); df.columns = ['WTI', 'USD_BRL']
    df['PP_FOB_USD'] = (df['WTI'] * 0.014) + 0.35
    return df

# Função auxiliar para mostrar status do DB na Sidebar
def show_db_status():
    db = get_db()
    if db:
        st.caption("🟢 Database: Online")
    else:
        st.caption("🔴 Database: Offline")
        if "db_error" in st.session_state:
            with st.expander("Ver Detalhes do Erro"):
                st.markdown(f"<div class='error-box'>{st.session_state['db_error']}</div>", unsafe_allow_html=True)

def run_monitor_module(is_admin=False):
    with st.sidebar:
        if is_admin: st.success(f"Admin: {st.session_state['user_name']}")
        else: st.info(f"Cliente: {st.session_state['user_name']}")
        show_db_status() # Mostra status aqui
        
        st.header("⚙️ Parâmetros")
        ocean = st.slider("Frete Marítimo", 0, 300, 60, 10)
        icms = st.selectbox("ICMS", [18, 12, 7, 4])
        freight = st.slider("Frete Interno", 0.0, 0.5, 0.15, 0.01)
        margin = st.slider("Margem", 0, 20, 10)
        st.markdown("---"); st.button("Sair", on_click=logout)

    st.title("Monitor de Custo Industrial: Polipropileno")
    with st.spinner('Calculando...'):
        df = get_market_data()
        df['CFR'] = df['PP_FOB_USD'] + (ocean/1000)
        df['Landed'] = df['CFR'] * df['USD_BRL'] * 1.12
        df['Final'] = (df['Landed'] + freight) * (1 + margin/100) / (1 - icms/100)
        df['Trend'] = df['Final'].rolling(7).mean()
        
        curr = df['Final'].iloc[-1]; var = (curr/df['Final'].iloc[-7]-1)*100
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Preço Final", f"R$ {curr:.2f}", f"{curr-df['Final'].iloc[-2]:.2f}")
        c2.metric("Tendência", f"{var:.2f}%", delta_color="inverse")
        c3.metric("Frete Marítimo", f"USD {ocean}"); c4.metric("Dólar", f"R$ {df['USD_BRL'].iloc[-1]:.4f}")
        
        fig, ax = plt.subplots(figsize=(10, 3)); fig.patch.set_facecolor('#0E1117'); ax.set_facecolor('#0E1117')
        ax.plot(df.index, df['Final'], color='#666', alpha=0.3); ax.plot(df.index, df['Trend'], color='#FFD700', lw=2.5)
        ax.tick_params(colors='#AAA'); [s.set_color('#333') for s in ax.spines.values()]
        st.pyplot(fig, use_container_width=True)

def run_backtest_module():
    with st.sidebar:
        st.header("🧪 Lab"); show_db_status()
        wti = st.number_input("Coef WTI", value=0.014, format="%.4f")
        spr = st.number_input("Spread", value=0.35)
        mkp = st.number_input("Markup", value=1.45)
        yr = st.slider("Anos", 1, 5, 3)
        st.markdown("---"); st.button("Sair", key='bk', on_click=logout)
    
    st.title("🧪 Laboratório de Backtest")
    df = get_market_data(yr*365)
    df['Teorico'] = ((df['WTI']*wti)+spr)*df['USD_BRL']*mkp
    c1, c2 = st.columns([2, 1])
    with c1:
        fig, ax = plt.subplots(figsize=(10, 4)); fig.patch.set_facecolor('#0E1117'); ax.set_facecolor('#0E1117')
        ax.plot(df.index, df['Teorico'], color='#FFD700'); ax.tick_params(colors='#AAA', rotation=45)
        st.pyplot(fig, use_container_width=True)
    with c2:
        up = st.file_uploader("CSV", type="csv")
        if up and mean_absolute_percentage_error:
            try:
                rdf = pd.read_csv(up); rdf['Data'] = pd.to_datetime(rdf['Data']); rdf = rdf.set_index('Data').sort_index()
                comp = df.join(rdf, how='inner').dropna()
                if not comp.empty:
                    mape = mean_absolute_percentage_error(comp['Preco'], comp['Teorico'])
                    st.metric("Erro MAPE", f"{mape*100:.1f}%")
            except: st.error("Erro CSV")

def run_user_management_module():
    with st.sidebar:
        st.header("👥 Usuários"); show_db_status()
        st.markdown("---"); st.button("Sair", key='usr', on_click=logout)

    st.title("👥 Controle de Acessos")
    with st.form("new"):
        c1, c2 = st.columns(2)
        u = c1.text_input("Login"); p = c1.text_input("Senha", type="password")
        n = c2.text_input("Nome"); r = c2.selectbox("Perfil", ["client", "admin"])
        if st.form_submit_button("Criar", use_container_width=True):
            ok, msg = create_user_in_db(u, p, n, r)
            if ok: st.success(msg)
            else: st.error(msg)
            
    if st.button("🔄 Listar"):
        users = list_users_from_db()
        if users: st.dataframe(pd.DataFrame(users)[['username', 'name', 'role']], use_container_width=True)

if check_password():
    if st.session_state["user_role"] == "admin":
        pg = st.sidebar.radio("Menu", ["Monitor", "Backtest", "Usuários"])
        if pg == "Monitor": run_monitor_module(True)
        elif pg == "Backtest": run_backtest_module()
        elif pg == "Usuários": run_user_management_module()
    else: run_monitor_module(False)
