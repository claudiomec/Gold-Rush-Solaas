# 📊 Revisão Técnica: Módulos data_engine.py e database.py

**Data:** $(date)  
**Revisores:** Senior Business Analyst | Senior Data Engineer | Senior Backend Developer

---

## 🎯 Objetivo

Revisar os módulos considerados o "cérebro matemático" do SAAS e propor melhorias de estado da arte em:
- **Qualidade de Dados** (Data Engineering)
- **Análise de Negócio** (Business Analytics)
- **Arquitetura e Código** (Backend Development)

---

## 📋 SUMÁRIO EXECUTIVO

### Pontos Fortes Identificados
✅ Estrutura modular bem organizada  
✅ Fallback robusto (Firestore → Yahoo Finance → Dados Mock)  
✅ Tratamento de timezone para compatibilidade Excel  
✅ Cache implementado para performance  

### Pontos Críticos de Melhoria
🔴 **CRÍTICO:** Falta de validação de dados e tratamento de outliers  
🔴 **CRÍTICO:** Ausência de logging estruturado e monitoramento  
🔴 **CRÍTICO:** Cálculos hardcoded sem configuração centralizada  
🟡 **ALTO:** Performance: queries Firestore sem otimização  
🟡 **ALTO:** Segurança: tratamento de exceções expõe detalhes  
🟢 **MÉDIO:** Testabilidade: código acoplado ao Streamlit  

---

## 🔍 ANÁLISE DETALHADA POR MÓDULO

---

## 1️⃣ MÓDULO: `data_engine.py`

### 1.1 PERSPECTIVA: Senior Data Engineer

#### 🔴 **CRÍTICO - Qualidade de Dados**

**Problema 1: Ausência de Validação de Dados**
```python
# ATUAL (linha 33-36)
data = [doc.to_dict() for doc in docs]
if data:
    df = pd.DataFrame(data)
```

**Impacto:**
- Dados corrompidos ou faltantes podem quebrar cálculos downstream
- Sem validação de tipos, ranges ou completude
- Outliers não detectados podem distorcer análises

**Sugestão:**
```python
def validate_market_data(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    Valida dados de mercado e retorna DataFrame limpo + lista de warnings.
    
    Returns:
        (df_validated, warnings_list)
    """
    warnings = []
    
    # Validação de colunas obrigatórias
    required_cols = ['wti', 'usd_brl', 'pp_fob_usd', 'date']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Colunas obrigatórias faltando: {missing}")
    
    # Validação de tipos
    df['wti'] = pd.to_numeric(df['wti'], errors='coerce')
    df['usd_brl'] = pd.to_numeric(df['usd_brl'], errors='coerce')
    df['pp_fob_usd'] = pd.to_numeric(df['pp_fob_usd'], errors='coerce')
    
    # Detecção de outliers (IQR method)
    for col in ['wti', 'usd_brl', 'pp_fob_usd']:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        outliers = df[(df[col] < Q1 - 1.5*IQR) | (df[col] > Q3 + 1.5*IQR)]
        if len(outliers) > 0:
            warnings.append(f"{len(outliers)} outliers detectados em {col}")
    
    # Validação de ranges realistas
    if (df['wti'] < 20).any() or (df['wti'] > 200).any():
        warnings.append("WTI fora do range esperado (20-200 USD)")
    
    if (df['usd_brl'] < 3).any() or (df['usd_brl'] > 8).any():
        warnings.append("USD_BRL fora do range esperado (3-8)")
    
    # Remove duplicatas por data
    df = df.drop_duplicates(subset=['date'], keep='last')
    
    # Remove linhas com valores nulos críticos
    df = df.dropna(subset=['wti', 'usd_brl', 'date'])
    
    return df, warnings
```

**Problema 2: Falta de Data Quality Metrics**
- Não há métricas de completude, consistência ou acurácia
- Impossível monitorar degradação de qualidade ao longo do tempo

**Sugestão:**
```python
def calculate_data_quality_metrics(df: pd.DataFrame) -> dict:
    """
    Calcula métricas de qualidade de dados para monitoramento.
    """
    return {
        'completeness': (1 - df.isnull().sum().sum() / (len(df) * len(df.columns))),
        'duplicates': df.duplicated(subset=['date']).sum(),
        'date_range': {
            'start': df['date'].min(),
            'end': df['date'].max(),
            'days': (df['date'].max() - df['date'].min()).days,
            'expected_days': len(df),
            'gaps': detect_date_gaps(df['date'])
        },
        'outliers_count': detect_outliers_count(df),
        'freshness': (datetime.now() - df['date'].max()).days
    }
```

