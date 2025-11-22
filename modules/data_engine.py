import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf
from modules import database

# Tenta importar métricas de erro
try:
    from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

@st.cache_data(ttl=3600)
def get_market_data(days_back=180):
    """
    Busca dados históricos e garante formato compatível com Excel (TZ-Naive).
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    df = pd.DataFrame()

    # 1. TENTATIVA PRIMÁRIA: DATA WAREHOUSE (FIRESTORE)
    try:
        db = database.get_db()
        if db:
            docs = db.collection('market_data')\
                     .where('date', '>=', start_date)\
                     .order_by('date')\
                     .stream()
            
            data = [doc.to_dict() for doc in docs]
            
            if data:
                df = pd.DataFrame(data)
                df = df.rename(columns={'wti': 'WTI', 'usd_brl': 'USD_BRL', 'pp_fob_usd': 'PP_FOB_USD', 'date': 'Date'})
                
                # LIMPEZA CRÍTICA 1: Converte e remove fuso na coluna antes de virar index
                df['Date'] = pd.to_datetime(df['Date'])
                if df['Date'].dt.tz is not None:
                    df['Date'] = df['Date'].dt.tz_localize(None)
                
                df = df.set_index('Date').sort_index()

    except Exception as e:
        print(f"⚠️ Falha no DB: {e}")

    # 2. PLANO B: YAHOO FINANCE
    if df.empty:
        wti = yf.download("CL=F", start=start_date, end=end_date, progress=False, auto_adjust=True)['Close']
        brl = yf.download("BRL=X", start=start_date, end=end_date, progress=False, auto_adjust=True)['Close']
        
        if wti.empty or brl.empty:
            idx = pd.date_range(start_date, end_date)
            return pd.DataFrame({'WTI': [70.0]*len(idx), 'USD_BRL': [5.0]*len(idx), 'PP_FOB_USD': [1.2]*len(idx)}, index=idx)

        df = pd.concat([wti, brl], axis=1).dropna()
        df.columns = ['WTI', 'USD_BRL']
        df['PP_FOB_USD'] = (df['WTI'] * 0.014) + 0.35

    # --- GARANTIA FINAL (A "Vacina" do Excel) ---
    if not df.empty:
        # Seleciona apenas colunas numéricas úteis
        cols = ['WTI', 'USD_BRL', 'PP_FOB_USD']
        df = df[[c for c in cols if c in df.columns]]
        
        # Remove fuso horário do índice se ainda existir
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
            
    return df

def calculate_cost_buildup(df, ocean_freight, freight_internal, icms_pct, margin_pct):
    df = df.copy()
    df['CFR_USD'] = df['PP_FOB_USD'] + (ocean_freight / 1000)
    df['Landed_BRL'] = df['CFR_USD'] * df['USD_BRL'] * 1.12
    df['Operational_Cost'] = df['Landed_BRL'] + freight_internal
    df['Price_Net'] = df['Operational_Cost'] * (1 + (margin_pct / 100))
    df['PP_Price'] = df['Price_Net'] / (1 - (icms_pct / 100))
    df['Trend'] = df['PP_Price'].rolling(window=7).mean()
    return df

def get_fair_price_snapshot():
    df = get_market_data(7)
    if df.empty: return 0.0
    df_calc = calculate_cost_buildup(df, 60, 0.15, 18, 10)
    return df_calc['PP_Price'].iloc[-1]

def run_backtest_validation(history_df, uploaded_df, wti_coef, spread, markup):
    if not HAS_SKLEARN: return None, None, None, "Biblioteca scikit-learn não instalada."

    # Garante compatibilidade no backtest também
    if history_df.index.tz is not None:
        history_df.index = history_df.index.tz_localize(None)

    history_df['PP_Theoretical'] = ((history_df['WTI'] * wti_coef) + spread) * history_df['USD_BRL'] * markup
    
    try:
        uploaded_df['Data'] = pd.to_datetime(uploaded_df['Data'])
        if uploaded_df['Data'].dt.tz is not None:
            uploaded_df['Data'] = uploaded_df['Data'].dt.tz_localize(None)
            
        uploaded_df = uploaded_df.set_index('Data').sort_index()
        comparison = history_df.join(uploaded_df, how='inner').dropna()
        
        if comparison.empty: return None, None, None, "Datas não coincidem."
            
        mape = mean_absolute_percentage_error(comparison['Preco'], comparison['PP_Theoretical'])
        rmse = mean_squared_error(comparison['Preco'], comparison['PP_Theoretical'], squared=False)
        return comparison, mape, rmse, "Sucesso"
    except Exception as e: return None, None, None, f"Erro nos dados: {str(e)}"