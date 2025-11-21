import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# ======================================================
# 1. CONFIGURAÇÃO DA PÁGINA (IDENTIDADE GOLD RUSH)
# ======================================================
st.set_page_config(
    page_title="Gold Rush Analytics",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo CSS customizado: Tema Escuro e Dourado
st.markdown("""
    <style>
    /* Fundo Principal */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    /* Cards de Métricas */
    div[data-testid="stMetric"] {
        background-color: #262730;
        border: 1px solid #444;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    div[data-testid="stMetricLabel"] {
        color: #FFD700 !important; /* Dourado */
    }
    /* Títulos */
    h1, h2, h3 {
        color: #FFD700 !important;
    }
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #16181E;
    }
    </style>
    """, unsafe_allow_html=True)

# ======================================================
# 2. FUNÇÕES DE BACKEND (Lógica SolaaS Calibrada)
# ======================================================
@st.cache_data(ttl=3600) # Cache de 1 hora para não sobrecarregar
def get_data():
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    # Baixando dados (WTI e Dólar)
    # auto_adjust=True evita warnings do Yahoo Finance
    wti = yf.download("CL=F", start=start_date, end=end_date, progress=False, auto_adjust=True)['Close']
    brl = yf.download("BRL=X", start=start_date, end=end_date, progress=False, auto_adjust=True)['Close']
    
    # Unindo e limpando
    df = pd.concat([wti, brl], axis=1).dropna()
    df.columns = ['WTI', 'USD_BRL']
    
    # --- ALGORITMO DE PRECIFICAÇÃO (CALIBRAGEM SP) ---
    
    # 1. Preço Internacional Base (USD/kg)
    # WTI * 0.014 + $0.35
    df['PP_Intl_USD'] = (df['WTI'] * 0.014) + 0.35
    
    # 2. Landed Cost (Brasil)
    # Conversão + 12% (II + Portos)
    df['Landed_Cost'] = df['PP_Intl_USD'] * df['USD_BRL'] * 1.12
    
    # 3. Tributação (ICMS SP 18% - Gross Up)
    # Base de cálculo "por dentro"
    df['Price_Taxed'] = df['Landed_Cost'] / (1 - 0.18)
    
    # 4. Markup Final (Logística + Margem SolaaS)
    # 1.13 = 13% de markup
    markup_default = 1.13
    df['PP_Price'] = df['Price_Taxed'] * markup_default
    
    # Tendência (Média Móvel 7 dias)
    df['Trend'] = df['PP_Price'].rolling(window=7).mean()
    
    return df

# ======================================================
# 3. INTERFACE DO CLIENTE (FRONTEND)
# ======================================================

# --- BARRA LATERAL ---
with st.sidebar:
    st.title("🏭 Gold Rush SolaaS")
    st.markdown("---")
    st.write("**Painel de Simulação**")
    
    # Filtros interativos
    st.caption("Ajuste os parâmetros para sua realidade:")
    markup_user = st.slider("Margem Distribuidor (%)", min_value=5, max_value=25, value=13)
    icms_user = st.selectbox("ICMS do Estado", [18, 12, 7, 4])
    
    st.markdown("---")
    st.info("💡 **Dica:** Valores acima de R$ 11,00 indicam ineficiência na cadeia de suprimentos.")
    st.caption("Versão 2.1 (Live Data)")

# --- ÁREA PRINCIPAL ---
st.title("Monitor de Custo Industrial: Polipropileno")
st.markdown("### 📊 Inteligência de Mercado em Tempo Real")

# Carregar dados (com spinner de carregamento)
with st.spinner('Conectando aos mercados globais e calibrando modelo...'):
    try:
        df = get_data()
        
        # --- RECALCULO COM INPUTS DO USUÁRIO ---
        # Se o usuário mudou o slider ou o ICMS, recalculamos aqui na hora
        if markup_user != 13 or icms_user != 18:
            # Recalcular ICMS
            df['Price_Taxed'] = df['Landed_Cost'] / (1 - (icms_user/100))
            # Recalcular Margem
            df['PP_Price'] = df['Price_Taxed'] * (1 + (markup_user/100))
            # Recalcular Tendência
            df['Trend'] = df['PP_Price'].rolling(window=7).mean()
            
        # --- KPIs (MÉTRICAS DE TOPO) ---
        current_price = df['PP_Price'].iloc[-1]
        last_price = df['PP_Price'].iloc[-2]
        delta = current_price - last_price
        
        # Variação % da tendência (7 dias)
        variation_pct = (current_price / df['PP_Price'].iloc[-7] - 1) * 100
        
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                label="Preço Justo (R$/kg)", 
                value=f"R$ {current_price:.2f}", 
                delta=f"{delta:.2f} vs ontem"
            )

        with col2:
            st.metric(
                label="Tendência (7 dias)", 
                value=f"{variation_pct:.2f}%", 
                delta_color="inverse" # Verde se cair, Vermelho se subir (para custo é melhor cair)
            )

        with col3:
            st.metric(
                label="Petróleo WTI", 
                value=f"USD {df['WTI'].iloc[-1]:.2f}"
            )

        with col4:
            st.metric(
                label="Dólar Comercial", 
                value=f"R$ {df['USD_BRL'].iloc[-1]:.4f}"
            )

        # --- GRÁFICO PRINCIPAL ---
        st.markdown("---")
        st.subheader("📈 Evolução de Preço (6 Meses)")

        # Criando o gráfico Matplotlib
        fig, ax = plt.subplots(figsize=(12, 5))
        
        # Cores do Fundo
        fig.patch.set_facecolor('#0E1117') 
        ax.set_facecolor('#0E1117')

        # Linhas
        ax.plot(df.index, df['PP_Price'], color='#C0C0C0', alpha=0.3, label='Spot Diário', linewidth=1)
        ax.plot(df.index, df['Trend'], color='#FFD700', label='Tendência Gold Rush', linewidth=3)

        # Estilização dos Eixos (Branco para contraste)
        ax.tick_params(axis='x', colors='#AAAAAA')
        ax.tick_params(axis='y', colors='#AAAAAA')
        ax.spines['bottom'].set_color('#444444')
        ax.spines['top'].set_color('#444444') 
        ax.spines['right'].set_color('#444444')
        ax.spines['left'].set_color('#444444')

        # Grid e Legenda
        ax.grid(True, alpha=0.1, color='white')
        ax.legend(facecolor='#262730', edgecolor='#444', labelcolor='white')
        
        st.pyplot(fig)

        # --- ÁREA DE INSIGHTS ---
        st.markdown("---")
        
        # Lógica do Insight
        if variation_pct > 0.5:
            recommendation = "🔴 **ALERTA DE ALTA:** Recomendamos antecipar compras do mês."
        elif variation_pct < -0.5:
            recommendation = "🟢 **OPORTUNIDADE:** Tendência de queda. Compre apenas o essencial e aguarde."
        else:
            recommendation = "🟡 **MERCADO ESTÁVEL:** Mantenha compras programadas."

        st.markdown(f"""
        <div style='background-color: #262730; padding: 20px; border-radius: 10px; border-left: 5px solid #FFD700;'>
            <h3 style='color: #FFD700; margin:0 0 10px 0;'>🧠 Insight Gold Rush Analytics</h3>
            <p style='color: #E0E0E0; font-size: 16px; margin:0;'>
            O modelo identifica que o preço atual de <b>R$ {current_price:.2f}/kg</b> reflete a volatilidade recente do câmbio (R$ {df['USD_BRL'].iloc[-1]:.3f}).
            <br><br>
            {recommendation}
            </p>
        </div>
        """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Erro ao conectar com os dados: {e}")
        st.warning("Tente recarregar a página em alguns instantes.")