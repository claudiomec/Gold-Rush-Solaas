"""
Módulo de Rate Limiter - Limitação de requisições
Responsável por prevenir abuso e ataques através de rate limiting.
"""
import streamlit as st
import logging
import time
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from modules.database import get_db
from firebase_admin import firestore

# Configuração de logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Tenta importar slowapi (opcional)
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    HAS_SLOWAPI = True
except ImportError:
    HAS_SLOWAPI = False
    logger.warning("slowapi não disponível. Rate limiting será básico.")


# ============================================================================
# RATE LIMITING SIMPLES (Fallback)
# ============================================================================

# Cache em memória para rate limiting (em produção, usar Redis)
_rate_limit_cache: Dict[str, list] = defaultdict(list)


def check_rate_limit(
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    max_requests: int = 100,
    window_seconds: int = 60
) -> Tuple[bool, Optional[str]]:
    """
    Verifica se usuário/IP pode fazer requisição.
    
    Args:
        user_id: ID do usuário (opcional)
        ip_address: Endereço IP (opcional)
        max_requests: Número máximo de requisições
        window_seconds: Janela de tempo em segundos
        
    Returns:
        Tuple[allowed, error_message]
    """
    # Identifica chave única
    if user_id:
        key = f"user:{user_id}"
    elif ip_address:
        key = f"ip:{ip_address}"
    else:
        # Tenta pegar IP do Streamlit
        try:
            # Streamlit não expõe IP diretamente, usa timestamp como fallback
            key = f"session:{id(st.session_state)}"
        except:
            return True, None  # Se não conseguir identificar, permite
    
    # Limpa requisições antigas
    now = time.time()
    _rate_limit_cache[key] = [
        req_time for req_time in _rate_limit_cache[key]
        if now - req_time < window_seconds
    ]
    
    # Verifica limite
    if len(_rate_limit_cache[key]) >= max_requests:
        logger.warning(
            "rate_limit_exceeded",
            extra={
                "key": key,
                "requests": len(_rate_limit_cache[key]),
                "max_requests": max_requests
            }
        )
        return False, f"Limite de requisições excedido. Tente novamente em {window_seconds} segundos."
    
    # Adiciona requisição atual
    _rate_limit_cache[key].append(now)
    
    return True, None


def check_user_rate_limit(user_id: str, action: str = "general") -> Tuple[bool, Optional[str]]:
    """
    Verifica rate limit específico por ação do usuário.
    
    Args:
        user_id: ID do usuário
        action: Tipo de ação ('login', 'report', 'api', etc.)
        
    Returns:
        Tuple[allowed, error_message]
    """
    # Limites por ação
    limits = {
        'login': (5, 300),  # 5 tentativas em 5 minutos
        'report': (10, 60),  # 10 relatórios por minuto
        'api': (100, 60),  # 100 requisições por minuto
        'general': (200, 60)  # 200 requisições gerais por minuto
    }
    
    max_requests, window_seconds = limits.get(action, limits['general'])
    
    return check_rate_limit(
        user_id=user_id,
        max_requests=max_requests,
        window_seconds=window_seconds
    )


def enforce_rate_limit_in_view(
    user_id: Optional[str] = None,
    action: str = "general"
) -> bool:
    """
    Middleware para aplicar rate limit em views do Streamlit.
    
    Args:
        user_id: ID do usuário (opcional)
        action: Tipo de ação
        
    Returns:
        True se permitido, False se bloqueado
    """
    allowed, error_msg = check_user_rate_limit(user_id or "anonymous", action)
    
    if not allowed:
        st.error(f"🚫 {error_msg}")
        return False
    
    return True


# ============================================================================
# RATE LIMITING COM FIREBASE (Persistente)
# ============================================================================

def check_rate_limit_firebase(
    user_id: str,
    action: str,
    max_requests: int,
    window_seconds: int
) -> Tuple[bool, Optional[str]]:
    """
    Verifica rate limit usando Firestore (persistente).
    
    Args:
        user_id: ID do usuário
        action: Tipo de ação
        max_requests: Número máximo de requisições
        window_seconds: Janela de tempo em segundos
        
    Returns:
        Tuple[allowed, error_message]
    """
    db = get_db()
    if not db:
        # Fallback para cache em memória
        return check_user_rate_limit(user_id, action)
    
    try:
        now = datetime.now()
        window_start = now - timedelta(seconds=window_seconds)
        
        # Busca requisições na janela
        rate_limits_ref = db.collection('rate_limits')
        query = rate_limits_ref.where('user_id', '==', user_id)\
                               .where('action', '==', action)\
                               .where('timestamp', '>=', window_start)\
                               .order_by('timestamp', direction=firestore.Query.DESCENDING)
        
        requests = list(query.stream())
        
        if len(requests) >= max_requests:
            logger.warning(
                "rate_limit_exceeded_firebase",
                extra={
                    "user_id": user_id,
                    "action": action,
                    "requests": len(requests),
                    "max_requests": max_requests
                }
            )
            return False, f"Limite de {action} excedido. Tente novamente em {window_seconds} segundos."
        
        # Registra nova requisição
        rate_limits_ref.add({
            'user_id': user_id,
            'action': action,
            'timestamp': now,
            'expires_at': now + timedelta(seconds=window_seconds)
        })
        
        # Limpa requisições expiradas (background)
        # TODO: Implementar limpeza periódica
        
        return True, None
        
    except Exception as e:
        logger.error(
            "check_rate_limit_firebase_error",
            extra={
                "user_id": user_id,
                "action": action,
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        # Em caso de erro, permite (fail open)
        return True, None

