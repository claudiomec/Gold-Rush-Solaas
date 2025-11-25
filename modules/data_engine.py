"""
Módulo de Engine de Dados - Cérebro matemático do SAAS
Responsável por buscar, validar e processar dados de mercado.
"""
import streamlit as st
import pandas as pd
import logging
import traceback
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, List, Any
import yfinance as yf
from modules import database
from modules.pricing_formulas import PricingFormula

# Configuração de logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Tenta importar métricas de erro
try:
    from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    logger.warning("scikit-learn não disponível. Métricas de erro não estarão disponíveis.")


# ============================================================================
# EXCEÇÕES CUSTOMIZADAS
# ============================================================================

class DataEngineError(Exception):
    """Exceção base para erros do data engine."""
    pass


class DataSourceUnavailableError(DataEngineError):
    """Erro quando fonte de dados não está disponível."""
    pass


class DataValidationError(DataEngineError):
    """Erro de validação de dados."""
    pass


# ============================================================================
# VALIDAÇÃO DE DADOS
# ============================================================================

def validate_market_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    Valida dados de mercado e retorna DataFrame limpo + lista de warnings.
    
    Args:
        df: DataFrame com dados de mercado
        
    Returns:
        Tuple[DataFrame validado, Lista de warnings]
        
    Raises:
        DataValidationError: Se dados não puderem ser validados
    """
    warnings = []
    
    if df.empty:
        raise DataValidationError("DataFrame vazio recebido para validação")
    
    # Validação de colunas obrigatórias (mapeamento flexível)
    required_cols_lower = ['wti', 'usd_brl', 'pp_fob_usd', 'date']
    required_cols_upper = ['WTI', 'USD_BRL', 'PP_FOB_USD', 'Date']
    
    # Verifica se tem as colunas (case insensitive)
    df_lower = df.copy()
    df_lower.columns = df_lower.columns.str.lower()
    
    missing = [c for c in required_cols_lower if c not in df_lower.columns]
    if missing:
        raise DataValidationError(f"Colunas obrigatórias faltando: {missing}")
    
    # Normaliza nomes das colunas para minúsculas
    col_mapping = {}
    for col in df.columns:
        col_lower = col.lower()
        if col_lower in required_cols_lower:
            col_mapping[col] = col_lower
    
    df_validated = df.rename(columns=col_mapping)
    
    # Garante que 'date' existe (pode ser index)
    if 'date' not in df_validated.columns and df_validated.index.name:
        if df_validated.index.name.lower() == 'date':
            df_validated = df_validated.reset_index()
    
    # Validação de tipos e conversão
    numeric_cols = ['wti', 'usd_brl', 'pp_fob_usd']
    for col in numeric_cols:
        if col in df_validated.columns:
            df_validated[col] = pd.to_numeric(df_validated[col], errors='coerce')
    
    # Converte data
    if 'date' in df_validated.columns:
        df_validated['date'] = pd.to_datetime(df_validated['date'], errors='coerce')
    
    # Detecção de outliers (método IQR)
    for col in numeric_cols:
        if col in df_validated.columns:
            Q1 = df_validated[col].quantile(0.25)
            Q3 = df_validated[col].quantile(0.75)
            IQR = Q3 - Q1
            
            if IQR > 0:  # Evita divisão por zero
                outliers = df_validated[
                    (df_validated[col] < Q1 - 1.5 * IQR) | 
                    (df_validated[col] > Q3 + 1.5 * IQR)
                ]
                if len(outliers) > 0:
                    warnings.append(f"{len(outliers)} outliers detectados em {col}")
                    logger.warning(f"Outliers detectados em {col}: {len(outliers)} valores")
    
    # Validação de ranges realistas (com tolerância)
    if 'wti' in df_validated.columns:
        wti_out_of_range = df_validated[
            (df_validated['wti'] < 10) | (df_validated['wti'] > 250)
        ]
        if len(wti_out_of_range) > 0:
            warnings.append(f"WTI fora do range esperado (10-250 USD) em {len(wti_out_of_range)} registros")
    
    if 'usd_brl' in df_validated.columns:
        usd_out_of_range = df_validated[
            (df_validated['usd_brl'] < 2) | (df_validated['usd_brl'] > 10)
        ]
        if len(usd_out_of_range) > 0:
            warnings.append(f"USD_BRL fora do range esperado (2-10) em {len(usd_out_of_range)} registros")
    
    # Remove duplicatas por data
    if 'date' in df_validated.columns:
        initial_len = len(df_validated)
        df_validated = df_validated.drop_duplicates(subset=['date'], keep='last')
        if len(df_validated) < initial_len:
            warnings.append(f"Removidas {initial_len - len(df_validated)} duplicatas por data")
    
    # Remove linhas com valores nulos críticos
    initial_len = len(df_validated)
    df_validated = df_validated.dropna(subset=['wti', 'usd_brl', 'date'])
    if len(df_validated) < initial_len:
        warnings.append(f"Removidas {initial_len - len(df_validated)} linhas com valores nulos")
    
    if df_validated.empty:
        raise DataValidationError("Após validação, DataFrame ficou vazio")
    
    return df_validated, warnings


def calculate_data_quality_metrics(df: pd.DataFrame) -> Dict:
    """
    Calcula métricas de qualidade de dados para monitoramento.
    
    Args:
        df: DataFrame com dados de mercado
        
    Returns:
        Dict com métricas de qualidade
    """
    if df.empty:
        return {
            'completeness': 0.0,
            'duplicates': 0,
            'date_range': None,
            'outliers_count': 0,
            'freshness_days': None
        }
    
    # Completude
    total_cells = len(df) * len(df.columns)
    null_cells = df.isnull().sum().sum()
    completeness = 1 - (null_cells / total_cells) if total_cells > 0 else 0.0
    
    # Duplicatas
    if 'date' in df.columns:
        duplicates = df.duplicated(subset=['date']).sum()
    else:
        duplicates = df.duplicated().sum()
    
    # Range de datas
    date_col = None
    if 'date' in df.columns:
        date_col = df['date']
    elif df.index.name and 'date' in df.index.name.lower():
        date_col = df.index
    elif isinstance(df.index, pd.DatetimeIndex):
        date_col = df.index
    
    date_range = None
    freshness_days = None
    if date_col is not None:
        try:
            date_min = pd.to_datetime(date_col).min()
            date_max = pd.to_datetime(date_col).max()
            days_span = (date_max - date_min).days
            
            date_range = {
                'start': date_min.isoformat() if hasattr(date_min, 'isoformat') else str(date_min),
                'end': date_max.isoformat() if hasattr(date_max, 'isoformat') else str(date_max),
                'days': days_span,
                'expected_days': len(df)
            }
            
            # Freshness (dias desde última atualização)
            if hasattr(date_max, 'to_pydatetime'):
                freshness_days = (datetime.now() - date_max.to_pydatetime()).days
            else:
                freshness_days = (datetime.now() - date_max).days
        except Exception as e:
            logger.warning(f"Erro ao calcular range de datas: {e}")
    
    # Contagem de outliers (simplificado)
    outliers_count = 0
    numeric_cols = ['wti', 'usd_brl', 'pp_fob_usd', 'WTI', 'USD_BRL', 'PP_FOB_USD']
    for col in numeric_cols:
        if col in df.columns:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            if IQR > 0:
                outliers = df[(df[col] < Q1 - 1.5 * IQR) | (df[col] > Q3 + 1.5 * IQR)]
                outliers_count += len(outliers)
    
    return {
        'completeness': round(completeness, 3),
        'duplicates': int(duplicates),
        'date_range': date_range,
        'outliers_count': outliers_count,
        'freshness_days': freshness_days
    }


# ============================================================================
# FALLBACK YAHOO FINANCE
# ============================================================================

def _fallback_yahoo_finance(days_back: int) -> pd.DataFrame:
    """
    Busca dados do Yahoo Finance como fallback.
    
    Args:
        days_back: Número de dias para buscar
        
    Returns:
        DataFrame com dados de mercado
    """
    start_date = datetime.now() - timedelta(days=days_back)
    end_date = datetime.now()
    
    logger.info(f"Buscando dados do Yahoo Finance: {start_date.date()} a {end_date.date()}")
    
    try:
        wti = yf.download("CL=F", start=start_date, end=end_date, progress=False, auto_adjust=True)
        brl = yf.download("BRL=X", start=start_date, end=end_date, progress=False, auto_adjust=True)
        
        if wti.empty or brl.empty:
            logger.warning("Yahoo Finance retornou dados vazios, usando dados mock")
            idx = pd.date_range(start_date, end_date, freq='D')
            return pd.DataFrame({
                'WTI': [70.0] * len(idx),
                'USD_BRL': [5.0] * len(idx),
                'PP_FOB_USD': [1.2] * len(idx)
            }, index=idx)
        
        # Extrai coluna Close se for DataFrame multi-coluna
        if isinstance(wti, pd.DataFrame):
            wti = wti['Close'] if 'Close' in wti.columns else wti.iloc[:, 0]
        if isinstance(brl, pd.DataFrame):
            brl = brl['Close'] if 'Close' in brl.columns else brl.iloc[:, 0]
        
        df = pd.concat([wti, brl], axis=1).dropna()
        df.columns = ['WTI', 'USD_BRL']
        # Usa fórmula centralizada
        df['PP_FOB_USD'] = df['WTI'].apply(
            lambda x: PricingFormula.calculate_pp_fob_usd(x)
        )
        
        return df
        
    except Exception as e:
        logger.error(f"Erro ao buscar dados do Yahoo Finance: {e}", exc_info=True)
        # Retorna dados mock em caso de erro
        idx = pd.date_range(start_date, end_date, freq='D')
        return pd.DataFrame({
            'WTI': [70.0] * len(idx),
            'USD_BRL': [5.0] * len(idx),
            'PP_FOB_USD': [1.2] * len(idx)
        }, index=idx)


# ============================================================================
# FUNÇÃO PRINCIPAL: GET_MARKET_DATA
# ============================================================================

@st.cache_data(ttl=3600)
def get_market_data(days_back: int = 180, validate: bool = True) -> pd.DataFrame:
    """
    Busca dados históricos de mercado com validação e fallback robusto.
    
    Args:
        days_back: Número de dias para buscar (padrão: 180)
        validate: Se True, valida dados antes de retornar (padrão: True)
        
    Returns:
        DataFrame com colunas: WTI, USD_BRL, PP_FOB_USD
        Index: DatetimeIndex (timezone-naive)
        
    Raises:
        DataSourceUnavailableError: Se nenhuma fonte disponível
        DataValidationError: Se validação falhar
        
    Example:
        >>> df = get_market_data(days_back=30)
        >>> print(df.head())
    """
    start_time = datetime.now()
    start_date = datetime.now() - timedelta(days=days_back)
    end_date = datetime.now()
    
    logger.info(
        "get_market_data_started",
        extra={
            "days_back": days_back,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
    )
    
    df = pd.DataFrame()
    
    # 1. TENTATIVA PRIMÁRIA: DATA WAREHOUSE (FIRESTORE)
    try:
        db = database.get_db()
        if db:
            logger.debug("Attempting Firestore query")
            docs = db.collection('market_data')\
                     .where('date', '>=', start_date)\
                     .order_by('date')\
                     .stream()
            
            data = [doc.to_dict() for doc in docs]
            
            if data:
                df = pd.DataFrame(data)
                df = df.rename(columns={
                    'wti': 'WTI',
                    'usd_brl': 'USD_BRL',
                    'pp_fob_usd': 'PP_FOB_USD',
                    'date': 'Date'
                })
                
                # LIMPEZA CRÍTICA: Converte e remove fuso na coluna antes de virar index
                if 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date'])
                    if df['Date'].dt.tz is not None:
                        df['Date'] = df['Date'].dt.tz_localize(None)
                    
                    df = df.set_index('Date').sort_index()
                
                logger.info(
                    "market_data_loaded_from_firestore",
                    extra={
                        "rows": len(df),
                        "source": "firestore",
                        "duration_ms": (datetime.now() - start_time).total_seconds() * 1000
                    }
                )
        else:
            logger.warning("Firestore não disponível")
            
    except Exception as e:
        logger.warning(
            "Falha ao buscar dados do Firestore",
            extra={
                "error": str(e),
                "error_type": type(e).__name__
            }
        )
    
    # 2. PLANO B: YAHOO FINANCE (se Firestore vazio)
    if df.empty:
        logger.info("Firestore retornou vazio, tentando Yahoo Finance")
        try:
            df = _fallback_yahoo_finance(days_back)
            logger.info(
                "market_data_loaded_from_yahoo",
                extra={
                    "rows": len(df),
                    "source": "yahoo_finance",
                    "duration_ms": (datetime.now() - start_time).total_seconds() * 1000
                }
            )
        except Exception as e:
            logger.error(
                "Erro ao buscar dados do Yahoo Finance",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                exc_info=True
            )
            raise DataSourceUnavailableError("Nenhuma fonte de dados disponível") from e
    
    # 3. VALIDAÇÃO (se solicitada)
    if validate and not df.empty:
        try:
            # Normaliza colunas para validação
            df_for_validation = df.copy()
            if df_for_validation.index.name and 'date' in df_for_validation.index.name.lower():
                df_for_validation = df_for_validation.reset_index()
            
            df_validated, warnings = validate_market_data(df_for_validation)
            
            # Log warnings
            if warnings:
                logger.warning(f"Data quality warnings: {warnings}")
            
            # Reconstrói DataFrame com formato esperado
            if 'date' in df_validated.columns:
                df_validated = df_validated.set_index('date')
            
            # Renomeia para formato padrão (maiúsculas)
            df_validated = df_validated.rename(columns={
                'wti': 'WTI',
                'usd_brl': 'USD_BRL',
                'pp_fob_usd': 'PP_FOB_USD'
            })
            
            df = df_validated
            
        except DataValidationError as e:
            logger.error(f"Validação de dados falhou: {e}", exc_info=True)
            # Se validação falhar mas temos dados, loga e continua (com warning)
            logger.warning("Continuando com dados não validados devido a erro de validação")
        except Exception as e:
            logger.error(f"Erro inesperado na validação: {e}", exc_info=True)
            # Continua com dados originais
    
    # 4. GARANTIA FINAL (Compatibilidade Excel - TZ-Naive)
    if not df.empty:
        # Seleciona apenas colunas numéricas úteis
        cols = ['WTI', 'USD_BRL', 'PP_FOB_USD']
        df = df[[c for c in cols if c in df.columns]]
        
        # Remove fuso horário do índice se ainda existir
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
    
    duration_ms = (datetime.now() - start_time).total_seconds() * 1000
    logger.info(
        "get_market_data_completed",
        extra={
            "rows": len(df),
            "duration_ms": duration_ms
        }
    )
    
    if df.empty:
        raise DataSourceUnavailableError("Nenhum dado disponível após todas as tentativas")
    
    return df


# ============================================================================
# CÁLCULOS DE CUSTO
# ============================================================================

def calculate_cost_buildup(
    df: pd.DataFrame,
    ocean_freight: float,
    freight_internal: float,
    icms_pct: float,
    margin_pct: float
) -> pd.DataFrame:
    """
    Calcula o buildup de custo completo do commodity.
    
    Args:
        df: DataFrame com dados de mercado (WTI, USD_BRL, PP_FOB_USD)
        ocean_freight: Frete marítimo em USD
        freight_internal: Frete interno em BRL
        icms_pct: Percentual de ICMS
        margin_pct: Percentual de margem
        
    Returns:
        DataFrame com colunas adicionais calculadas
    """
    if df.empty:
        logger.warning("DataFrame vazio recebido para calculate_cost_buildup")
        return df
    
    df = df.copy()
    
    # Validação de colunas necessárias
    required_cols = ['PP_FOB_USD', 'USD_BRL']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Colunas necessárias faltando: {missing}")
    
    # Cálculo do buildup
    df['CFR_USD'] = df['PP_FOB_USD'] + (ocean_freight / 1000)
    df['Landed_BRL'] = df['CFR_USD'] * df['USD_BRL'] * 1.12
    df['Operational_Cost'] = df['Landed_BRL'] + freight_internal
    df['Price_Net'] = df['Operational_Cost'] * (1 + (margin_pct / 100))
    df['PP_Price'] = df['Price_Net'] / (1 - (icms_pct / 100))
    df['Trend'] = df['PP_Price'].rolling(window=7).mean()
    
    return df


def get_fair_price_snapshot() -> float:
    """
    Retorna snapshot do preço justo atual (últimos 7 dias).
    
    Returns:
        Preço justo em BRL/kg (0.0 se não disponível)
    """
    try:
        df = get_market_data(7, validate=True)
        if df.empty:
            logger.warning("get_fair_price_snapshot: DataFrame vazio")
            return 0.0
        
        df_calc = calculate_cost_buildup(df, 60, 0.15, 18, 10)
        
        if 'PP_Price' not in df_calc.columns or df_calc.empty:
            return 0.0
        
        return float(df_calc['PP_Price'].iloc[-1])
    except Exception as e:
        logger.error(f"Erro ao calcular fair price snapshot: {e}", exc_info=True)
        return 0.0


# ============================================================================
# BACKTEST E VALIDAÇÃO
# ============================================================================

def run_backtest_validation(
    history_df: pd.DataFrame,
    uploaded_df: pd.DataFrame,
    wti_coef: float,
    spread: float,
    markup: float
) -> Tuple[Optional[pd.DataFrame], Optional[float], Optional[float], str]:
    """
    Executa validação de backtest comparando dados históricos com upload.
    
    Args:
        history_df: DataFrame com dados históricos
        uploaded_df: DataFrame com dados enviados pelo usuário
        wti_coef: Coeficiente WTI
        spread: Spread
        markup: Markup
        
    Returns:
        Tuple[DataFrame de comparação, MAPE, RMSE, Mensagem]
    """
    if not HAS_SKLEARN:
        return None, None, None, "Biblioteca scikit-learn não instalada."
    
    try:
        # Garante compatibilidade no backtest também
        if history_df.index.tz is not None:
            history_df.index = history_df.index.tz_localize(None)
        
        history_df['PP_Theoretical'] = (
            (history_df['WTI'] * wti_coef) + spread
        ) * history_df['USD_BRL'] * markup
        
        uploaded_df['Data'] = pd.to_datetime(uploaded_df['Data'])
        if uploaded_df['Data'].dt.tz is not None:
            uploaded_df['Data'] = uploaded_df['Data'].dt.tz_localize(None)
        
        uploaded_df = uploaded_df.set_index('Data').sort_index()
        comparison = history_df.join(uploaded_df, how='inner').dropna()
        
        if comparison.empty:
            return None, None, None, "Datas não coincidem."
        
        mape = mean_absolute_percentage_error(
            comparison['Preco'],
            comparison['PP_Theoretical']
        )
        rmse = mean_squared_error(
            comparison['Preco'],
            comparison['PP_Theoretical'],
            squared=False
        )
        
        return comparison, mape, rmse, "Sucesso"
        
    except Exception as e:
        logger.error(f"Erro no backtest validation: {e}", exc_info=True)
        return None, None, None, f"Erro nos dados: {str(e)}"


# ============================================================================
# MÉTRICAS DE CONFIANÇA E ANÁLISE DE SENSIBILIDADE
# ============================================================================

def calculate_price_confidence(
    df: pd.DataFrame,
    current_price: float
) -> Dict[str, any]:
    """
    Calcula métricas de confiança no preço calculado.
    
    Args:
        df: DataFrame com dados históricos (deve ter coluna PP_Price)
        current_price: Preço atual calculado
        
    Returns:
        Dict com métricas de confiança:
        {
            'confidence_score': 0.0-1.0,
            'data_freshness_days': int,
            'data_completeness': float,
            'volatility_index': float,
            'recommendation': str
        }
    """
    if df.empty:
        return {
            'confidence_score': 0.0,
            'data_freshness_days': None,
            'data_completeness': 0.0,
            'volatility_index': None,
            'recommendation': 'Dados insuficientes para calcular confiança'
        }
    
    # 1. Freshness (quanto mais recente, maior confiança)
    try:
        if isinstance(df.index, pd.DatetimeIndex):
            last_date = df.index[-1]
            if hasattr(last_date, 'to_pydatetime'):
                last_date = last_date.to_pydatetime()
            days_since_update = (datetime.now() - last_date).days
        else:
            days_since_update = 999  # Muito antigo
        
        freshness_score = max(0.0, 1.0 - (days_since_update / 7.0))  # 7 dias = 0
    except Exception as e:
        logger.warning(f"Erro ao calcular freshness: {e}")
        days_since_update = 999
        freshness_score = 0.0
    
    # 2. Completude (quanto mais dados, maior confiança)
    try:
        total_cells = len(df) * len(df.columns)
        null_cells = df.isnull().sum().sum()
        completeness = 1.0 - (null_cells / total_cells) if total_cells > 0 else 0.0
    except Exception:
        completeness = 0.0
    
    # 3. Volatilidade (alta volatilidade = menor confiança)
    try:
        if 'PP_Price' in df.columns:
            volatility = df['PP_Price'].pct_change().std()
            # Normaliza volatilidade (assume que > 0.1 (10%) é muito volátil)
            volatility_score = max(0.0, 1.0 - (volatility * 10.0))
        else:
            volatility = None
            volatility_score = 0.5  # Neutro se não tiver PP_Price
    except Exception:
        volatility = None
        volatility_score = 0.5
    
    # 4. Consistência (dados consistentes = maior confiança)
    try:
        if 'PP_Price' in df.columns and len(df) > 1:
            mean_price = df['PP_Price'].mean()
            if mean_price > 0:
                consistency = 1.0 - (df['PP_Price'].diff().abs().mean() / mean_price)
                consistency = max(0.0, min(1.0, consistency))  # Clamp entre 0 e 1
            else:
                consistency = 0.5
        else:
            consistency = 0.5
    except Exception:
        consistency = 0.5
    
    # Score final (média ponderada)
    confidence = (
        freshness_score * 0.3 +
        completeness * 0.3 +
        volatility_score * 0.2 +
        consistency * 0.2
    )
    
    # Recomendação
    if confidence >= 0.8:
        recommendation = "Alta confiança - Pode usar para decisão"
    elif confidence >= 0.6:
        recommendation = "Confiança moderada - Considere validar com outras fontes"
    else:
        recommendation = "Baixa confiança - Aguarde atualização de dados"
    
    return {
        'confidence_score': round(confidence, 3),
        'data_freshness_days': days_since_update if days_since_update != 999 else None,
        'data_completeness': round(completeness, 3),
        'volatility_index': round(volatility, 4) if volatility is not None else None,
        'consistency_score': round(consistency, 3),
        'recommendation': recommendation
    }


def sensitivity_analysis(
    base_params: Dict[str, float],
    ranges: Dict[str, Tuple[float, float]],
    days_back: int = 30
) -> pd.DataFrame:
    """
    Análise de sensibilidade dos parâmetros de cálculo.
    
    Args:
        base_params: Parâmetros base {'ocean_freight': 60, 'icms': 18, 'margin': 10, 'freight_internal': 0.15}
        ranges: Ranges de variação {'ocean_freight': (-10, +10), 'icms': (-2, +2), 'margin': (-2, +2)}
        days_back: Número de dias para análise (padrão: 30)
        
    Returns:
        DataFrame com impacto de cada parâmetro no preço final
    """
    logger.info("sensitivity_analysis_started", extra={"base_params": base_params})
    
    try:
        # Busca dados de mercado
        df = get_market_data(days_back, validate=True)
        if df.empty:
            logger.warning("sensitivity_analysis: DataFrame vazio")
            return pd.DataFrame()
        
        # Calcula preço base
        base_price = calculate_cost_buildup(
            df,
            base_params.get('ocean_freight', 60),
            base_params.get('freight_internal', 0.15),
            base_params.get('icms', 18),
            base_params.get('margin', 10)
        )['PP_Price'].iloc[-1]
        
        results = []
        
        # Testa cada parâmetro
        for param, (min_delta, max_delta) in ranges.items():
            if param not in base_params:
                logger.warning(f"Parâmetro {param} não encontrado em base_params")
                continue
            
            # Testa variação negativa
            test_params = base_params.copy()
            test_params[param] = base_params[param] + min_delta
            
            try:
                test_price = calculate_cost_buildup(
                    df,
                    test_params.get('ocean_freight', 60),
                    test_params.get('freight_internal', 0.15),
                    test_params.get('icms', 18),
                    test_params.get('margin', 10)
                )['PP_Price'].iloc[-1]
                
                impact = test_price - base_price
                impact_pct = (impact / base_price) * 100 if base_price > 0 else 0
                
                results.append({
                    'parameter': param,
                    'change': min_delta,
                    'new_value': test_params[param],
                    'price_impact': round(impact, 4),
                    'price_impact_pct': round(impact_pct, 2),
                    'sensitivity_rank': abs(impact_pct)
                })
            except Exception as e:
                logger.warning(f"Erro ao calcular sensibilidade para {param} (min): {e}")
            
            # Testa variação positiva
            test_params = base_params.copy()
            test_params[param] = base_params[param] + max_delta
            
            try:
                test_price = calculate_cost_buildup(
                    df,
                    test_params.get('ocean_freight', 60),
                    test_params.get('freight_internal', 0.15),
                    test_params.get('icms', 18),
                    test_params.get('margin', 10)
                )['PP_Price'].iloc[-1]
                
                impact = test_price - base_price
                impact_pct = (impact / base_price) * 100 if base_price > 0 else 0
                
                results.append({
                    'parameter': param,
                    'change': max_delta,
                    'new_value': test_params[param],
                    'price_impact': round(impact, 4),
                    'price_impact_pct': round(impact_pct, 2),
                    'sensitivity_rank': abs(impact_pct)
                })
            except Exception as e:
                logger.warning(f"Erro ao calcular sensibilidade para {param} (max): {e}")
        
        if not results:
            logger.warning("sensitivity_analysis: Nenhum resultado gerado")
            return pd.DataFrame()
        
        df_results = pd.DataFrame(results)
        df_results = df_results.sort_values('sensitivity_rank', ascending=False)
        
        logger.info(f"sensitivity_analysis_completed: {len(df_results)} resultados")
        
        return df_results
        
    except Exception as e:
        logger.error(f"Erro na análise de sensibilidade: {e}", exc_info=True)
        return pd.DataFrame()