#### 🔴 **CRÍTICO - Performance e Escalabilidade**

**Problema 3: Query Firestore Ineficiente**
```python
# ATUAL (linha 28-31)
docs = db.collection('market_data')\
         .where('date', '>=', start_date)\
         .order_by('date')\
         .stream()
```

**Impacto:**
- Sem índice composto, query pode ser lenta
- Carrega todos os documentos em memória de uma vez
- Sem paginação para grandes volumes

**Sugestão:**
```python
def get_market_data_optimized(days_back=180, batch_size=1000):
    """
    Versão otimizada com paginação e cache inteligente.
    """
    # 1. Verifica cache primeiro (últimos 7 dias sempre em cache)
    cache_key = f"market_data_{days_back}"
    if days_back <= 7:
        cached = st.cache_data(ttl=300).get(cache_key)  # 5 min para dados recentes
        if cached is not None:
            return cached
    
    # 2. Query otimizada com paginação
    db = database.get_db()
    if not db:
        return _fallback_yahoo_finance(days_back)
    
    all_data = []
    query = db.collection('market_data')\
              .where('date', '>=', start_date)\
              .order_by('date')\
              .limit(batch_size)
    
    while True:
        batch = query.stream()
        batch_data = [doc.to_dict() for doc in batch]
        if not batch_data:
            break
        all_data.extend(batch_data)
        
        # Paginação
        last_doc = batch_data[-1]
        query = query.start_after(last_doc['date'])
    
    # 3. Validação e transformação
    df = pd.DataFrame(all_data)
    df_validated, warnings = validate_market_data(df)
    
    # 4. Log warnings (se houver)
    if warnings:
        logger.warning(f"Data quality warnings: {warnings}")
    
    return df_validated
```

**Problema 4: Cache Não Inteligente**
- Cache fixo de 1 hora não considera volatilidade dos dados
- Dados de mercado mudam durante horário comercial vs. não comercial

**Sugestão:**
```python
def get_cache_ttl():
    """
    TTL dinâmico baseado em horário e tipo de dado.
    """
    now = datetime.now()
    hour = now.hour
    
    # Horário comercial (9h-17h): cache menor (5 min)
    if 9 <= hour <= 17:
        return 300
    # Fora do horário: cache maior (1 hora)
    else:
        return 3600
```

#### 🟡 **ALTO - Arquitetura de Dados**

**Problema 5: Cálculo PP_FOB_USD Hardcoded**
```python
# ATUAL (linha 60)
df['PP_FOB_USD'] = (df['WTI'] * 0.014) + 0.35
```

**Impacto:**
- Fórmula pode mudar e está espalhada no código
- Difícil calibrar ou A/B testar diferentes fórmulas
- Sem histórico de versões da fórmula

**Sugestão:**
```python
# Criar módulo de configuração de fórmulas
# modules/pricing_formulas.py

class PricingFormula:
    """Classe para gerenciar fórmulas de precificação."""
    
    VERSION = "1.2"
    
    @staticmethod
    def calculate_pp_fob_usd(wti: float, formula_version: str = None) -> float:
        """
        Calcula PP_FOB_USD baseado em WTI.
        
        Fórmulas disponíveis:
        - v1.0: (WTI * 0.014) + 0.35
        - v1.1: (WTI * 0.0145) + 0.32
        - v1.2: (WTI * 0.014) + 0.35 + (WTI * 0.0001)  # Versão atual
        """
        version = formula_version or PricingFormula.VERSION
        
        if version == "1.0":
            return (wti * 0.014) + 0.35
        elif version == "1.1":
            return (wti * 0.0145) + 0.32
        elif version == "1.2":
            return (wti * 0.014) + 0.35 + (wti * 0.0001)
        else:
            raise ValueError(f"Versão de fórmula inválida: {version}")
    
    @staticmethod
    def get_formula_metadata(version: str) -> dict:
        """Retorna metadados da fórmula (autor, data, validação)."""
        return {
            "1.0": {"author": "Initial", "date": "2024-01-01", "validation": "backtest_2023"},
            "1.1": {"author": "Data Team", "date": "2024-06-01", "validation": "backtest_2024_q1"},
            "1.2": {"author": "Data Team", "date": "2024-12-01", "validation": "backtest_2024_q3"}
        }
```

