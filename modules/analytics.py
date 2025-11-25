"""
Módulo de Analytics - Coleta e cálculo de métricas de uso e valor
"""
import streamlit as st
from datetime import datetime, timedelta
from modules.database import get_db
from modules.data_engine import get_market_data, calculate_cost_buildup
import pandas as pd

def get_user_metrics(user_id=None):
    """
    Retorna métricas do usuário atual ou de um usuário específico.
    
    Args:
        user_id: ID do usuário (None para usuário atual)
        
    Returns:
        dict com métricas do usuário
    """
    db = get_db()
    if not db:
        return {}
    
    try:
        # Se não especificado, pega do session state
        if user_id is None:
            user_id = st.session_state.get('user_name')
        
        if not user_id:
            return {}
        
        # Busca histórico de acessos (se existir)
        # Por enquanto, retorna métricas básicas calculadas
        df = get_market_data(180)  # Últimos 180 dias
        
        if df.empty:
            return {}
        
        # Calcula métricas básicas
        latest_price = df['PP_Price'].iloc[-1] if 'PP_Price' in df.columns else 0
        oldest_price = df['PP_Price'].iloc[0] if len(df) > 0 else 0
        
        total_change = ((latest_price / oldest_price - 1) * 100) if oldest_price > 0 else 0
        
        # Calcula economia potencial (exemplo)
        avg_price = df['PP_Price'].mean() if 'PP_Price' in df.columns else 0
        current_price = latest_price
        
        return {
            'total_days_tracked': len(df),
            'current_price': current_price,
            'average_price': avg_price,
            'price_change_pct': total_change,
            'price_change_abs': latest_price - oldest_price,
            'last_update': df.index[-1] if len(df) > 0 else None,
            'data_points': len(df)
        }
    except Exception as e:
        print(f"Erro ao calcular métricas: {e}")
        return {}

def calculate_savings_potential(current_price, fair_price, volume_kg=1000):
    """
    Calcula economia potencial baseada na diferença de preço.
    
    Args:
        current_price: Preço atual
        fair_price: Preço justo
        volume_kg: Volume em kg
        
    Returns:
        dict com economia potencial
    """
    if current_price <= 0 or fair_price <= 0:
        return {'savings': 0, 'savings_pct': 0, 'status': 'neutral'}
    
    diff = current_price - fair_price
    savings = abs(diff) * volume_kg
    savings_pct = (abs(diff) / fair_price) * 100
    
    if diff > 0:
        status = 'loss'  # Pagando acima do justo
    elif diff < 0:
        status = 'savings'  # Economizando
    else:
        status = 'neutral'
    
    return {
        'savings': savings,
        'savings_pct': savings_pct,
        'status': status,
        'diff_per_kg': diff
    }

def get_usage_stats(user_id=None):
    """
    Retorna estatísticas de uso do sistema.
    
    Args:
        user_id: ID do usuário
        
    Returns:
        dict com estatísticas
    """
    # Por enquanto retorna dados básicos
    # Futuramente pode rastrear acessos, relatórios gerados, etc.
    return {
        'reports_generated': 0,  # Será implementado com tracking
        'last_access': datetime.now(),
        'total_sessions': 0
    }

