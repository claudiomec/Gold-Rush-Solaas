"""
Módulo de Filtros e Busca - Funcionalidades de filtragem avançada
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

def render_data_filters(df, date_column='Date'):
    """
    Renderiza filtros avançados para dataframes.
    
    Args:
        df: DataFrame para filtrar
        date_column: Nome da coluna de data
        
    Returns:
        DataFrame filtrado
    """
    st.markdown("### 🔍 Filtros e Busca")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Filtro de data
        if date_column in df.columns or df.index.name == date_column or isinstance(df.index, pd.DatetimeIndex):
            date_range = st.date_input(
                "📅 Período",
                value=(df.index.min() if isinstance(df.index, pd.DatetimeIndex) else datetime.now() - timedelta(days=30),
                       df.index.max() if isinstance(df.index, pd.DatetimeIndex) else datetime.now()),
                key="date_filter"
            )
            
            if len(date_range) == 2:
                start_date, end_date = date_range
                if isinstance(df.index, pd.DatetimeIndex):
                    df = df[(df.index >= pd.Timestamp(start_date)) & (df.index <= pd.Timestamp(end_date))]
    
    with col2:
        # Busca por texto (se houver colunas de texto)
        text_columns = df.select_dtypes(include=['object']).columns.tolist()
        if text_columns:
            search_term = st.text_input("🔎 Buscar", key="text_search", placeholder="Digite para buscar...")
            if search_term:
                mask = pd.Series([False] * len(df))
                for col in text_columns:
                    mask |= df[col].astype(str).str.contains(search_term, case=False, na=False)
                df = df[mask]
    
    with col3:
        # Filtro por valor numérico
        numeric_columns = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
        if numeric_columns:
            selected_col = st.selectbox("📊 Coluna Numérica", [""] + numeric_columns, key="numeric_col")
            if selected_col:
                min_val = float(df[selected_col].min())
                max_val = float(df[selected_col].max())
                value_range = st.slider(
                    f"Valor ({selected_col})",
                    min_value=min_val,
                    max_value=max_val,
                    value=(min_val, max_val),
                    key=f"value_filter_{selected_col}"
                )
                df = df[(df[selected_col] >= value_range[0]) & (df[selected_col] <= value_range[1])]
    
    return df

def render_quick_filters():
    """Renderiza filtros rápidos na sidebar."""
    st.markdown("### ⚡ Filtros Rápidos")
    
    # Filtro de período
    period = st.selectbox(
        "📅 Período",
        ["Últimos 7 dias", "Últimos 30 dias", "Últimos 90 dias", "Últimos 180 dias", "Último ano", "Todo o período"],
        key="quick_period"
    )
    
    # Filtro de tendência
    trend = st.selectbox(
        "📈 Tendência",
        ["Todas", "Alta", "Baixa", "Estável"],
        key="quick_trend"
    )
    
    return period, trend

def apply_quick_filters(df, period, trend):
    """Aplica filtros rápidos ao dataframe."""
    # Filtro de período
    if period == "Últimos 7 dias":
        days = 7
    elif period == "Últimos 30 dias":
        days = 30
    elif period == "Últimos 90 dias":
        days = 90
    elif period == "Últimos 180 dias":
        days = 180
    elif period == "Último ano":
        days = 365
    else:
        days = None
    
    if days and isinstance(df.index, pd.DatetimeIndex):
        cutoff_date = df.index.max() - timedelta(days=days)
        df = df[df.index >= cutoff_date]
    
    # Filtro de tendência (se houver coluna de variação)
    if trend != "Todas" and 'PP_Price' in df.columns and len(df) > 1:
        df = df.copy()
        df['Change'] = df['PP_Price'].pct_change() * 100
        
        if trend == "Alta":
            df = df[df['Change'] > 0.5]
        elif trend == "Baixa":
            df = df[df['Change'] < -0.5]
        elif trend == "Estável":
            df = df[(df['Change'] >= -0.5) & (df['Change'] <= 0.5)]
    
    return df

def render_search_bar(placeholder="Buscar..."):
    """Renderiza uma barra de busca simples."""
    return st.text_input("🔍", placeholder=placeholder, key="global_search")