---

### 1.2 PERSPECTIVA: Senior Business Analyst

#### 🔴 **CRÍTICO - Métricas de Negócio**

**Problema 6: Falta de Métricas de Confiança**
- Não há indicador de confiabilidade dos dados
- Cliente não sabe se pode confiar no preço calculado

**Sugestão:**
```python
def calculate_price_confidence(df: pd.DataFrame, current_price: float) -> dict:
    """
    Calcula métricas de confiança no preço calculado.
    
    Returns:
        {
            'confidence_score': 0.0-1.0,
            'data_freshness_days': int,
            'data_completeness': float,
            'volatility_index': float,
            'recommendation': str
        }
    """
    # 1. Freshness (quanto mais recente, maior confiança)
    days_since_update = (datetime.now() - df.index[-1]).days
    freshness_score = max(0, 1 - (days_since_update / 7))  # 7 dias = 0
    
    # 2. Completude (quanto mais dados, maior confiança)
    completeness = 1 - (df.isnull().sum().sum() / (len(df) * len(df.columns)))
    
    # 3. Volatilidade (alta volatilidade = menor confiança)
    volatility = df['PP_Price'].pct_change().std()
    volatility_score = max(0, 1 - (volatility * 10))  # Normalizado
    
    # 4. Consistência (dados consistentes = maior confiança)
    consistency = 1 - (df['PP_Price'].diff().abs().mean() / df['PP_Price'].mean())
    
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
        'confidence_score': round(confidence, 2),
        'data_freshness_days': days_since_update,
        'data_completeness': round(completeness, 2),
        'volatility_index': round(volatility, 4),
        'recommendation': recommendation
    }
```

**Problema 7: Falta de Análise de Sensibilidade**
- Não mostra impacto de mudanças nos parâmetros
- Cliente não entende quais variáveis mais afetam o preço

**Sugestão:**
```python
def sensitivity_analysis(base_params: dict, ranges: dict) -> pd.DataFrame:
    """
    Análise de sensibilidade dos parâmetros de cálculo.
    
    Args:
        base_params: {'ocean_freight': 60, 'icms': 18, 'margin': 10}
        ranges: {'ocean_freight': (-10, +10), 'icms': (-2, +2), 'margin': (-2, +2)}
    
    Returns:
        DataFrame com impacto de cada parâmetro no preço final
    """
    base_price = calculate_cost_buildup(
        get_market_data(),
        base_params['ocean_freight'],
        base_params.get('freight_internal', 0.15),
        base_params['icms'],
        base_params['margin']
    )['PP_Price'].iloc[-1]
    
    results = []
    
    for param, (min_delta, max_delta) in ranges.items():
        for delta in [min_delta, max_delta]:
            test_params = base_params.copy()
            test_params[param] += delta
            
            test_price = calculate_cost_buildup(
                get_market_data(),
                test_params['ocean_freight'],
                test_params.get('freight_internal', 0.15),
                test_params['icms'],
                test_params['margin']
            )['PP_Price'].iloc[-1]
            
            impact = test_price - base_price
            impact_pct = (impact / base_price) * 100
            
            results.append({
                'parameter': param,
                'change': delta,
                'new_value': test_params[param],
                'price_impact': impact,
                'price_impact_pct': impact_pct,
                'sensitivity_rank': abs(impact_pct)
            })
    
    df = pd.DataFrame(results)
    df = df.sort_values('sensitivity_rank', ascending=False)
    
    return df
```

#### 🟡 **ALTO - Rastreabilidade e Auditoria**

**Problema 8: Sem Histórico de Cálculos**
- Não há como auditar como um preço foi calculado
- Impossível reprocessar com parâmetros históricos

