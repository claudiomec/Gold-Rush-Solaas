import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# Tenta importar métricas de erro (Graceful Degradation)
try:
    from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

@st.cache_data(ttl=3600)
def get_market_data(days_back=180):
    """
    Baixa dados históricos do Yahoo Finance (WTI e USD/BRL).
    Retorna DataFrame limpo e alinhado.
    """
    end = datetime.now()
    start = end - timedelta(days=days_back)
    
    # Download silencioso e ajustado
    wti = yf.download("CL=F", start=start, end=end, progress=False, auto_adjust=True)['Close']
    brl = yf.download("BRL=X", start=start, end=end, progress=False, auto_adjust=True)['Close']
    
    # Tratamento de falha de API (Dados Dummy para não quebrar UI)
    if wti.empty or brl.empty:
        idx = pd.date_range(start, end)
        return pd.DataFrame({
            'WTI': [70.0]*len(idx), 
            'USD_BRL': [5.0]*len(idx), 
            'PP_FOB_USD': [1.2]*len(idx)
        }, index=idx)

    df = pd.concat([wti, brl], axis=1).dropna()
    df.columns = ['WTI', 'USD_BRL']
    
    # --- FÓRMULA BASE (Proxy Internacional) ---
    # WTI * Coeficiente + Spread
    df['PP_FOB_USD'] = (df['WTI'] * 0.014) + 0.35
    
    return df

def calculate_cost_buildup(df, ocean_freight, freight_internal, icms_pct, margin_pct):
    """
    Aplica a engenharia de custos SP sobre um DataFrame de mercado.
    """
    df = df.copy()
    
    # 1. CFR (Cost and Freight)
    df['CFR_USD'] = df['PP_FOB_USD'] + (ocean_freight / 1000)
    
    # 2. Landed Cost (Nacionalização) - II 12% + Taxas
    df['Landed_BRL'] = df['CFR_USD'] * df['USD_BRL'] * 1.12
    
    # 3. Custo Operacional (Com Frete Rodoviário)
    df['Operational_Cost'] = df['Landed_BRL'] + freight_internal
    
    # 4. Preço Líquido (Com Margem Comercial)
    df['Price_Net'] = df['Operational_Cost'] * (1 + (margin_pct / 100))
    
    # 5. Preço Final (Com ICMS 'Por Dentro')
    df['PP_Price'] = df['Price_Net'] / (1 - (icms_pct / 100))
    
    # 6. Tendência (Média Móvel 7 dias)
    df['Trend'] = df['PP_Price'].rolling(window=7).mean()
    
    return df

def get_fair_price_snapshot():
    """Retorna apenas o preço justo de hoje (float) para uso rápido."""
    df = get_market_data(7) # Última semana
    if df.empty: return 0.0
    
    # Parâmetros Padrão de Mercado SP
    df_calc = calculate_cost_buildup(
        df, 
        ocean_freight=60, 
        freight_internal=0.15, 
        icms_pct=18, 
        margin_pct=10
    )
    return df_calc['PP_Price'].iloc[-1]

def run_backtest_validation(history_df, uploaded_df, wti_coef, spread, markup):
    """
    Cruza dados históricos com upload do cliente e calcula erro.
    Retorna: DataFrame comparativo, MAPE, RMSE, Mensagem
    """
    if not HAS_SKLEARN:
        return None, None, None, "Biblioteca scikit-learn não instalada."

    # Calcula a curva teórica com os parâmetros do usuário
    history_df['PP_Theoretical'] = ((history_df['WTI'] * wti_coef) + spread) * history_df['USD_BRL'] * markup
    
    # Prepara o DataFrame do Cliente
    try:
        uploaded_df['Data'] = pd.to_datetime(uploaded_df['Data'])
        uploaded_df = uploaded_df.set_index('Data').sort_index()
        
        # Cruzamento (Inner Join)
        comparison = history_df.join(uploaded_df, how='inner').dropna()
        
        if comparison.empty:
            return None, None, None, "Datas não coincidem."
            
        # Cálculo de Erro
        mape = mean_absolute_percentage_error(comparison['Preco'], comparison['PP_Theoretical'])
        rmse = mean_squared_error(comparison['Preco'], comparison['PP_Theoretical'], squared=False)
        
        return comparison, mape, rmse, "Sucesso"
        
    except Exception as e:
        return None, None, None, f"Erro nos dados: {str(e)}"