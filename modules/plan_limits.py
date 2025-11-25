"""
Módulo de Plan Limits - Verificação de limites por plano
Responsável por verificar se usuário pode executar ações baseado no plano.
"""
import streamlit as st
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from modules.subscription import (
    get_user_subscription,
    PlanType,
    SubscriptionStatus,
    get_plan_limits,
    check_subscription_expired
)
from modules.database import get_db
from firebase_admin import firestore

# Configuração de logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ============================================================================
# VERIFICAÇÃO DE LIMITES
# ============================================================================

def check_user_limit(
    user_id: str,
    limit_type: str,
    current_usage: Optional[int] = None
) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Verifica se usuário pode executar ação baseado no plano.
    
    Args:
        user_id: ID do usuário
        limit_type: Tipo de limite ('history_days', 'reports_per_month', 'users', 'api_access')
        current_usage: Uso atual (opcional, será calculado se None)
        
    Returns:
        Tuple[allowed, error_message, subscription_info]
    """
    logger.debug(f"check_user_limit_started: {user_id}, {limit_type}")
    
    # Busca assinatura
    subscription = get_user_subscription(user_id)
    if not subscription:
        logger.warning(f"check_user_limit_no_subscription: {user_id}")
        # Sem assinatura = plano FREE
        subscription = {
            'plan_type': PlanType.FREE.value,
            'status': SubscriptionStatus.ACTIVE.value
        }
    
    # Verifica se expirada
    if check_subscription_expired(subscription):
        logger.warning(f"check_user_limit_expired: {user_id}")
        subscription['status'] = SubscriptionStatus.EXPIRED.value
        return False, "Sua assinatura expirou. Por favor, renove para continuar usando.", subscription
    
    plan_type = PlanType(subscription.get('plan_type', PlanType.FREE.value))
    limits = get_plan_limits(plan_type)
    
    # Verifica limite específico
    if limit_type == 'history_days':
        max_days = limits.get('max_history_days')
        if max_days is None:
            return True, None, subscription  # Ilimitado
        if current_usage and current_usage > max_days:
            return False, f"Seu plano permite apenas {max_days} dias de histórico. Upgrade para acessar mais dados.", subscription
        return True, None, subscription
    
    elif limit_type == 'reports_per_month':
        max_reports = limits.get('max_reports_per_month')
        if max_reports is None:
            return True, None, subscription  # Ilimitado
        
        # Calcula uso atual do mês se não fornecido
        if current_usage is None:
            current_usage = get_reports_count_this_month(user_id)
        
        if current_usage >= max_reports:
            return False, f"Você atingiu o limite de {max_reports} relatórios/mês do seu plano. Upgrade para gerar mais relatórios.", subscription
        return True, None, subscription
    
    elif limit_type == 'users':
        max_users = limits.get('max_users')
        if max_users is None:
            return True, None, subscription  # Ilimitado
        if current_usage and current_usage >= max_users:
            return False, f"Seu plano permite apenas {max_users} usuário(s). Upgrade para adicionar mais usuários.", subscription
        return True, None, subscription
    
    elif limit_type == 'api_access':
        has_access = limits.get('api_access', False)
        if not has_access:
            return False, "Acesso à API disponível apenas nos planos Professional e Enterprise. Faça upgrade!", subscription
        return True, None, subscription
    
    else:
        logger.warning(f"check_user_limit_unknown_type: {limit_type}")
        return True, None, subscription  # Tipo desconhecido = permite


def get_reports_count_this_month(user_id: str) -> int:
    """
    Conta quantos relatórios o usuário gerou este mês.
    
    Args:
        user_id: ID do usuário
        
    Returns:
        Número de relatórios gerados este mês
    """
    db = get_db()
    if not db:
        return 0
    
    try:
        # Primeiro dia do mês atual
        first_day = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        reports_ref = db.collection('reports')
        query = reports_ref.where('user_id', '==', user_id)\
                          .where('created_at', '>=', first_day)
        
        count = len(list(query.stream()))
        return count
        
    except Exception as e:
        logger.error(
            "get_reports_count_this_month_error",
            extra={
                "user_id": user_id,
                "error": str(e)
            },
            exc_info=True
        )
        return 0


def check_history_days_limit(user_id: str, requested_days: int) -> Tuple[bool, Optional[str]]:
    """
    Verifica se usuário pode acessar histórico de N dias.
    
    Args:
        user_id: ID do usuário
        requested_days: Número de dias solicitados
        
    Returns:
        Tuple[allowed, error_message]
    """
    subscription = get_user_subscription(user_id)
    if not subscription:
        subscription = {'plan_type': PlanType.FREE.value}
    
    plan_type = PlanType(subscription.get('plan_type', PlanType.FREE.value))
    limits = get_plan_limits(plan_type)
    max_days = limits.get('max_history_days')
    
    if max_days is None:
        return True, None  # Ilimitado
    
    if requested_days > max_days:
        return False, f"Seu plano permite apenas {max_days} dias de histórico. Você solicitou {requested_days} dias."
    
    return True, None


def check_reports_limit(user_id: str) -> Tuple[bool, Optional[str], Optional[int]]:
    """
    Verifica se usuário pode gerar relatório.
    
    Args:
        user_id: ID do usuário
        
    Returns:
        Tuple[allowed, error_message, reports_remaining]
    """
    subscription = get_user_subscription(user_id)
    if not subscription:
        subscription = {'plan_type': PlanType.FREE.value}
    
    plan_type = PlanType(subscription.get('plan_type', PlanType.FREE.value))
    limits = get_plan_limits(plan_type)
    max_reports = limits.get('max_reports_per_month')
    
    if max_reports is None:
        return True, None, None  # Ilimitado
    
    current_usage = get_reports_count_this_month(user_id)
    remaining = max_reports - current_usage
    
    if current_usage >= max_reports:
        return False, f"Você atingiu o limite de {max_reports} relatórios/mês. Upgrade para gerar mais.", remaining
    
    return True, None, remaining


def check_api_access(user_id: str) -> Tuple[bool, Optional[str]]:
    """
    Verifica se usuário tem acesso à API.
    
    Args:
        user_id: ID do usuário
        
    Returns:
        Tuple[allowed, error_message]
    """
    subscription = get_user_subscription(user_id)
    if not subscription:
        subscription = {'plan_type': PlanType.FREE.value}
    
    plan_type = PlanType(subscription.get('plan_type', PlanType.FREE.value))
    limits = get_plan_limits(plan_type)
    has_access = limits.get('api_access', False)
    
    if not has_access:
        return False, "Acesso à API disponível apenas nos planos Professional e Enterprise."
    
    return True, None


def get_user_plan_info(user_id: str) -> Dict[str, Any]:
    """
    Retorna informações completas do plano do usuário.
    
    Args:
        user_id: ID do usuário
        
    Returns:
        Dict com informações do plano e limites
    """
    subscription = get_user_subscription(user_id)
    if not subscription:
        subscription = {
            'plan_type': PlanType.FREE.value,
            'status': SubscriptionStatus.ACTIVE.value
        }
    
    plan_type = PlanType(subscription.get('plan_type', PlanType.FREE.value))
    limits = get_plan_limits(plan_type)
    
    # Calcula uso atual
    reports_this_month = get_reports_count_this_month(user_id)
    max_reports = limits.get('max_reports_per_month')
    reports_remaining = None if max_reports is None else max_reports - reports_this_month
    
    return {
        'plan_type': plan_type.value,
        'plan_name': plan_type.value.capitalize(),
        'status': subscription.get('status'),
        'limits': limits,
        'usage': {
            'reports_this_month': reports_this_month,
            'reports_remaining': reports_remaining,
            'reports_limit': max_reports
        },
        'subscription': subscription
    }


def enforce_limit_in_view(user_id: str, limit_type: str, action_name: str = "esta ação") -> bool:
    """
    Middleware para aplicar limite em views do Streamlit.
    Mostra erro e retorna False se limite excedido.
    
    Args:
        user_id: ID do usuário
        limit_type: Tipo de limite
        action_name: Nome da ação (para mensagem de erro)
        
    Returns:
        True se permitido, False se bloqueado
    """
    allowed, error_msg, subscription_info = check_user_limit(user_id, limit_type)
    
    if not allowed:
        st.error(f"🚫 {error_msg}")
        if subscription_info and subscription_info.get('plan_type') != PlanType.FREE.value:
            st.info("💡 Considere fazer upgrade do seu plano para acessar mais recursos.")
        return False
    
    return True