**Sugestão:**
```python
def calculate_cost_buildup_with_audit(
    df, ocean_freight, freight_internal, icms_pct, margin_pct,
    save_audit: bool = True
) -> tuple[pd.DataFrame, dict]:
    """
    Versão com auditoria completa do cálculo.
    
    Returns:
        (df_resultado, audit_trail)
    """
    audit = {
        'timestamp': datetime.now().isoformat(),
        'input_params': {
            'ocean_freight': ocean_freight,
            'freight_internal': freight_internal,
            'icms_pct': icms_pct,
            'margin_pct': margin_pct
        },
        'data_snapshot': {
            'date_range': (df.index[0].isoformat(), df.index[-1].isoformat()),
            'rows_count': len(df),
            'wti_avg': float(df['WTI'].mean()),
            'usd_brl_avg': float(df['USD_BRL'].mean())
        },
        'calculation_steps': []
    }
    
    # Cálculo com rastreamento de cada passo
    df = df.copy()
    
    step1 = df['PP_FOB_USD'] + (ocean_freight / 1000)
    audit['calculation_steps'].append({
        'step': 'CFR_USD',
        'formula': 'PP_FOB_USD + (ocean_freight / 1000)',
        'result_sample': float(step1.iloc[-1])
    })
    df['CFR_USD'] = step1
    
    step2 = df['CFR_USD'] * df['USD_BRL'] * 1.12
    audit['calculation_steps'].append({
        'step': 'Landed_BRL',
        'formula': 'CFR_USD * USD_BRL * 1.12',
        'result_sample': float(step2.iloc[-1])
    })
    df['Landed_BRL'] = step2
    
    # ... (continuar para todos os passos)
    
    audit['final_result'] = {
        'pp_price': float(df['PP_Price'].iloc[-1]),
        'trend': float(df['Trend'].iloc[-1])
    }
    
    # Salvar audit trail no banco (opcional)
    if save_audit:
        db = database.get_db()
        if db:
            db.collection('calculation_audit').add(audit)
    
    return df, audit
```

---

### 1.3 PERSPECTIVA: Senior Backend Developer

#### 🔴 **CRÍTICO - Logging e Observabilidade**

**Problema 9: Logging Inadequado**
```python
# ATUAL (linha 47)
print(f"⚠️ Falha no DB: {e}")
```

**Impacto:**
- Impossível rastrear problemas em produção
- Sem métricas de performance
- Erros não são capturados para análise

**Sugestão:**
```python
import logging
from typing import Optional

# Configurar logger estruturado
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def get_market_data(days_back=180) -> pd.DataFrame:
    """
    Versão com logging estruturado.
    """
    start_time = datetime.now()
    logger.info(
        "get_market_data_started",
        extra={
            "days_back": days_back,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
    )
    
    try:
        # Tentativa Firestore
        db = database.get_db()
        if db:
            logger.debug("Attempting Firestore query")
            # ... query ...
            
            if data:
                logger.info(
                    "market_data_loaded_from_firestore",
                    extra={
                        "rows": len(df),
                        "source": "firestore",
                        "duration_ms": (datetime.now() - start_time).total_seconds() * 1000
                    }
                )
                return df
        
        # Fallback Yahoo Finance
        logger.warning("Falling back to Yahoo Finance", extra={"reason": "firestore_empty"})
        # ... yahoo finance ...
        
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
            "get_market_data_failed",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            },
            exc_info=True
        )
        raise
    
    return df
```

#### 🔴 **CRÍTICO - Tratamento de Erros**

**Problema 10: Exceções Genéricas**
- `except Exception as e` captura tudo
- Não diferencia erros recuperáveis de erros críticos
- Mensagens de erro podem expor detalhes sensíveis

**Sugestão:**
```python
class DataEngineError(Exception):
    """Base exception para erros do data engine."""
    pass

class DataSourceUnavailableError(DataEngineError):
    """Erro quando fonte de dados não está disponível."""
    pass

class DataValidationError(DataEngineError):
    """Erro de validação de dados."""
    pass

def get_market_data(days_back=180) -> pd.DataFrame:
    """
    Versão com tratamento de erros específico.
    """
    try:
        db = database.get_db()
        if not db:
            raise DataSourceUnavailableError("Firestore não disponível")
        
        # ... query ...
        
        if df.empty:
            logger.warning("Firestore returned empty dataset")
            raise DataSourceUnavailableError("Dados não encontrados no Firestore")
        
        # Validação
        df_validated, warnings = validate_market_data(df)
        if df_validated.empty:
            raise DataValidationError("Dados validados estão vazios")
        
        return df_validated
        
    except DataSourceUnavailableError:
        # Erro recuperável: tenta fallback
        logger.info("Attempting fallback data source")
        return _fallback_yahoo_finance(days_back)
        
    except DataValidationError as e:
        # Erro não recuperável: precisa intervenção
        logger.error(f"Data validation failed: {e}")
        raise
        
    except Exception as e:
        # Erro inesperado: log e re-raise
        logger.critical(f"Unexpected error in get_market_data: {e}", exc_info=True)
        raise DataEngineError(f"Erro interno do sistema de dados") from e
```

