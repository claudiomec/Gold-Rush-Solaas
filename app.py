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

# Tenta importar sklearn para métricas de erro
try:
    from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error
except ImportError:
    mean_absolute_percentage_error = None

# ======================================================
# 1. CONFIGURAÇÃO GLOBAL E CSS
# ======================================================
st.set_page_config(
    page_title="Gold Rush Analytics",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    /* Tema Escuro e Dourado */
    .stApp { background-color: #0E1117; }
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    
    /* Sidebar */
    section[data-testid="stSidebar"] { background-color: #1C1E24; }
    section[data-testid="stSidebar"] * { color: #FFFFFF !important; }
    
    /* Tipografia */
    h1, h2, h3 { color: #FFD700 !important; }
    
    /* Cards e Métricas */
    div[data-testid="stMetric"] {
        background-color: #262730;
        border: 1px solid #444;
        border-radius: 6px;
        padding: 10px;
    }
    div[data-testid="stMetricLabel"] { color: #FFD700 !important; font-size: 0.9rem !important; }
    div[data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 1.4rem !important; }
    
    /* Formulários e Inputs */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] { 
        background-color: #1C1E24 !important; 
        color: white !important; 
        border: 1px solid #444; 
    }
    div[data-testid="stForm"] { border: 1px solid #FFD700; background-color: #16181E; padding: 20px; border-radius: 10px; }
    
    /* Tabelas */
    div[data-testid="stDataFrame"] { background-color: #1C1E24; }

    /* Esconder botões de rádio do menu */
    .stRadio > label { display: none; }
    </style>
    """, unsafe_allow_html=True)

# ======================================================
# 2. GERENCIADOR DE BANCO DE DADOS (FIRESTORE)
# ======================================================

@st.cache_resource
def get_db():
    """Conecta ao Firestore (Google Cloud DB) de forma robusta."""
    try:
        if not firebase_admin._apps:
            if "firebase" in st.secrets:
                if "text_key" in st.secrets["firebase"]:
                    key_dict = json.loads(st.secrets["firebase"]["text_key"])
                else:
                    key_dict = dict(st.secrets["firebase"])
                
                cred = credentials.Certificate(key_dict)
                firebase_admin.initialize_app(cred)
                return firestore.client()
        else:
            return firestore.client()
    except Exception as e:
        print(f"Aviso de conexão DB: {e}")
        return None

def authenticate_user(username, password):
    """Verifica usuário no Banco de Dados (Prioridade) ou no Backup Local."""
    db = get_db()
    if db:
        try:
            users_ref = db.collection('users')
            query = users_ref.where('username', '==', username).where('password', '==', password).stream()
            for doc in query:
                return doc.to_dict()
        except Exception as e:
            print(f"Erro ao consultar Firestore: {e}")
    
    if "users" in st.secrets:
        if username in st.secrets["users"] and st.secrets["users"][username]["password"] == password:
            return st.secrets["users"][username]
    return None

def create_user_in_db(username, password, name, role):
    """Cria um novo usuário no Firestore."""
    db = get_db()
    if not db:
        return False, "Banco de dados não conectado. Configure o Firebase."
    
    try:
        # Usa o username como ID do documento para evitar duplicatas e facilitar busca
        doc_ref = db.collection('users').document(username)
        doc_ref.set({
            'username': username,
            'password': password,
            'name': name,
            'role': role,
            'created_at': firestore.SERVER_TIMESTAMP
        })
        return True, "Usuário criado com sucesso!"
    except Exception as e:
        return False, f"Erro ao criar: {str(e)}"

def list_users_from_db():
    """Lista todos os usuários cadastrados."""
    db = get_db()
    if not db:
        return []
    try:
        users_ref = db.collection('users')
        docs = users_ref.stream()
        return [doc.to_dict() for doc in docs]
    except:
        return []

# ======================================================
# 3. SISTEMA DE LOGIN
# ======================================================

def check_password():
    """Gerencia a tela de login e sessão."""
    if st.session_state.get("password_correct", False):
        return True

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center;'>🔐 Gold Rush Access</h1>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            user = st.text_input("Usuário")
            password = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Entrar no Portal", use_container_width=True)

            if submitted:
                user_data = authenticate_user(user, password)
                if user_data:
                    st.session_state["password_correct"] = True
                    st.session_state["user_role"] = user_data.get("role", "client")
                    st.session_state["user_name"] = user_data.get("name", user)
                    st.rerun()
                else:
                    st.error("😕 Usuário ou senha incorretos.")
                    
    return False

def logout():
    """Limpa a sessão e recarrega."""
    st.session_state["password_correct"] = False
    st.session_state["user_role"] = None
    st.rerun()

# ======================================================
# 4. FUNÇÕES DE DADOS
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

# ======================================================
# 5. MÓDULOS DA APLICAÇÃO
# ======================================================

def run_monitor_module(is_admin=False):
    """Módulo 1: O Dashboard Principal."""
    with st.sidebar:
        if is_admin:
            st.success(f"👋 Admin: {st.session_state['user_name']}")
        else:
            st.info(f"🏭 Cliente: {st.session_state['user_name']}")
            
        st.header("⚙️ Cost Build-up")
        ocean_freight = st.slider("Frete Marítimo (USD/ton)", 0, 300, 60, step=10)
        icms_user = st.selectbox("ICMS Destino (%)", [18, 12, 7, 4], index=0)
        freight_user = st.slider("Frete Interno (R$/kg)", 0.00, 0.50, 0.15, step=0.01)
        margin_user = st.slider("Margem Distribuidor (%)", 0, 20, 10)
        
        st.markdown("---")
        if st.button("Sair / Logout"): logout()

    st.title("Monitor de Custo Industrial: Polipropileno")
    
    with st.spinner('Calculando Cost Build-up...'):
        df = get_market_data(days_back=180)
        
        df['CFR_USD'] = df['PP_FOB_USD'] + (ocean_freight / 1000)
        df['Landed_BRL'] = df['CFR_USD'] * df['USD_BRL'] * 1.12
        df['Operational_Cost'] = df['Landed_BRL'] + freight_user
        df['Price_Net'] = df['Operational_Cost'] * (1 + (margin_user/100))
        df['PP_Price'] = df['Price_Net'] / (1 - (icms_user/100))
        df['Trend'] = df['PP_Price'].rolling(window=7).mean()
        
        current_price = df['PP_Price'].iloc[-1]
        variation_pct = (current_price / df['PP_Price'].iloc[-7] - 1) * 100
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Preço Final (R$/kg)", f"R$ {current_price:.2f}", f"{current_price - df['PP_Price'].iloc[-2]:.2f}")
        c2.metric("Tendência (7d)", f"{variation_pct:.2f}%", delta_color="inverse")
        c3.metric("Frete Marítimo", f"USD {ocean_freight}/ton")
        c4.metric("Dólar Base", f"R$ {df['USD_BRL'].iloc[-1]:.4f}")

        fig, ax = plt.subplots(figsize=(10, 3))
        fig.patch.set_facecolor('#0E1117')
        ax.set_facecolor('#0E1117')
        ax.plot(df.index, df['PP_Price'], color='#666', alpha=0.3, label='Spot Calculado', linewidth=1)
        ax.plot(df.index, df['Trend'], color='#FFD700', label='Tendência Gold Rush', linewidth=2.5)
        ax.tick_params(axis='both', colors='#AAA', labelsize=8)
        for spine in ax.spines.values(): spine.set_color('#333')
        ax.grid(True, alpha=0.1)
        ax.legend(facecolor='#1C1E24', labelcolor='white', fontsize=8)
        st.pyplot(fig, use_container_width=True)

        if variation_pct > 0.5:
            msg, cor = "⚠️ <b>ALTA:</b> Pressão de custos detectada. Antecipe compras.", "#FF4B4B"
        elif variation_pct < -0.5:
            msg, cor = "✅ <b>BAIXA:</b> Janela de oportunidade. Compre fracionado.", "#00CC96"
        else:
            msg, cor = "⚖️ <b>ESTÁVEL:</b> Mercado lateralizado. Mantenha programação.", "#FFAA00"

        st.markdown(f"""
        <div style='background-color: #1C1E24; padding: 10px; border-radius: 6px; border-left: 4px solid {cor}; color: #DDD; font-size: 0.9rem;'>
            {msg} Cálculo baseado em ICMS {icms_user}% e Margem {margin_user}%.
        </div>
        """, unsafe_allow_html=True)

def run_backtest_module():
    """Módulo 2: Validação de Fórmula (Apenas Admin)."""
    with st.sidebar:
        st.header("🧪 Lab de Fórmula")
        coef_wti = st.number_input("Coef. WTI", value=0.014, format="%.4f", step=0.001)
        coef_spread = st.number_input("Spread ($)", value=0.35, format="%.2f", step=0.05)
        coef_markup = st.number_input("Markup Brasil", value=1.45, format="%.2f", step=0.05)
        years_back = st.slider("Anos Históricos", 1, 5, 3)
        st.markdown("---")
        if st.button("Sair / Logout", key='bt_logout'): logout()

    st.title("🧪 Laboratório de Backtest")
    df = get_market_data(days_back=years_back*365)
    df['PP_Theoretical'] = ((df['WTI'] * coef_wti) + coef_spread) * df['USD_BRL'] * coef_markup
    
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("Curva Teórica")
        fig, ax = plt.subplots(figsize=(10, 4))
        fig.patch.set_facecolor('#0E1117')
        ax.set_facecolor('#0E1117')
        ax.plot(df.index, df['PP_Theoretical'], color='#FFD700', linewidth=2)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%Y'))
        ax.tick_params(axis='x', colors='#AAAAAA', rotation=45)
        ax.tick_params(axis='y', colors='#AAAAAA')
        for spine in ax.spines.values(): spine.set_color('#333')
        st.pyplot(fig, use_container_width=True)
    with c2:
        st.subheader("Validação Real")
        uploaded_file = st.file_uploader("Upload CSV", type="csv")
        if uploaded_file and mean_absolute_percentage_error:
            try:
                real_df = pd.read_csv(uploaded_file)
                real_df['Data'] = pd.to_datetime(real_df['Data'])
                real_df = real_df.set_index('Data').sort_index()
                comparison = df.join(real_df, how='inner').dropna()
                if not comparison.empty:
                    mape = mean_absolute_percentage_error(comparison['Preco'], comparison['PP_Theoretical'])
                    rmse = np.sqrt(mean_squared_error(comparison['Preco'], comparison['PP_Theoretical']))
                    st.metric("Erro (MAPE)", f"{mape*100:.1f}%")
                    st.metric("Erro (Reais)", f"R$ {rmse:.2f}")
                else: st.warning("Sem match de datas.")
            except: st.error("Erro no CSV")

def run_user_management_module():
    """Módulo 3: Gestão de Acessos (Apenas Admin)."""
    with st.sidebar:
        st.header("👥 Gestão de Usuários")
        st.info("Adicione novos clientes ou administradores.")
        st.markdown("---")
        if st.button("Sair / Logout", key='users_logout'): logout()

    st.title("👥 Controle de Acessos")
    
    # Formulário de Cadastro
    st.markdown("### Cadastrar Novo Usuário")
    with st.form("new_user_form"):
        col1, col2 = st.columns(2)
        with col1:
            new_username = st.text_input("Usuário (Login)", placeholder="Ex: cliente_abc")
            new_password = st.text_input("Senha Provisória", type="password")
        with col2:
            new_name = st.text_input("Nome da Empresa / Pessoa", placeholder="Ex: Indústria ABC Ltda")
            new_role = st.selectbox("Nível de Acesso", ["client", "admin"])
        
        submitted = st.form_submit_button("Criar Acesso", use_container_width=True)
        
        if submitted:
            if new_username and new_password and new_name:
                success, msg = create_user_in_db(new_username, new_password, new_name, new_role)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
            else:
                st.warning("Por favor, preencha todos os campos.")

    # Listagem de Usuários Existentes
    st.markdown("---")
    st.markdown("### Usuários Cadastrados (Firestore)")
    
    # Botão de refresh manual para não ficar lendo o banco toda hora
    if st.button("🔄 Atualizar Lista"):
        users_list = list_users_from_db()
        if users_list:
            # Transforma em DataFrame para exibir bonito
            df_users = pd.DataFrame(users_list)
            # Seleciona e renomeia colunas para exibição
            if not df_users.empty:
                display_cols = ['name', 'username', 'role']
                # Garante que as colunas existem
                cols_to_show = [c for c in display_cols if c in df_users.columns]
                st.dataframe(
                    df_users[cols_to_show].rename(columns={
                        'name': 'Nome / Empresa',
                        'username': 'Login',
                        'role': 'Permissão'
                    }), 
                    use_container_width=True,
                    hide_index=True
                )
        else:
            st.info("Nenhum usuário encontrado no banco de dados (ou erro de conexão).")

# ======================================================
# 6. ORQUESTRAÇÃO (CONTROLLER)
# ======================================================

if check_password():
    role = st.session_state["user_role"]
    
    if role == "admin":
        st.sidebar.title("Painel Admin")
        # Adicionei a nova opção no menu
        page = st.sidebar.radio("Navegação", ["Monitor de Mercado", "Laboratório de Backtest", "Gestão de Usuários"])
        
        if page == "Monitor de Mercado":
            run_monitor_module(is_admin=True)
        elif page == "Laboratório de Backtest":
            run_backtest_module()
        elif page == "Gestão de Usuários":
            run_user_management_module()
            
    elif role == "client":
        run_monitor_module(is_admin=False)
