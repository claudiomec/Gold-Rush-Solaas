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
# 2. CSS OTIMIZADO (Compacto)
# ======================================================
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; }
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    div[data-testid="stVerticalBlock"] > div { gap: 0.5rem; }
    
    /* Sidebar */
    section[data-testid="stSidebar"] { background-color: #1C1E24; }
    section[data-testid="stSidebar"] * { color: #FFFFFF !important; }
    
    /* Tipografia */
    h1 { font-size: 1.8rem !important; color: #FFD700 !important; margin-bottom: 0 !important; }
    h3 { font-size: 1.1rem !important; color: #FFD700 !important; }
    
    /* Métricas */
    div[data-testid="stMetric"] {
        background-color: #262730;
        border: 1px solid #444;
        border-radius: 6px;
        padding: 10px;
    }
    div[data-testid="stMetricLabel"] { color: #FFD700 !important; font-size: 0.9rem !important; }
    div[data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 1.4rem !important; }
    </style>
    """, unsafe_allow_html=True)

# ======================================================
# 3. BACKEND (Dados Brutos)
# ======================================================
@st.cache_data(ttl=3600)
def get_raw_data():
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    # Baixa WTI e Dólar
    wti = yf.download("CL=F", start=start_date, end=end_date, progress=False, auto_adjust=True)['Close']
    brl = yf.download("BRL=X", start=start_date, end=end_date, progress=False, auto_adjust=True)['Close']
    
    df = pd.concat([wti, brl], axis=1).dropna()
    df.columns = ['WTI', 'USD_BRL']
    
    # Preço Base Internacional (FOB - Free On Board)
    # WTI * 0.014 + Spread ($0.35) = ~$1.20 USD/kg
    df['PP_FOB_USD'] = (df['WTI'] * 0.014) + 0.35
    
    return df

# ======================================================
# 4. FRONTEND (Calculadora SP)
# ======================================================

# --- SIDEBAR (Parâmetros de Custo) ---
with st.sidebar:
    st.header("🏭 Gold Rush")
    st.markdown("---")
    st.subheader("⚙️ Cost Build-up")
    
    # 1. Logística Internacional
    st.caption("🚢 Logística Internacional")
    ocean_freight = st.slider("Frete Marítimo (USD/ton)", 0, 300, 60, step=10)
    
    # 2. Tributação
    st.caption("🏛️ Tributação")
    icms_user = st.selectbox("ICMS Destino (%)", [18, 12, 7, 4], index=0)
    
    # 3. Logística Física (R$/kg)
    st.caption("🚚 Frete Interno (Santos -> Fábrica)")
    freight_user = st.slider("Custo Rodoviário (R$/kg)", 0.00, 0.50, 0.15, step=0.01)
    
    # 4. Margem do Distribuidor
    st.caption("💰 Margem Comercial")
    margin_user = st.slider("Margem (%)", 0, 20, 10)
    
    st.markdown("---")
    st.caption(f"Config: Frete Intl ${ocean_freight} | ICMS {icms_user}%")

# --- HEADER ---
st.title("Monitor de Custo Industrial: Polipropileno")

# Carregamento e Cálculo em Tempo Real
with st.spinner('Calculando Landed Cost...'):
    try:
        df = get_raw_data()
        
        # === LÓGICA DE NEGÓCIO REFINADA (Cost Build-up) ===
        
        # 1. Custo CFR (Cost and Freight) em USD
        # Soma o frete internacional (convertido de ton para kg) ao preço FOB
        df['CFR_USD'] = df['PP_FOB_USD'] + (ocean_freight / 1000)
        
        # 2. Nacionalização (Landed Cost BRL)
        # Base CFR * Câmbio * 1.12 (II 12% + Taxas Portuárias sobre o valor CFR)
        df['Landed_BRL'] = df['CFR_USD'] * df['USD_BRL'] * 1.12
        
        # 3. Custo Operacional Total (Produto Nacionalizado + Frete Interno)
        df['Operational_Cost'] = df['Landed_BRL'] + freight_user
        
        # 4. Aplicação da Margem Comercial (Sobre o Custo Op)
        df['Price_Net'] = df['Operational_Cost'] * (1 + (margin_user/100))
        
        # 5. Tributação Final (Gross Up - Cálculo "Por Dentro")
        df['PP_Price'] = df['Price_Net'] / (1 - (icms_user/100))
        
        # 6. Tendência
        df['Trend'] = df['PP_Price'].rolling(window=7).mean()
        
        # === VISUALIZAÇÃO ===
        
        current_price = df['PP_Price'].iloc[-1]
        variation_pct = (current_price / df['PP_Price'].iloc[-7] - 1) * 100
        
        # KPIs
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Preço Final (R$/kg)", f"R$ {current_price:.2f}", f"{current_price - df['PP_Price'].iloc[-2]:.2f}")
        c2.metric("Tendência (7d)", f"{variation_pct:.2f}%", delta_color="inverse")
        c3.metric("Frete Marítimo", f"USD {ocean_freight}/ton")
        c4.metric("Dólar Base", f"R$ {df['USD_BRL'].iloc[-1]:.4f}")

        # Gráfico
        fig, ax = plt.subplots(figsize=(10, 3))
        fig.patch.set_facecolor('#0E1117') 
        ax.set_facecolor('#0E1117')
        
        ax.plot(df.index, df['PP_Price'], color='#666', alpha=0.3, label='Spot Calculado', linewidth=1)
        ax.plot(df.index, df['Trend'], color='#FFD700', label='Tendência Gold Rush', linewidth=2.5)
        
        ax.tick_params(axis='both', colors='#AAA', labelsize=8)
        for spine in ax.spines.values(): spine.set_color('#333')
        ax.grid(True, alpha=0.1)
        ax.legend(facecolor='#1C1E24', labelcolor='white', fontsize=8)
        
        plt.tight_layout()
        st.pyplot(fig, use_container_width=True)

        # Insight
        if variation_pct > 0.5:
            msg, cor = "⚠️ <b>ALTA:</b> Pressão de custos. Antecipe.", "#FF4B4B"
        elif variation_pct < -0.5:
            msg, cor = "✅ <b>BAIXA:</b> Janela de oportunidade.", "#00CC96"
        else:
            msg, cor = "⚖️ <b>ESTÁVEL:</b> Mercado lateralizado.", "#FFAA00"

        st.markdown(f"""
        <div style='background-color: #1C1E24; padding: 10px 15px; border-radius: 8px; border-left: 4px solid {cor}; margin-top: 5px;'>
            <p style='color: #DDD; margin: 0; font-size: 0.9rem;'>
            {msg} Cálculo base: <b>CFR (Cost & Freight)</b> com frete marítimo de USD {ocean_freight}/ton.
            </p>
        </div>
        """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Erro de Cálculo: {e}")