#### 🟡 **ALTO - Testabilidade**

**Problema 11: Acoplamento com Streamlit**
- Funções dependem de `st.cache_data`
- Difícil testar sem ambiente Streamlit
- Código não é reutilizável em outros contextos

**Sugestão:**
```python
from typing import Callable, Optional
from functools import lru_cache

# Abstração de cache
class CacheProvider:
    """Interface para diferentes providers de cache."""
    
    @staticmethod
    def get_cached(key: str, ttl: int, func: Callable, *args, **kwargs):
        raise NotImplementedError

class StreamlitCacheProvider(CacheProvider):
    """Provider para Streamlit."""
    
    @staticmethod
    def get_cached(key: str, ttl: int, func: Callable, *args, **kwargs):
        # Usa st.cache_data se disponível
        if 'st' in globals():
            return st.cache_data(ttl=ttl)(func)(*args, **kwargs)
        return func(*args, **kwargs)

class LRUCacheProvider(CacheProvider):
    """Provider para testes (LRU cache simples)."""
    
    @staticmethod
    @lru_cache(maxsize=128)
    def get_cached(key: str, ttl: int, func: Callable, *args, **kwargs):
        return func(*args, **kwargs)

# Injeção de dependência
_cache_provider: Optional[CacheProvider] = None

def set_cache_provider(provider: CacheProvider):
    """Permite injetar provider de cache (útil para testes)."""
    global _cache_provider
    _cache_provider = provider

def get_market_data(days_back=180, cache_provider: Optional[CacheProvider] = None):
    """
    Versão com cache injetável.
    """
    provider = cache_provider or _cache_provider or StreamlitCacheProvider()
    
    cache_key = f"market_data_{days_back}"
    ttl = get_cache_ttl()
    
    return provider.get_cached(cache_key, ttl, _get_market_data_impl, days_back)

def _get_market_data_impl(days_back: int) -> pd.DataFrame:
    """Implementação real (sem cache)."""
    # ... lógica original ...
```

#### 🟡 **ALTO - Type Hints e Documentação**

**Problema 12: Falta de Type Hints**
- Código difícil de entender e manter
- IDEs não conseguem fazer autocomplete adequado
- Erros de tipo só aparecem em runtime

**Sugestão:**
```python
from typing import Optional, Tuple
from datetime import datetime
import pandas as pd

def get_market_data(
    days_back: int = 180,
    validate: bool = True
) -> pd.DataFrame:
    """
    Busca dados históricos de mercado.
    
    Args:
        days_back: Número de dias para buscar (padrão: 180)
        validate: Se True, valida dados antes de retornar
        
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
    # ... implementação ...
```

---

## 2️⃣ MÓDULO: `database.py`

### 2.1 PERSPECTIVA: Senior Data Engineer

#### 🔴 **CRÍTICO - Transações e Consistência**

**Problema 13: Operações Sem Transações**
```python
# ATUAL (linha 45-49)
doc_ref.set({
    'username': username, 'email': email, ...
})
```

**Impacto:**
- Se operação falhar no meio, dados podem ficar inconsistentes
- Sem rollback em caso de erro
- Race conditions possíveis

**Sugestão:**
```python
def create_user(username, email, password, name, role, modules):
    """
    Versão com transação e validações.
    """
    db = get_db()
    if not db:
        return False, "Banco Offline.", None
    
    # Validações antes da transação
    if not username or not email:
        return False, "Username e email são obrigatórios.", None
    
    if not is_valid_email(email):
        return False, "Email inválido.", None
    
    # Transação atômica
    transaction = db.transaction()
    
    @firestore.transactional
    def create_user_transaction(transaction):
        users_ref = db.collection('users')
        
        # Verifica se username já existe (na transação)
        doc_ref = users_ref.document(username)
        snapshot = doc_ref.get(transaction=transaction)
        
        if snapshot.exists:
            raise ValueError("Login já existe.")
        
        # Verifica se email já existe
        email_query = users_ref.where('email', '==', email).limit(1)
        email_docs = list(email_query.stream())
        if email_docs:
            raise ValueError("Email já cadastrado.")
        
        # Cria usuário
        password_hash = hash_password(password)
        token = str(uuid.uuid4())
        
        transaction.set(doc_ref, {
            'username': username,
            'email': email,
            'password': password_hash,
            'name': name,
            'role': role,
            'modules': modules,
            'verified': False,
            'verification_token': token,
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP
        })
        
        return token
    
    try:
        token = create_user_transaction(transaction)
        return True, "Usuário criado!", token
    except ValueError as e:
        return False, str(e), None
    except Exception as e:
        logger.error(f"Error creating user: {e}", exc_info=True)
        return False, "Erro interno ao criar usuário.", None
```

