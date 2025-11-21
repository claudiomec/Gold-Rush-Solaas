import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error
import numpy as np

# Configuração da Página
st.set_page_config(page_title="Gold Rush Backtest Lab", page_icon="🧪", layout="wide")

# Estilo Dark
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; }
    h1, h2, h3 { color: #FFD700 !important; }
    .stMetric { background-color: #1C1E24; padding: 10px; border-radius: 8px; border: 1px solid #444; }
    .stMetric label { color: #FFD700 !important; }
    .stMetric div { color: #FFF !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("🧪 Laboratório de Backtest: Fórmula PP")
st.markdown("""
Use esta ferramenta para **validar a precisão** da sua fórmula matemática contra dados passados.
Se a curva teórica bater com seu histórico de compras, o modelo está aprovado para Forecast.
""")

# --- SIDEBAR: CONFIGURAÇÃO DA FÓRMULA ---
with st.sidebar:
    st.header("⚙️ Calibragem da Fórmula")
    st.info("Fórmula Base: ((WTI * A) + B) * Dólar * C")
    
    # Coeficientes Dinâmicos (para você brincar de ajustar)
    coef_wti = st.number_input("Coeficiente WTI (A)", value=0.015, format="%.4f", step=0.001)
    coef_spread = st.number_input("Spread USD/kg (B)", value=0.35, format="%.2f", step=0.05)
    coef_markup = st.number_input("Markup Brasil (C)", value=1.45, format="%.2f", step=0.05)
    
    st.markdown("---")
    st.write("**Janela de Análise:**")
    years_back = st.slider("Anos de Histórico", 1, 5, 3)

# --- BACKEND: RECUPERAÇÃO HISTÓRICA ---
@st.cache_data
def get_historical_data(years):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years*365)
    
    # Baixar histórico longo
    wti = yf.download("CL=F", start=start_date, end=end_date, progress=False, auto_adjust=True)['Close']
    brl = yf.download("BRL=X", start=start_date, end=end_date, progress=False, auto_adjust=True)['Close']
    
    df = pd.concat([wti, brl], axis=1).dropna()
    df.columns = ['WTI', 'USD_BRL']
    return df

df = get_historical_data(years_back)

# --- APLICAÇÃO DA FÓRMULA (SIMULAÇÃO) ---
# PP = ((WTI * 0.015) + 0.35) * Dólar * 1.45
df['PP_Theoretical'] = ((df['WTI'] * coef_wti) + coef_spread) * df['USD_BRL'] * coef_markup

# --- ÁREA DE VALIDAÇÃO (UPLOAD) ---
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📈 Curva Teórica (O Modelo)")
    st.line_chart(df['PP_Theoretical'], color="#FFD700", height=400)

with col2:
    st.subheader("📂 Validar com Realidade")
    st.markdown("Tem dados reais de compra? Faça upload para calcular a precisão.")
    
    uploaded_file = st.file_uploader("Upload CSV (Colunas: Data, Preco)", type="csv")
    
    if uploaded_file is not None:
        try:
            # Ler CSV do usuário
            real_df = pd.read_csv(uploaded_file)
            real_df['Data'] = pd.to_datetime(real_df['Data'])
            real_df = real_df.set_index('Data').sort_index()
            
            # Cruzar dados (Merge) com tolerância de datas
            # Requerer match exato ou usar asof merge se necessário
            # Aqui vamos simplificar fazendo um reindex no dataframe do modelo
            comparison = df.join(real_df, how='inner')
            comparison.rename(columns={'Preco': 'PP_Real'}, inplace=True)
            
            if not comparison.empty:
                # Métricas de Erro
                mape = mean_absolute_percentage_error(comparison['PP_Real'], comparison['PP_Theoretical'])
                rmse = np.sqrt(mean_squared_error(comparison['PP_Real'], comparison['PP_Theoretical']))
                
                st.success("✅ Validação Concluída!")
                st.metric("Erro Médio (MAPE)", f"{mape*100:.2f}%")
                st.metric("Erro em Reais (RMSE)", f"R$ {rmse:.2f}")
                
                # Plota comparação
                st.markdown("### Comparativo Visual")
                comp_chart = comparison[['PP_Theoretical', 'PP_Real']]
                st.line_chart(comp_chart, color=["#FFD700", "#00FF00"])
                
                # Insight de Calibragem
                avg_diff = (comparison['PP_Theoretical'] - comparison['PP_Real']).mean()
                if avg_diff > 0:
                    st.warning(f"Seu modelo está superestimando em média R$ {avg_diff:.2f}. Tente reduzir o Markup.")
                else:
                    st.warning(f"Seu modelo está subestimando em média R$ {abs(avg_diff):.2f}. Tente aumentar o Spread.")
            else:
                st.error("As datas do seu CSV não coincidem com o histórico baixado.")
        except Exception as e:
            st.error(f"Erro ao ler arquivo: {e}")
            st.info("O CSV deve ter cabeçalho: 'Data' (aaaa-mm-dd) e 'Preco' (float).")

# --- ANÁLISE ESTATÍSTICA DO MODELO ---
st.markdown("---")
st.subheader("📊 Estatísticas da Fórmula")
col_a, col_b, col_c, col_d = st.columns(4)
col_a.metric("Preço Médio (Período)", f"R$ {df['PP_Theoretical'].mean():.2f}")
col_b.metric("Mínima Histórica", f"R$ {df['PP_Theoretical'].min():.2f}")
col_c.metric("Máxima Histórica", f"R$ {df['PP_Theoretical'].max():.2f}")
col_d.metric("Volatilidade", f"{df['PP_Theoretical'].std():.2f}")