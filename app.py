import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import numpy as np

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

# ======================================================
# 2. CSS PROFISSIONAL
# ======================================================
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; }
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    
    /* Sidebar */
    section[data-testid="stSidebar"] { background-color: #1C1E24; }
    section[data-testid="stSidebar"] * { color: #FFFFFF !important; }
    
    /* Tipografia Dourada */
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
    
    /* Abas/Radio Buttons */
    .stRadio > label { display: none; }
    </style>
    """, unsafe_allow_html=True)

# ======================================================
# 3. FUNÇÕES DE DADOS
# ======================================================
@st.cache_data(ttl=3600)
def get_market_data(days_back=180):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    wti = yf.download("CL=F", start=start_date, end=end_date, progress=False, auto_adjust=True)['Close']
    brl = yf.download("BRL=X", start=start_date, end=end_date, progress=False, auto_adjust=True)['Close']
    
    df = pd.concat([wti, brl], axis=1).dropna()
    df.columns = ['WTI', 'USD_BRL']
    
    # Preço FOB Base
    df['PP_FOB_USD'] = (df['WTI'] * 0.014) + 0.35
    
    return df

# ======================================================
# 4. MÓDULO 1: MONITOR DE PREÇOS
# ======================================================
def run_monitor_module():
    with st.sidebar:
        st.header("🏭 Gold Rush")
        st.markdown("---")
        st.subheader("⚙️ Cost Build-up")
        
        ocean_freight = st.slider("Frete Marítimo (USD/ton)", 0, 300, 60, step=10)
        icms_user = st.selectbox("ICMS Destino (%)", [18, 12, 7, 4], index=0)
        freight_user = st.slider("Frete Interno (R$/kg)", 0.00, 0.50, 0.15, step=0.01)
        margin_user = st.slider("Margem (%)", 0, 20, 10)
        
        st.markdown("---")
        st.caption("v2.7 - Visual Fixed")

    st.title("Monitor de Custo Industrial: Polipropileno")
    
    with st.spinner('Calculando Cotações...'):
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
        ax.plot(df.index, df['Trend'], color='#FFD700', label='Tendência', linewidth=2.5)
        
        ax.tick_params(axis='both', colors='#AAA', labelsize=8)
        for spine in ax.spines.values(): spine.set_color('#333')
        ax.grid(True, alpha=0.1)
        ax.legend(facecolor='#1C1E24', labelcolor='white', fontsize=8)
        st.pyplot(fig, use_container_width=True)

        if variation_pct > 0.5:
            msg, cor = "⚠️ <b>ALTA:</b> Pressão de custos.", "#FF4B4B"
        elif variation_pct < -0.5:
            msg, cor = "✅ <b>BAIXA:</b> Janela de oportunidade.", "#00CC96"
        else:
            msg, cor = "⚖️ <b>ESTÁVEL:</b> Mercado lateralizado.", "#FFAA00"

        st.markdown(f"<div style='background-color: #1C1E24; padding: 10px; border-left: 4px solid {cor}; color: #DDD; font-size: 0.9rem;'>{msg}</div>", unsafe_allow_html=True)

# ======================================================
# 5. MÓDULO 2: LABORATÓRIO DE BACKTEST (Gráficos Otimizados)
# ======================================================
def run_backtest_module():
    with st.sidebar:
        st.header("🧪 Lab de Fórmula")
        st.info("Ajuste os coeficientes para bater com seu histórico.")
        
        coef_wti = st.number_input("Coef. WTI", value=0.014, format="%.4f", step=0.001)
        coef_spread = st.number_input("Spread ($)", value=0.35, format="%.2f", step=0.05)
        coef_markup = st.number_input("Markup Brasil", value=1.45, format="%.2f", step=0.05)
        years_back = st.slider("Anos de Histórico", 1, 5, 3)

    st.title("🧪 Laboratório de Backtest")
    st.markdown("Valide a precisão da sua fórmula comparando com o passado.")

    df = get_market_data(days_back=years_back*365)
    
    # Fórmula de Teste
    df['PP_Theoretical'] = ((df['WTI'] * coef_wti) + coef_spread) * df['USD_BRL'] * coef_markup
    
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.subheader("Curva Teórica (O Modelo)")
        
        # GRÁFICO MATPLOTLIB (Substituindo st.line_chart)
        fig, ax = plt.subplots(figsize=(10, 4))
        fig.patch.set_facecolor('#0E1117')
        ax.set_facecolor('#0E1117')
        
        ax.plot(df.index, df['PP_Theoretical'], color='#FFD700', linewidth=2, label='Modelo Teórico')
        
        # Eixos Formatados (Datas Claras)
        ax.tick_params(axis='x', colors='#AAAAAA', rotation=45)
        ax.tick_params(axis='y', colors='#AAAAAA')
        for spine in ax.spines.values(): spine.set_color('#333')
        ax.grid(True, alpha=0.1)
        ax.legend(facecolor='#1C1E24', labelcolor='white')
        
        st.pyplot(fig, use_container_width=True)
        
    with c2:
        st.subheader("Validação Real")
        uploaded_file = st.file_uploader("Upload CSV (Data, Preco)", type="csv")
        
        if uploaded_file and mean_absolute_percentage_error:
            try:
                real_df = pd.read_csv(uploaded_file)
                real_df['Data'] = pd.to_datetime(real_df['Data'])
                real_df = real_df.set_index('Data').sort_index()
                
                comparison = df.join(real_df, how='inner').dropna()
                comparison.rename(columns={'Preco': 'PP_Real'}, inplace=True)
                
                if not comparison.empty:
                    mape = mean_absolute_percentage_error(comparison['PP_Real'], comparison['PP_Theoretical'])
                    rmse = np.sqrt(mean_squared_error(comparison['PP_Real'], comparison['PP_Theoretical']))
                    
                    st.success("✅ Calculado!")
                    st.metric("Erro Médio (MAPE)", f"{mape*100:.1f}%")
                    st.metric("Erro (Reais)", f"R$ {rmse:.2f}")
                    
                    # GRÁFICO DE COMPARAÇÃO (MATPLOTLIB)
                    fig_comp, ax_comp = plt.subplots(figsize=(10, 4))
                    fig_comp.patch.set_facecolor('#0E1117')
                    ax_comp.set_facecolor('#0E1117')
                    
                    ax_comp.plot(comparison.index, comparison['PP_Theoretical'], color='#FFD700', label='Teórico', linewidth=2)
                    ax_comp.plot(comparison.index, comparison['PP_Real'], color='#00FF00', label='Real (NF)', linewidth=2, linestyle='--')
                    
                    ax_comp.tick_params(axis='x', colors='#AAAAAA', rotation=45)
                    ax_comp.tick_params(axis='y', colors='#AAAAAA')
                    for spine in ax_comp.spines.values(): spine.set_color('#333')
                    ax_comp.grid(True, alpha=0.1)
                    ax_comp.legend(facecolor='#1C1E24', labelcolor='white')
                    
                    st.pyplot(fig_comp, use_container_width=True)
                else:
                    st.warning("Sem datas coincidentes.")
            except Exception as e:
                st.error(f"Erro no CSV: {e}")
        elif not mean_absolute_percentage_error:
            st.error("Biblioteca sklearn não instalada.")

# ======================================================
# 6. ROTEADOR
# ======================================================
st.sidebar.title("Navegação")
page = st.sidebar.radio("Módulo", ["Monitor de Mercado", "Laboratório de Backtest"])

if page == "Monitor de Mercado":
    run_monitor_module()
elif page == "Laboratório de Backtest":
    run_backtest_module()