#### 🟡 **ALTO - Índices e Performance**

**Problema 14: Queries Sem Índices**
```python
# ATUAL (linha 66, 91, 116)
query = users_ref.where('username', '==', current_username).stream()
```

**Impacto:**
- Queries podem ser lentas sem índices adequados
- Firestore pode rejeitar queries complexas sem índice

**Sugestão:**
```python
# Documentar índices necessários no Firestore:
# - Collection: users
#   - Índice composto: username (Ascending)
#   - Índice composto: email (Ascending)
#   - Índice composto: verification_token (Ascending)

# Criar função helper para queries otimizadas
def get_user_by_username(username: str) -> Optional[dict]:
    """
    Busca usuário por username (otimizado com índice).
    """
    db = get_db()
    if not db:
        return None
    
    # Usa document ID quando possível (mais rápido)
    doc_ref = db.collection('users').document(username)
    doc = doc_ref.get()
    
    if doc.exists:
        return doc.to_dict()
    
    # Fallback: query (se username != document ID)
    query = db.collection('users')\
              .where('username', '==', username)\
              .limit(1)\
              .stream()
    
    doc = next(query, None)
    return doc.to_dict() if doc else None
```

#### 🟡 **ALTO - Validação de Dados**

**Problema 15: Dados Não Validados Antes de Salvar**
- Email pode estar em formato inválido
- Role pode ter valor não permitido
- Modules pode ter valores inválidos

**Sugestão:**
```python
from enum import Enum
from typing import List

class UserRole(str, Enum):
    CLIENT = "client"
    ADMIN = "admin"

class UserModule(str, Enum):
    MONITOR = "Monitor"
    CALCULATOR = "Calculadora Financeira"
    DASHBOARD = "Dashboard"

def validate_user_data(
    username: str,
    email: str,
    role: str,
    modules: List[str]
) -> Tuple[bool, Optional[str]]:
    """
    Valida dados do usuário antes de salvar.
    
    Returns:
        (is_valid, error_message)
    """
    # Validação de username
    if not username or len(username) < 3:
        return False, "Username deve ter pelo menos 3 caracteres"
    
    if not username.replace('_', '').replace('.', '').isalnum():
        return False, "Username contém caracteres inválidos"
    
    # Validação de email
    if not is_valid_email(email):
        return False, "Email inválido"
    
    # Validação de role
    try:
        UserRole(role)
    except ValueError:
        return False, f"Role inválida. Permitidas: {[r.value for r in UserRole]}"
    
    # Validação de modules
    valid_modules = [m.value for m in UserModule]
    invalid_modules = [m for m in modules if m not in valid_modules]
    if invalid_modules:
        return False, f"Módulos inválidos: {invalid_modules}"
    
    return True, None
```

---

### 2.2 PERSPECTIVA: Senior Backend Developer

#### 🔴 **CRÍTICO - Segurança**

**Problema 16: Sanitização de Chave Privada Frágil**
```python
# ATUAL (linha 21-23)
pk = pk.replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "")
pk = pk.replace("\\n", "").replace("\n", "").replace(" ", "").replace("\t", "").replace('"', '').replace("'", "")
```

**Impacto:**
- Lógica de sanitização frágil e difícil de manter
- Pode falhar com formatos diferentes
- Não valida se a chave está correta após sanitização

