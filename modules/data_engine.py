import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf
# Importamos o módulo de banco de dados local
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
    Busca dados históricos.
    Estratégia: Tenta ler do Firestore (Robô). Se falhar, vai no Yahoo (Fallback).
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    # ---------------------------------------------------------
    # 1. TENTATIVA PRIMÁRIA: DATA WAREHOUSE (FIRESTORE)
    # ---------------------------------------------------------
    try:
        db = database.get_db()
        if db:
            # Busca dados já processados pelo Robô
            docs = db.collection('market_data')\
                     .where('date', '>=', start_date)\
                     .order_by('date')\
                     .stream()
            
            data = []
            for doc in docs:
                data.append(doc.to_dict())
            
            if data:
                df = pd.DataFrame(data)
                
                # Normaliza nomes das colunas
                df = df.rename(columns={
                    'wti': 'WTI',
                    'usd_brl': 'USD_BRL',
                    'pp_fob_usd': 'PP_FOB_USD',
                    'date': 'Date'
                })
                
                # --- CORREÇÃO CRÍTICA PARA EXCEL (TZ-NAIVE) ---
                # Converte para datetime
                df['Date'] = pd.to_datetime(df['Date'])
                
                # Se tiver fuso horário (tz-aware), remove para evitar erro no Excel
                if df['Date'].dt.tz is not None:
                    df['Date'] = df['Date'].dt.tz_localize(None)
                
                df = df.set_index('Date').sort_index()
                
                if not df.empty:
                    return df

    except Exception as e:
        print(f"⚠️ Aviso: Falha ao ler do Banco ({e}). Tentando Yahoo...")

    # ---------------------------------------------------------
    # 2. PLANO B: YAHOO FINANCE (FALLBACK)
    # ---------------------------------------------------------
    
    wti = yf.download("CL=F", start=start_date, end=end_date, progress=False, auto_adjust=True)['Close']
    brl = yf.download("BRL=X", start=start_date, end=end_date, progress=False, auto_adjust=True)['Close']
    
    if wti.empty or brl.empty:
        idx = pd.date_range(start_date, end_date)
        return pd.DataFrame({'WTI': [70.0]*len(idx), 'USD_BRL': [5.0]*len(idx), 'PP_FOB_USD': [1.2]*len(idx)}, index=idx)

    df = pd.concat([wti, brl], axis=1).dropna()
    df.columns = ['WTI', 'USD_BRL']
    
    # --- CORREÇÃO CRÍTICA PARA EXCEL (TZ-NAIVE) ---
    # O Yahoo retorna datas com fuso. Removemos aqui.
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
        
    df['PP_FOB_USD'] = (df['WTI'] * 0.014) + 0.35
    
    return df

def calculate_cost_buildup(df, ocean_freight, freight_internal, icms_pct, margin_pct):
    """Calcula a cascata de custos SP."""
    df = df.copy()
    df['CFR_USD'] = df['PP_FOB_USD'] + (ocean_freight / 1000)
    df['Landed_BRL'] = df['CFR_USD'] * df['USD_BRL'] * 1.12
    df['Operational_Cost'] = df['Landed_BRL'] + freight_internal
    df['Price_Net'] = df['Operational_Cost'] * (1 + (margin_pct / 100))
    df['PP_Price'] = df['Price_Net'] / (1 - (icms_pct / 100))
    df['Trend'] = df['PP_Price'].rolling(window=7).mean()
    return df

def get_fair_price_snapshot():
    """Retorna o preço justo de hoje (snapshot)."""
    df = get_market_data(7)
    if df.empty: return 0.0
    df_calc = calculate_cost_buildup(df, 60, 0.15, 18, 10)
    return df_calc['PP_Price'].iloc[-1]

def run_backtest_validation(history_df, uploaded_df, wti_coef, spread, markup):
    """Validação estatística."""
    if not HAS_SKLEARN:
        return None, None, None, "Biblioteca scikit-learn não instalada."

    history_df['PP_Theoretical'] = ((history_df['WTI'] * wti_coef) + spread) * history_df['USD_BRL'] * markup
    
    try:
        uploaded_df['Data'] = pd.to_datetime(uploaded_df['Data'])
        uploaded_df = uploaded_df.set_index('Data').sort_index()
        comparison = history_df.join(uploaded_df, how='inner').dropna()
        
        if comparison.empty:
            return None, None, None, "Datas não coincidem."
            
        mape = mean_absolute_percentage_error(comparison['Preco'], comparison['PP_Theoretical'])
        rmse = mean_squared_error(comparison['Preco'], comparison['PP_Theoretical'], squared=False)
        
        return comparison, mape, rmse, "Sucesso"
        
    except Exception as e:
        return None, None, None, f"Erro nos dados: {str(e)}"