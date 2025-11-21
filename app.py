import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# ======================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ======================================================
st.set_page_config(
    page_title="Gold Rush Analytics",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ======================================================
# 2. CSS CORRIGIDO (Alto Contraste)
# ======================================================
st.markdown("""
    <style>
    /* Fundo Geral */
    .stApp {
        background-color: #0E1117;
    }
    
    /* --- BARRA LATERAL (SIDEBAR) --- */
    section[data-testid="stSidebar"] {
        background-color: #1C1E24; /* Cinza mais claro que o fundo */
    }
    
    /* Forçar cor branca em TODOS os textos da sidebar */
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3, 
    section[data-testid="stSidebar"] label, 
    section[data-testid="stSidebar"] span, 
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] div {
        color: #FFFFFF !important;
    }
    
    /* Títulos Dourados (Gold Rush) */
    h1, h2, h3 {
        color: #FFD700 !important;
    }
    
    /* Cards de Métricas */
    div[data-testid="stMetric"] {
        background-color: #262730;
        border: 1px solid #444;
        border-radius: 8px;
        padding: 10px;
    }
    div[data-testid="stMetricLabel"] {
        color: #FFD700 !important; /* Label Dourado */
    }
    div[data-testid="stMetricValue"] {
        color: #FFFFFF !important; /* Valor Branco */
    }
    </style>
    """, unsafe_allow_html=True)

# ======================================================
# 3. BACKEND (Lógica de Negócio)
# ======================================================
@st.cache_data(ttl=3600)
def get_data():
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    # Baixando dados com auto_adjust para evitar erros
    wti = yf.download("CL=F", start=start_date, end=end_date, progress=False, auto_adjust=True)['Close']
    brl = yf.download("BRL=X", start=start_date, end=end_date, progress=False, auto_adjust=True)['Close']
    
    df = pd.concat([wti, brl], axis=1).dropna()
    df.columns = ['WTI', 'USD_BRL']
    
    # Lógica Base (Sem Markup ainda)
    df['PP_Intl_USD'] = (df['WTI'] * 0.014) + 0.35
    df['Landed_Cost'] = df['PP_Intl_USD'] * df['USD_BRL'] * 1.12
    
    return df

# ======================================================
# 4. FRONTEND (Interface)
# ======================================================

# --- SIDEBAR ---
with st.sidebar:
    st.title("🏭 Gold Rush SolaaS")
    st.markdown("---")
    
    st.header("⚙️ Simulação")
    
    # Inputs
    markup_user = st.slider("Margem Distribuidor (%)", 5, 25, 13)
    icms_user = st.selectbox("ICMS do Estado (%)", [18, 12, 7, 4])
    
    st.markdown("---")
    st.info("ℹ️ Ajuste os filtros acima para recalcular o preço final.")
    st.caption("v2.2 - Contraste Ajustado")

# --- ÁREA PRINCIPAL ---
st.title("Monitor de Custo Industrial: Polipropileno")
st.markdown("### 📊 Inteligência de Mercado em Tempo Real")

# Carregamento
with st.spinner('Conectando aos mercados globais...'):
    try:
        # Pega dados base
        df = get_data()
        
        # --- CÁLCULO DINÂMICO (Baseado na Sidebar) ---
        # 1. Aplica ICMS "Por Dentro"
        df['Price_Taxed'] = df['Landed_Cost'] / (1 - (icms_user/100))
        # 2. Aplica Margem
        df['PP_Price'] = df['Price_Taxed'] * (1 + (markup_user/100))
        # 3. Calcula Tendência
        df['Trend'] = df['PP_Price'].rolling(window=7).mean()
        
        # --- KPIs ---
        current_price = df['PP_Price'].iloc[-1]
        
        # Variação % (7 dias)
        variation_pct = (current_price / df['PP_Price'].iloc[-7] - 1) * 100
        
        col1, col2, col3, col4 = st.columns(4)
        
        col1.metric("Preço Justo (R$/kg)", f"R$ {current_price:.2f}", f"{current_price - df['PP_Price'].iloc[-2]:.2f}")
        col2.metric("Tendência (7d)", f"{variation_pct:.2f}%", delta_color="inverse")
        col3.metric("Petróleo WTI", f"USD {df['WTI'].iloc[-1]:.2f}")
        col4.metric("Dólar", f"R$ {df['USD_BRL'].iloc[-1]:.4f}")

        # --- GRÁFICO ---
        st.markdown("---")
        st.subheader("📈 Evolução de Preço (6 Meses)")

        fig, ax = plt.subplots(figsize=(12, 5))
        # Configuração de Cores do Gráfico para bater com o tema
        fig.patch.set_facecolor('#0E1117') 
        ax.set_facecolor('#0E1117')
        
        ax.plot(df.index, df['PP_Price'], color='#888888', alpha=0.3, label='Spot Diário', linewidth=1)
        ax.plot(df.index, df['Trend'], color='#FFD700', label='Tendência Gold Rush', linewidth=3)
        
        # Eixos brancos
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')
        ax.spines['bottom'].set_color('#333')
        ax.spines['top'].set_color('#333') 
        ax.spines['right'].set_color('#333')
        ax.spines['left'].set_color('#333')
        
        ax.grid(True, alpha=0.1)
        ax.legend(facecolor='#1C1E24', labelcolor='white', framealpha=1)
        
        st.pyplot(fig)

        # --- INSIGHT ---
        if variation_pct > 0.5:
            msg = "⚠️ TENDÊNCIA DE ALTA: Antecipe compras."
            cor_borda = "#FF4B4B" # Vermelho
        elif variation_pct < -0.5:
            msg = "✅ TENDÊNCIA DE BAIXA: Compre apenas o necessário."
            cor_borda = "#00CC96" # Verde
        else:
            msg = "⚖️ ESTABILIDADE: Mantenha programação."
            cor_borda = "#FFAA00" # Amarelo

        st.markdown(f"""
        <div style='background-color: #1C1E24; padding: 15px; border-radius: 10px; border-left: 5px solid {cor_borda};'>
            <h4 style='color: white; margin:0;'>🔎 Análise Executiva</h4>
            <p style='color: #CCC; margin: 5px 0 0 0;'>{msg}</p>
        </div>
        """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Erro de conexão: {e}")