**Sugestão:**
```python
import re
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

def sanitize_private_key(key_str: str) -> str:
    """
    Sanitiza e valida chave privada do Firebase.
    
    Args:
        key_str: String com a chave privada (pode ter formatação variada)
        
    Returns:
        Chave privada formatada corretamente
        
    Raises:
        ValueError: Se a chave não puder ser validada
    """
    # Remove todos os espaços, quebras de linha e caracteres especiais
    cleaned = re.sub(r'[\s\n\r\t"\'\\]', '', key_str)
    
    # Remove marcadores de início/fim se existirem
    cleaned = re.sub(r'BEGINPRIVATEKEY|ENDPRIVATEKEY', '', cleaned, flags=re.IGNORECASE)
    
    # Reconstroi a chave no formato correto
    # Chave privada RSA tem 2048 bits = 256 bytes = 344 caracteres base64
    if len(cleaned) < 300:
        raise ValueError("Chave privada parece estar incompleta")
    
    # Formata com quebras de linha a cada 64 caracteres (padrão PEM)
    formatted_key = "-----BEGIN PRIVATE KEY-----\n"
    for i in range(0, len(cleaned), 64):
        formatted_key += cleaned[i:i+64] + "\n"
    formatted_key += "-----END PRIVATE KEY-----"
    
    # Valida se a chave pode ser carregada (teste de integridade)
    try:
        serialization.load_pem_private_key(
            formatted_key.encode(),
            password=None,
            backend=default_backend()
        )
    except Exception as e:
        raise ValueError(f"Chave privada inválida: {e}")
    
    return formatted_key
```

#### 🔴 **CRÍTICO - Rate Limiting e Proteção**

**Problema 17: Sem Proteção Contra Abuso**
- Funções podem ser chamadas infinitamente
- Sem rate limiting
- Vulnerável a ataques de força bruta

**Sugestão:**
```python
from functools import wraps
from datetime import datetime, timedelta
from collections import defaultdict

# Rate limiter simples (em produção, usar Redis)
_rate_limiter = defaultdict(list)

def rate_limit(max_calls: int = 5, period_seconds: int = 60):
    """
    Decorator para rate limiting.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            now = datetime.now()
            
            # Limpa chamadas antigas
            _rate_limiter[func_name] = [
                call_time for call_time in _rate_limiter[func_name]
                if now - call_time < timedelta(seconds=period_seconds)
            ]
            
            # Verifica limite
            if len(_rate_limiter[func_name]) >= max_calls:
                raise RateLimitError(
                    f"Muitas chamadas para {func_name}. "
                    f"Limite: {max_calls} por {period_seconds}s"
                )
            
            # Registra chamada
            _rate_limiter[func_name].append(now)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

@rate_limit(max_calls=3, period_seconds=300)  # 3 tentativas a cada 5 min
def verify_user_token(token: str) -> Tuple[bool, str]:
    """
    Versão com rate limiting.
    """
    # ... implementação ...
```

#### 🟡 **ALTO - Logging de Auditoria**

**Problema 18: Sem Log de Operações Sensíveis**
- Criação/edição de usuários não é auditada
- Impossível rastrear quem fez o quê e quando

**Sugestão:**
```python
def audit_log(
    action: str,
    user_id: Optional[str] = None,
    target_user: Optional[str] = None,
    details: Optional[dict] = None
):
    """
    Registra evento de auditoria.
    """
    db = get_db()
    if not db:
        return
    
    audit_entry = {
        'action': action,  # 'user_created', 'user_updated', 'user_deleted'
        'user_id': user_id,  # Quem fez a ação
        'target_user': target_user,  # Sobre quem foi a ação
        'details': details or {},
        'timestamp': firestore.SERVER_TIMESTAMP,
        'ip_address': _get_client_ip(),  # Se disponível
    }
    
    db.collection('audit_logs').add(audit_entry)
    logger.info(f"Audit: {action}", extra=audit_entry)

def create_user(username, email, password, name, role, modules):
    """
    Versão com auditoria.
    """
    # ... criação ...
    
    # Log de auditoria
    current_user = st.session_state.get('user_name', 'system')
    audit_log(
        action='user_created',
        user_id=current_user,
        target_user=username,
        details={
            'email': email,
            'role': role,
            'modules': modules
        }
    )
    
    return True, "Usuário criado!", token
```

---

### 2.3 PERSPECTIVA: Senior Business Analyst

#### 🟡 **ALTO - Métricas de Usuários**

**Problema 19: Falta de Analytics de Usuários**
- Não há métricas de engajamento
- Não rastreia conversão (criação → verificação → uso)
- Não mede retenção

