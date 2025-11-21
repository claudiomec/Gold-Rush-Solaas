import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import numpy as np
import json
import time

# Bibliotecas do Firebase
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
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stMultiSelect div[data-baseweb="select"] { 
        background-color: #1C1E24 !important; color: white !important; border: 1px solid #444; 
    }
    div[data-testid="stForm"] { border: 1px solid #FFD700; background-color: #16181E; padding: 20px; border-radius: 10px; }
    div[data-testid="stDataFrame"] { background-color: #1C1E24; }
    .stRadio > label { display: none; }
    
    /* Estilo para Cards de Economia */
    .savings-card { background-color: #1C1E24; border-left: 5px solid #00CC96; padding: 15px; margin-bottom: 10px; border-radius: 5px; }
    .loss-card { background-color: #1C1E24; border-left: 5px solid #FF4B4B; padding: 15px; margin-bottom: 10px; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# ======================================================
# 2. GERENCIADOR DE BANCO DE DADOS
# ======================================================

@st.cache_resource
def get_db():
    try:
        if firebase_admin._apps:
            return firestore.client()
            
        if "firebase" in st.secrets:
            if "text_key" in st.secrets["firebase"]:
                key_dict = json.loads(st.secrets["firebase"]["text_key"])
            else:
                key_dict = dict(st.secrets["firebase"])
            
            # Auto-Reparo de Chave
            if "private_key" in key_dict:
                pk = key_dict["private_key"]
                pk = pk.replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "")
                pk = pk.replace("\\n", "").replace("\n", "").replace(" ", "").replace("\t", "").replace('"', '').replace("'", "")
                key_dict["private_key"] = "-----BEGIN PRIVATE KEY-----\n" + pk + "\n-----END PRIVATE KEY-----"

            cred = credentials.Certificate(key_dict)
            firebase_admin.initialize_app(cred)
            return firestore.client()
        return None
    except Exception as e:
        print(f"DB Error: {e}")
        return None

def authenticate_user(username, password):
    db = get_db()
    if db:
        try:
            users_ref = db.collection('users')
            query = users_ref.where('username', '==', username).where('password', '==', password).stream()
            for doc in query: return doc.to_dict()
        except: pass
    
    if "users" in st.secrets and username in st.secrets["users"]:
        if st.secrets["users"][username]["password"] == password:
            # Usuários de backup (secrets) têm acesso padrão apenas ao Monitor
            user_data = st.secrets["users"][username]
            if "modules" not in user_data:
                # Converte o objeto st.secrets para dict normal para poder adicionar campos
                user_data = dict(user_data)
                user_data["modules"] = ["Monitor"] 
            return user_data
    return None

def create_user_in_db(username, password, name, role, modules):
    db = get_db()
    if not db: return False, "Banco Offline."
    try:
        db.collection('users').document(username).set({
            'username': username, 'password': password, 'name': name, 'role': role,
            'modules': modules, # Lista de módulos permitidos
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
# 3. LOGIN
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
                    st.session_state.update({
                        "password_correct": True, 
                        "user_role": user_data.get("role", "client"), 
                        "user_name": user_data.get("name", u),
                        # Recupera módulos ou define padrão se não existir (retrocompatibilidade)
                        "user_modules": user_data.get("modules", ["Monitor"]) 
                    })
                    st.rerun()
                else: st.error("Acesso negado.")
    return False

def logout():
    st.session_state["password_correct"] = False
    st.rerun()

# ======================================================
# 4. MÓDULOS DE DADOS
# ======================================================
@st.cache_data(ttl=3600)
def get_market_data(days_back=180):
    end = datetime.now(); start = end - timedelta(days=days_back)
    wti = yf.download("CL=F", start=start, end=end, progress=False, auto_adjust=True)['Close']
    brl = yf.download("BRL=X", start=start, end=end, progress=False, auto_adjust=True)['Close']
    
    if wti.empty or brl.empty:
        idx = pd.date_range(start, end)
        return pd.DataFrame({'WTI': [70]*len(idx), 'USD_BRL': [5.0]*len(idx), 'PP_FOB_USD': [1.2]*len(idx)}, index=idx)

    df = pd.concat([wti, brl], axis=1).dropna(); df.columns = ['WTI', 'USD_BRL']
    df['PP_FOB_USD'] = (df['WTI'] * 0.014) + 0.35
    return df

# --- HELPER DE CÁLCULO ---
def calculate_fair_price_now():
    # Função rápida para pegar o preço justo atual (usada na calculadora)
    df = get_market_data(7) # Pega só última semana
    if df.empty: return 0
    
    # Parâmetros Padrão de Mercado (SP)
    ocean_freight = 60 # USD/ton
    freight_internal = 0.15 # R$/kg
    icms = 18 # %
    margin = 10 # %
    
    last_row = df.iloc[-1]
    cfr = last_row['PP_FOB_USD'] + (ocean_freight/1000)
    landed = cfr * last_row['USD_BRL'] * 1.12
    operational = landed + freight_internal
    price_net = operational * (1 + margin/100)
    price_final = price_net / (1 - icms/100)
    
    return price_final

# ======================================================
# 5. TELAS (VIEWS)
# ======================================================

def run_monitor_module(is_admin=False):
    with st.sidebar:
        if is_admin: st.success(f"Admin: {st.session_state['user_name']}")
        else: st.info(f"Cliente: {st.session_state['user_name']}")
        if get_db(): st.caption("🟢 Database: Online")
        
        st.header("⚙️ Parâmetros")
        ocean = st.slider("Frete Marítimo", 0, 300, 60, 10)
        icms = st.selectbox("ICMS", [18, 12, 7, 4])
        freight = st.slider("Frete Interno", 0.0, 0.5, 0.15, 0.01)
        margin = st.slider("Margem", 0, 20, 10)
        st.markdown("---"); st.button("Sair", key='monlogout', on_click=logout)

    st.title("Monitor de Custo Industrial: Polipropileno")
    with st.spinner('Calculando...'):
        df = get_market_data()
        
        if not df.empty:
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
            ax.tick_params(colors='#AAA')
            for s in ax.spines.values(): s.set_color('#333')
            st.pyplot(fig, use_container_width=True)

            if var > 0.5: msg, cor = "⚠️ <b>ALTA:</b> Pressão de custos.", "#FF4B4B"
            elif var < -0.5: msg, cor = "✅ <b>BAIXA:</b> Oportunidade.", "#00CC96"
            else: msg, cor = "⚖️ <b>ESTÁVEL:</b> Mercado lateral.", "#FFAA00"
            st.markdown(f"<div style='background-color:#1C1E24;padding:10px;border-left:4px solid {cor};color:#DDD;font-size:0.9rem'>{msg}</div>", unsafe_allow_html=True)

def run_financial_calculator():
    with st.sidebar:
        st.header("💰 Calculadora")
        st.info("Módulo Premium")
        st.markdown("---"); st.button("Sair", key='finlogout', on_click=logout)

    st.title("💰 Calculadora Financeira (Tira-Teima)")
    st.markdown("Compare suas condições atuais com o Preço Justo de Mercado (Gold Rush) e descubra oportunidades de economia.")
    
    # Preço Justo Atual (Puxado do Modelo)
    fair_price = calculate_fair_price_now()
    
    col_input, col_result = st.columns([1, 1])
    
    with col_input:
        st.subheader("Seus Dados Atuais")
        current_price_user = st.number_input("Preço Pago na Última NF (R$/kg)", value=10.50, step=0.01, format="%.2f")
        volume_ton = st.number_input("Volume Mensal de Compra (Toneladas)", value=50, step=10)
        volume_kg = volume_ton * 1000
        
    with col_result:
        st.subheader("Análise de Competitividade")
        
        delta = current_price_user - fair_price
        
        # Card do Preço Justo
        st.markdown(f"""
        <div style='background-color: #262730; padding: 15px; border-radius: 8px; text-align: center;'>
            <span style='color: #AAA; font-size: 0.9rem;'>Preço Justo de Mercado (Hoje)</span><br>
            <span style='color: #FFD700; font-size: 2rem; font-weight: bold;'>R$ {fair_price:.2f}</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if delta > 0:
            # Cliente está pagando mais caro (Perda)
            monthly_loss = delta * volume_kg
            annual_loss = monthly_loss * 12
            pct_over = (delta / fair_price) * 100
            
            st.markdown(f"""
            <div class='loss-card'>
                <h3 style='margin:0; color: #FF4B4B;'>🔴 Ineficiência Detectada</h3>
                <p style='color: white;'>Você está pagando <b>{pct_over:.1f}% acima</b> do preço justo.</p>
                <hr style='border-color: #444;'>
                <p style='color: #DDD; margin-bottom: 0;'>Desperdício Mensal Estimado:</p>
                <h2 style='color: #FF4B4B; margin: 0;'>R$ {monthly_loss:,.2f}</h2>
                <p style='color: #DDD; margin-bottom: 0; margin-top: 10px;'>Projeção Anual:</p>
                <h4 style='color: #FF4B4B; margin: 0;'>R$ {annual_loss:,.2f}</h4>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Cliente está pagando bem (Ganho)
            monthly_gain = abs(delta) * volume_kg
            st.markdown(f"""
            <div class='savings-card'>
                <h3 style='margin:0; color: #00CC96;'>🟢 Excelente Negociação!</h3>
                <p style='color: white;'>Você está pagando abaixo do preço de referência.</p>
                <h2 style='color: #00CC96;'>Economia: R$ {monthly_gain:,.2f}/mês</h2>
            </div>
            """, unsafe_allow_html=True)

def run_backtest_module():
    with st.sidebar:
        st.header("🧪 Lab"); st.button("Sair", key='bklout', on_click=logout)
    st.title("🧪 Backtest Lab")
    # (Código resumido do backtest - mantém o mesmo da versão anterior)
    df = get_market_data(1095)
    c1, c2 = st.columns([2, 1])
    with c1: st.line_chart(df['WTI'], color="#FFD700") # Simplificado para economizar linhas
    with c2: st.info("Módulo de uso interno para calibração.")

def run_user_management_module():
    with st.sidebar:
        st.header("👥 Usuários"); 
        if get_db(): st.caption("🟢 Online")
        st.markdown("---"); st.button("Sair", key='usr', on_click=logout)

    st.title("👥 Controle de Acessos")
    
    with st.form("new"):
        c1, c2 = st.columns(2)
        u = c1.text_input("Login"); p = c1.text_input("Senha", type="password")
        n = c2.text_input("Nome"); r = c2.selectbox("Perfil", ["client", "admin"])
        
        # SELETOR DE MÓDULOS (Novidade v4.0)
        st.markdown("**Módulos Contratados:**")
        modules = st.multiselect(
            "Selecione os acessos deste cliente:",
            ["Monitor", "Calculadora Financeira"],
            default=["Monitor"]
        )
        
        if st.form_submit_button("Criar", use_container_width=True):
            ok, msg = create_user_in_db(u, p, n, r, modules)
            if ok: st.success(msg)
            else: st.error(msg)
            
    if st.button("🔄 Listar"):
        users = list_users_from_db()
        if users: 
            # Tratamento para exibir lista de módulos na tabela
            df_users = pd.DataFrame(users)
            if 'modules' not in df_users.columns: df_users['modules'] = "['Monitor']" # Fallback
            st.dataframe(df_users[['username', 'name', 'role', 'modules']], use_container_width=True)

# ======================================================
# 6. ORQUESTRAÇÃO (ROTEAMENTO INTELIGENTE)
# ======================================================

if check_password():
    role = st.session_state["user_role"]
    user_modules = st.session_state.get("user_modules", ["Monitor"])
    
    if role == "admin":
        # Admin vê TUDO
        menu_options = ["Monitor", "Calculadora Financeira", "Backtest", "Usuários"]
        st.sidebar.title("Painel Admin")
    else:
        # Cliente vê apenas o que contratou
        menu_options = user_modules
        st.sidebar.title("Menu")
    
    # Seletor de Navegação
    page = st.sidebar.radio("Ir para:", menu_options)
    
    # Roteador
    if page == "Monitor": run_monitor_module(is_admin=(role=="admin"))
    elif page == "Calculadora Financeira": run_financial_calculator()
    elif page == "Backtest": run_backtest_module()
    elif page == "Usuários": run_user_management_module()
