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
    .stTextInput input { background-color: #1C1E24; color: white; border: 1px solid #444; }
    div[data-testid="stForm"] { border: 1px solid #FFD700; background-color: #16181E; padding: 20px; border-radius: 10px; }
    
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
        # Verifica se já inicializou para não duplicar a instância
        if not firebase_admin._apps:
            # Verifica se existe a configuração [firebase] nos segredos
            if "firebase" in st.secrets:
                # Lógica Híbrida: Aceita tanto o formato novo (TOML Dict) quanto o antigo (JSON string)
                if "text_key" in st.secrets["firebase"]:
                    # Formato Antigo (JSON String)
                    key_dict = json.loads(st.secrets["firebase"]["text_key"])
                else:
                    # Formato Novo (TOML Nativo - Recomendado)
                    # Converte o objeto de configuração do Streamlit para um dicionário Python puro
                    key_dict = dict(st.secrets["firebase"])
                
                # Cria a credencial
                cred = credentials.Certificate(key_dict)
                firebase_admin.initialize_app(cred)
                return firestore.client()
        else:
            return firestore.client()
    except Exception as e:
        # Se falhar, não quebra o app, apenas loga o erro (o login usará o backup local)
        print(f"Aviso de conexão DB: {e}")
        return None

def authenticate_user(username, password):
    """Verifica usuário no Banco de Dados (Prioridade) ou no Backup Local."""
    
    # 1. Tentativa: Banco de Dados Real (Firestore)
    db = get_db()
    if db:
        try:
            users_ref = db.collection('users')
            # Busca usuário e senha compatíveis
            query = users_ref.where('username', '==', username).where('password', '==', password).stream()
            for doc in query:
                user_data = doc.to_dict()
                return user_data # Sucesso: Retorna dados do usuário
        except Exception as e:
            print(f"Erro ao consultar Firestore: {e}")
    
    # 2. Fallback: Arquivo de Segredos (Backup para quando o DB não estiver configurado)
    if "users" in st.secrets:
        if username in st.secrets["users"] and st.secrets["users"][username]["password"] == password:
            return st.secrets["users"][username]
            
    return None

# ======================================================
# 3. SISTEMA DE LOGIN
# ======================================================

def check_password():
    """Gerencia a tela de login e sessão."""
    if st.session_state.get("password_correct", False):
        return True

    # Layout Centralizado para Login
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
# 4. FUNÇÕES DE DADOS (Lógica de Negócio)
# ======================================================
@st.cache_data(ttl=3600)
def get_market_data(days_back=180):
    """Baixa dados do Yahoo Finance e prepara base."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    # Baixa dados com auto_adjust para evitar warnings
    wti = yf.download("CL=F", start=start_date, end=end_date, progress=False, auto_adjust=True)['Close']
    brl = yf.download("BRL=X", start=start_date, end=end_date, progress=False, auto_adjust=True)['Close']
    
    df = pd.concat([wti, brl], axis=1).dropna()
    df.columns = ['WTI', 'USD_BRL']
    
    # Preço FOB Base (Proxy Internacional)
    df['PP_FOB_USD'] = (df['WTI'] * 0.014) + 0.35
    return df

# ======================================================
# 5. MÓDULOS DA APLICAÇÃO
# ======================================================

def run_monitor_module(is_admin=False):
    """Módulo 1: O Dashboard Principal."""
    
    # Sidebar Específica
    with st.sidebar:
        if is_admin:
            st.success(f"👋 Admin: {st.session_state['user_name']}")
        else:
            st.info(f"🏭 Cliente: {st.session_state['user_name']}")
            
        st.header("⚙️ Cost Build-up")
        st.caption("Simule seus custos reais:")
        
        ocean_freight = st.slider("Frete Marítimo (USD/ton)", 0, 300, 60, step=10)
        icms_user = st.selectbox("ICMS Destino (%)", [18, 12, 7, 4], index=0)
        freight_user = st.slider("Frete Interno (R$/kg)", 0.00, 0.50, 0.15, step=0.01)
        margin_user = st.slider("Margem Distribuidor (%)", 0, 20, 10)
        
        st.markdown("---")
        if st.button("Sair / Logout"): logout()

    # Conteúdo Principal
    st.title("Monitor de Custo Industrial: Polipropileno")
    
    with st.spinner('Calculando Cost Build-up...'):
        df = get_market_data(days_back=180)
        
        # --- LÓGICA DE CUSTO SP ---
        # 1. CFR (Cost and Freight)
        df['CFR_USD'] = df['PP_FOB_USD'] + (ocean_freight / 1000)
        # 2. Landed Cost (II + Taxas)
        df['Landed_BRL'] = df['CFR_USD'] * df['USD_BRL'] * 1.12
        # 3. Custo Operacional (Com Frete Interno)
        df['Operational_Cost'] = df['Landed_BRL'] + freight_user
        # 4. Preço Líquido (Com Margem)
        df['Price_Net'] = df['Operational_Cost'] * (1 + (margin_user/100))
        # 5. Preço Final (Com ICMS por dentro)
        df['PP_Price'] = df['Price_Net'] / (1 - (icms_user/100))
        
        # Tendência
        df['Trend'] = df['PP_Price'].rolling(window=7).mean()
        
        # Métricas
        current_price = df['PP_Price'].iloc[-1]
        variation_pct = (current_price / df['PP_Price'].iloc[-7] - 1) * 100
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Preço Final (R$/kg)", f"R$ {current_price:.2f}", f"{current_price - df['PP_Price'].iloc[-2]:.2f}")
        c2.metric("Tendência (7d)", f"{variation_pct:.2f}%", delta_color="inverse")
        c3.metric("Frete Marítimo", f"USD {ocean_freight}/ton")
        c4.metric("Dólar Base", f"R$ {df['USD_BRL'].iloc[-1]:.4f}")

        # Gráfico Matplotlib Otimizado
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

        # Insight de Negócio
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
        st.info("Ajuste os coeficientes para bater com o histórico.")
        
        coef_wti = st.number_input("Coef. WTI", value=0.014, format="%.4f", step=0.001)
        coef_spread = st.number_input("Spread ($)", value=0.35, format="%.2f", step=0.05)
        coef_markup = st.number_input("Markup Brasil", value=1.45, format="%.2f", step=0.05)
        years_back = st.slider("Anos Históricos", 1, 5, 3)
        
        st.markdown("---")
        if st.button("Sair / Logout", key='bt_logout'): logout()

    st.title("🧪 Laboratório de Backtest")
    st.markdown("Valide a precisão da sua fórmula matemática comparando com o passado.")

    df = get_market_data(days_back=years_back*365)
    
    # Aplica a Fórmula de Teste
    df['PP_Theoretical'] = ((df['WTI'] * coef_wti) + coef_spread) * df['USD_BRL'] * coef_markup
    
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.subheader("Curva Teórica (O Modelo)")
        
        # Gráfico Teórico
        fig, ax = plt.subplots(figsize=(10, 4))
        fig.patch.set_facecolor('#0E1117')
        ax.set_facecolor('#0E1117')
        ax.plot(df.index, df['PP_Theoretical'], color='#FFD700', linewidth=2, label='Modelo')
        
        # Eixos de Data Formatados
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%Y'))
        ax.tick_params(axis='x', colors='#AAAAAA', rotation=45)
        ax.tick_params(axis='y', colors='#AAAAAA')
        for spine in ax.spines.values(): spine.set_color('#333')
        ax.grid(True, alpha=0.1)
        
        st.pyplot(fig, use_container_width=True)
        
    with c2:
        st.subheader("Validação Real")
        st.markdown("Faça upload do seu histórico de compras (CSV).")
        uploaded_file = st.file_uploader("Arquivo CSV (Colunas: Data, Preco)", type="csv")
        
        if uploaded_file and mean_absolute_percentage_error:
            try:
                real_df = pd.read_csv(uploaded_file)
                real_df['Data'] = pd.to_datetime(real_df['Data'])
                real_df = real_df.set_index('Data').sort_index()
                
                # Cruzamento (Inner Join por Data)
                comparison = df.join(real_df, how='inner').dropna()
                comparison.rename(columns={'Preco': 'PP_Real'}, inplace=True)
                
                if not comparison.empty:
                    mape = mean_absolute_percentage_error(comparison['PP_Real'], comparison['PP_Theoretical'])
                    rmse = np.sqrt(mean_squared_error(comparison['PP_Real'], comparison['PP_Theoretical']))
                    
                    st.success("✅ Validação Concluída!")
                    st.metric("Erro Médio (MAPE)", f"{mape*100:.1f}%")
                    st.metric("Erro (Reais)", f"R$ {rmse:.2f}")
                    
                    # Gráfico Comparativo
                    fig_comp, ax_comp = plt.subplots(figsize=(10, 4))
                    fig_comp.patch.set_facecolor('#0E1117')
                    ax_comp.set_facecolor('#0E1117')
                    
                    ax_comp.plot(comparison.index, comparison['PP_Theoretical'], color='#FFD700', label='Teórico')
                    ax_comp.plot(comparison.index, comparison['PP_Real'], color='#00FF00', label='Real', linestyle='--')
                    
                    ax_comp.xaxis.set_major_formatter(mdates.DateFormatter('%m/%Y'))
                    ax_comp.tick_params(axis='x', colors='#AAA', rotation=45)
                    ax_comp.tick_params(axis='y', colors='#AAA')
                    ax_comp.legend(facecolor='#1C1E24', labelcolor='white')
                    
                    st.pyplot(fig_comp, use_container_width=True)
                else:
                    st.warning("As datas do CSV não coincidem com o histórico.")
            except Exception as e:
                st.error(f"Erro ao processar CSV: {e}")
        elif not mean_absolute_percentage_error:
            st.error("Biblioteca scikit-learn ausente.")

# ======================================================
# 6. ORQUESTRAÇÃO (CONTROLLER)
# ======================================================

if check_password():
    role = st.session_state["user_role"]
    
    if role == "admin":
        # Admin vê menu de navegação
        st.sidebar.title("Navegação Admin")
        page = st.sidebar.radio("Módulo", ["Monitor de Mercado", "Laboratório de Backtest"])
        
        if page == "Monitor de Mercado":
            run_monitor_module(is_admin=True)
        elif page == "Laboratório de Backtest":
            run_backtest_module()
            
    elif role == "client":
        # Cliente vê apenas o Monitor (sem opção de navegar)
        run_monitor_module(is_admin=False)