**Sugestão:**
```python
def get_user_analytics() -> dict:
    """
    Retorna métricas de usuários para análise de negócio.
    """
    db = get_db()
    if not db:
        return {}
    
    users = list(db.collection('users').stream())
    
    total = len(users)
    verified = sum(1 for u in users if u.to_dict().get('verified', False))
    admins = sum(1 for u in users if u.to_dict().get('role') == 'admin')
    
    # Taxa de conversão (criação → verificação)
    conversion_rate = (verified / total * 100) if total > 0 else 0
    
    # Usuários por módulo
    module_usage = defaultdict(int)
    for u in users:
        modules = u.to_dict().get('modules', [])
        for m in modules:
            module_usage[m] += 1
    
    # Usuários criados por período
    now = datetime.now()
    last_7_days = sum(
        1 for u in users
        if u.to_dict().get('created_at') and
        (now - u.to_dict()['created_at']).days <= 7
    )
    
    return {
        'total_users': total,
        'verified_users': verified,
        'unverified_users': total - verified,
        'admin_users': admins,
        'client_users': total - admins,
        'conversion_rate': round(conversion_rate, 2),
        'module_usage': dict(module_usage),
        'new_users_7d': last_7_days,
        'verification_rate': round((verified / total * 100) if total > 0 else 0, 2)
    }
```

---

## 📊 PRIORIZAÇÃO DAS MELHORIAS

### 🔴 **CRÍTICO (Implementar Imediatamente)**

1. **Validação de Dados** (`data_engine.py`)
   - Impacto: Previne cálculos incorretos
   - Esforço: Médio
   - ROI: Alto

2. **Logging Estruturado** (Ambos)
   - Impacto: Essencial para produção
   - Esforço: Baixo
   - ROI: Muito Alto

3. **Tratamento de Erros Específico** (`data_engine.py`)
   - Impacto: Melhora confiabilidade
   - Esforço: Médio
   - ROI: Alto

4. **Transações Atômicas** (`database.py`)
   - Impacto: Previne inconsistências
   - Esforço: Médio
   - ROI: Alto

5. **Sanitização Segura de Chaves** (`database.py`)
   - Impacto: Segurança crítica
   - Esforço: Baixo
   - ROI: Muito Alto

### 🟡 **ALTO (Implementar em 2-4 semanas)**

6. **Métricas de Confiança** (`data_engine.py`)
7. **Análise de Sensibilidade** (`data_engine.py`)
8. **Otimização de Queries** (`database.py`)
9. **Validação de Dados de Usuário** (`database.py`)
10. **Auditoria de Operações** (`database.py`)

### 🟢 **MÉDIO (Backlog)**

11. **Abstração de Cache** (`data_engine.py`)
12. **Type Hints Completos** (Ambos)
13. **Métricas de Analytics de Usuários** (`database.py`)
14. **Rate Limiting** (`database.py`)

---

## 🎯 RECOMENDAÇÕES FINAIS

### Arquitetura
1. **Separar Lógica de Negócio do Streamlit**
   - Criar camada de serviço pura (sem `st.*`)
   - Facilita testes e reutilização

2. **Configuração Centralizada**
   - Mover fórmulas e constantes para arquivo de config
   - Permitir override via variáveis de ambiente

3. **Camada de Dados Abstrata**
   - Interface para diferentes fontes de dados
   - Facilita migração futura

### Qualidade
1. **Testes Unitários**
   - Cobertura mínima: 80%
   - Focar em lógica de cálculo e validação

2. **Testes de Integração**
   - Testar fluxo completo ETL
   - Testar interação com Firestore

3. **Monitoramento**
   - Métricas de performance (latência, throughput)
   - Alertas para degradação de qualidade de dados

### Documentação
1. **Docstrings Completos**
   - Todos os métodos públicos
   - Exemplos de uso

2. **Diagramas de Arquitetura**
   - Fluxo de dados
   - Dependências entre módulos

---

## 📝 PRÓXIMOS PASSOS

1. **Revisar este documento** e aprovar melhorias prioritárias
2. **Criar issues/tasks** para cada melhoria aprovada
3. **Implementar em fases** (crítico → alto → médio)
4. **Testar cada fase** antes de prosseguir
5. **Documentar mudanças** no código

---

**Fim do Documento de Revisão**

