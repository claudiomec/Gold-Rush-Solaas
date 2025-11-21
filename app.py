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
    </style>
    """, unsafe_allow_html=True)

# ======================================================
# 2. GERENCIADOR DE BANCO DE DADOS (FIRESTORE)
# ======================================================

@st.cache_resource
def get_db():
    """Conecta ao Firestore com tratamento de erro robusto."""
    try:
        if not firebase_admin._apps:
            if "firebase" in st.secrets:
                # Detecta formato (TOML Dict ou JSON String)
                if "text_key" in st.secrets["firebase"]:
                    key_dict = json.loads(st.secrets["firebase"]["text_key"])
                else:
                    key_dict = dict(st.secrets["firebase"])
                
                # --- VACINA CONTRA ERRO DE FORMATAÇÃO ---
                # Corrige as quebras de linha (\n) que costumam quebrar a conexão
                if "private_key" in key_dict:
                    key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")
                
                cred = credentials.Certificate(key_dict)
                firebase_admin.initialize_app(cred)
                return firestore.client()
        else:
            return firestore.client()
    except Exception as e:
        # Imprime o erro no console do servidor para debug
        print(f"CRITICAL DB ERROR: {e}")
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
    """Cria usuário no Firestore."""
    db = get_db()
    if not db:
        return False, "❌ Erro Crítico: Banco de Dados Desconectado. Verifique os Segredos."
    
    try:
        doc_ref = db.collection('users').document(username)
        doc_ref.set({
            'username': username,
            'password': password,
            'name': name,
            'role': role,
            'created_at': firestore.SERVER_TIMESTAMP
        })
        return True, "✅ Usuário criado com sucesso!"
    except Exception as e:
        return False, f"Erro ao gravar: {str(e)}"

def list_users_from_db():
    """Lista usuários."""
    db = get_db()
    if not db: return []
    try:
        return [doc.to_dict() for doc in db.collection('users').stream()]
    except: return []

# ======================================================
# 3. SISTEMA DE LOGIN
# ======================================================

def check_password():
    if st.session_state.get("password_correct", False):
        return True

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br><h1 style='text-align: center;'>🔐 Gold Rush Access</h1>", unsafe_allow_html=True)
        with st.form("login_form"):
            user = st.text_input("Usuário")
            password = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Entrar", use_container_width=True)
            if submitted:
                user_data = authenticate_user(user, password)
                if user_data:
                    st.session_state["password_correct"] = True
                    st.session_state["user_role"] = user_data.get("role", "client")
                    st.session_state["user_name"] = user_data.get("name", user)
                    st.rerun()
                else:
                    st.error("Acesso negado.")
    return False

def logout():
    st.session_state["password_correct"] = False
    st.session_state["user_role"] = None
    st.rerun()

# ======================================================
# 4. MÓDULOS E LÓGICA
# ======================================================
@st.cache_data(ttl=3600)
def get_market_data(days_back=180):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    wti = yf.download("CL=F", start=start_date, end=end_date, progress=False, auto_adjust=True)['Close']
    brl = yf.download("BRL=X", start=start_date, end=end_date, progress=False, auto_adjust=True)['Close']
    df = pd.concat([wti, brl], axis=1).dropna()
    df.columns = ['WTI', 'USD_BRL']
    df['PP_FOB_USD'] = (df['WTI'] * 0.014) + 0.35
    return df

def run_monitor_module(is_admin=False):
    with st.sidebar:
        if is_admin: st.success(f"Admin: {st.session_state['user_name']}")
        else: st.info(f"Cliente: {st.session_state['user_name']}")
        
        # Indicador de Status do Banco
        if get_db(): st.caption("🟢 Database: Online")
        else: st.caption("🔴 Database: Offline (Modo Backup)")
        
        st.header("⚙️ Parâmetros")
        ocean_freight = st.slider("Frete Marítimo (USD/ton)", 0, 300, 60, step=10)
        icms_user = st.selectbox("ICMS Destino (%)", [18, 12, 7, 4], index=0)
        freight_user = st.slider("Frete Interno (R$/kg)", 0.00, 0.50, 0.15, step=0.01)
        margin_user = st.slider("Margem (%)", 0, 20, 10)
        st.markdown("---")
        if st.button("Sair"): logout()

    st.title("Monitor de Custo Industrial: Polipropileno")
    with st.spinner('Calculando...'):
        df = get_market_data(days_back=180)
        df['CFR_USD'] = df['PP_FOB_USD'] + (ocean_freight / 1000)
        df['Landed_BRL'] = df['CFR_USD'] * df['USD_BRL'] * 1.12
        df['Operational_Cost'] = df['Landed_BRL'] + freight_user
        df['Price_Net'] = df['Operational_Cost'] * (1 + (margin_user/100))
        df['PP_Price'] = df['Price_Net'] / (1 - (icms_user/100))
        df['Trend'] = df['PP_Price'].rolling(window=7).mean()
        
        current_price, variation_pct = df['PP_Price'].iloc[-1], (df['PP_Price'].iloc[-1]/df['PP_Price'].iloc[-7]-1)*100
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Preço Final", f"R$ {current_price:.2f}", f"{current_price-df['PP_Price'].iloc[-2]:.2f}")
        c2.metric("Tendência (7d)", f"{variation_pct:.2f}%", delta_color="inverse")
        c3.metric("Frete Marítimo", f"USD {ocean_freight}")
        c4.metric("Dólar", f"R$ {df['USD_BRL'].iloc[-1]:.4f}")

        fig, ax = plt.subplots(figsize=(10, 3))
        fig.patch.set_facecolor('#0E1117'); ax.set_facecolor('#0E1117')
        ax.plot(df.index, df['PP_Price'], color='#666', alpha=0.3)
        ax.plot(df.index, df['Trend'], color='#FFD700', linewidth=2.5)
        ax.tick_params(axis='both', colors='#AAA', labelsize=8)
        for s in ax.spines.values(): s.set_color('#333')
        st.pyplot(fig, use_container_width=True)

        if variation_pct > 0.5: msg, cor = "⚠️ <b>ALTA:</b> Pressão de custos.", "#FF4B4B"
        elif variation_pct < -0.5: msg, cor = "✅ <b>BAIXA:</b> Oportunidade.", "#00CC96"
        else: msg, cor = "⚖️ <b>ESTÁVEL:</b> Mercado lateral.", "#FFAA00"
        st.markdown(f"<div style='background-color:#1C1E24;padding:10px;border-left:4px solid {cor};color:#DDD;font-size:0.9rem'>{msg}</div>", unsafe_allow_html=True)

def run_backtest_module():
    with st.sidebar:
        st.header("🧪 Lab")
        coef_wti = st.number_input("Coef. WTI", value=0.014, format="%.4f")
        coef_spread = st.number_input("Spread ($)", value=0.35)
        coef_markup = st.number_input("Markup", value=1.45)
        years_back = st.slider("Anos", 1, 5, 3)
        st.markdown("---")
        if st.button("Sair", key='bklout'): logout()

    st.title("🧪 Backtest Lab")
    df = get_market_data(days_back=years_back*365)
    df['PP_Theoretical'] = ((df['WTI'] * coef_wti) + coef_spread) * df['USD_BRL'] * coef_markup
    
    c1, c2 = st.columns([2, 1])
    with c1:
        fig, ax = plt.subplots(figsize=(10, 4))
        fig.patch.set_facecolor('#0E1117'); ax.set_facecolor('#0E1117')
        ax.plot(df.index, df['PP_Theoretical'], color='#FFD700')
        ax.tick_params(axis='both', colors='#AAA', rotation=45)
        st.pyplot(fig, use_container_width=True)
    with c2:
        up = st.file_uploader("Upload CSV", type="csv")
        if up and mean_absolute_percentage_error:
            try:
                rdf = pd.read_csv(up); rdf['Data'] = pd.to_datetime(rdf['Data']); rdf = rdf.set_index('Data').sort_index()
                comp = df.join(rdf, how='inner').dropna()
                if not comp.empty:
                    mape = mean_absolute_percentage_error(comp['Preco'], comp['PP_Theoretical'])
                    st.metric("Erro (MAPE)", f"{mape*100:.1f}%")
                else: st.warning("Sem match.")
            except: st.error("Erro CSV")

def run_user_management_module():
    with st.sidebar:
        st.header("👥 Usuários")
        
        # Indicador Visual de Status
        if get_db():
            st.caption("🟢 Sistema Online")
        else:
            st.error("🔴 Sistema Offline")
            st.caption("Verifique os Segredos do Firebase.")
            
        st.markdown("---")
        if st.button("Sair", key='usrlout'): logout()

    st.title("👥 Controle de Acessos")
    
    with st.form("new_user"):
        c1, c2 = st.columns(2)
        u = c1.text_input("Login"); p = c1.text_input("Senha", type="password")
        n = c2.text_input("Nome"); r = c2.selectbox("Perfil", ["client", "admin"])
        if st.form_submit_button("Criar", use_container_width=True):
            if u and p and n:
                ok, msg = create_user_in_db(u, p, n, r)
                if ok: st.success(msg)
                else: st.error(msg)
            else: st.warning("Preencha tudo.")
    
    st.markdown("---")
    if st.button("🔄 Atualizar Lista"):
        users = list_users_from_db()
        if users: st.dataframe(pd.DataFrame(users)[['username', 'name', 'role']], use_container_width=True)
        else: st.info("Nenhum usuário ou erro de conexão.")

if check_password():
    role = st.session_state["user_role"]
    if role == "admin":
        page = st.sidebar.radio("Menu", ["Monitor", "Backtest", "Usuários"])
        if page == "Monitor": run_monitor_module(is_admin=True)
        elif page == "Backtest": run_backtest_module()
        elif page == "Usuários": run_user_management_module()
    elif role == "client":
        run_monitor_module(is_admin=False)
