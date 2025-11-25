"""
Módulo de Subscription - Gerenciamento de planos e assinaturas
Responsável por criar, atualizar e gerenciar assinaturas dos usuários.
"""
import streamlit as st
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from enum import Enum
from modules.database import get_db
from firebase_admin import firestore

# Configuração de logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ============================================================================
# ENUMS E CONSTANTES
# ============================================================================

class PlanType(str, Enum):
    """Tipos de planos disponíveis."""
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, Enum):
    """Status de assinatura."""
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    TRIAL = "trial"
    PENDING = "pending"


# Definição de limites por plano
PLAN_LIMITS = {
    PlanType.FREE: {
        "max_users": 1,
        "max_history_days": 30,
        "max_reports_per_month": 5,
        "api_access": False,
        "support_level": "email",
        "price_monthly": 0.0,
        "price_currency": "BRL"
    },
    PlanType.STARTER: {
        "max_users": 3,
        "max_history_days": 90,
        "max_reports_per_month": 20,
        "api_access": False,
        "support_level": "priority",
        "price_monthly": 299.0,
        "price_currency": "BRL"
    },
    PlanType.PROFESSIONAL: {
        "max_users": 10,
        "max_history_days": None,  # None = ilimitado
        "max_reports_per_month": None,  # None = ilimitado
        "api_access": True,
        "support_level": "priority",
        "price_monthly": 799.0,
        "price_currency": "BRL"
    },
    PlanType.ENTERPRISE: {
        "max_users": None,  # None = ilimitado
        "max_history_days": None,
        "max_reports_per_month": None,
        "api_access": True,
        "support_level": "dedicated",
        "price_monthly": None,  # Customizado
        "price_currency": "BRL"
    }
}


# ============================================================================
# FUNÇÕES DE ASSINATURA
# ============================================================================

def get_user_subscription(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Busca assinatura ativa do usuário.
    
    Args:
        user_id: ID do usuário (username ou email)
        
    Returns:
        Dict com dados da assinatura ou None se não encontrada
    """
    logger.debug(f"get_user_subscription_started: {user_id}")
    
    db = get_db()
    if not db:
        logger.warning("get_user_subscription_failed: Banco offline")
        return None
    
    try:
        subscriptions_ref = db.collection('subscriptions')
        query = subscriptions_ref.where('user_id', '==', user_id)\
                                 .where('status', '==', SubscriptionStatus.ACTIVE.value)\
                                 .order_by('start_date', direction=firestore.Query.DESCENDING)\
                                 .limit(1)
        
        docs = list(query.stream())
        
        if docs:
            subscription = docs[0].to_dict()
            subscription['id'] = docs[0].id
            logger.info(f"get_user_subscription_success: {user_id}")
            return subscription
        
        # Se não tem assinatura ativa, retorna plano FREE por padrão
        logger.info(f"get_user_subscription_default_free: {user_id}")
        return {
            'user_id': user_id,
            'plan_type': PlanType.FREE.value,
            'status': SubscriptionStatus.ACTIVE.value,
            'start_date': datetime.now(),
            'end_date': None,
            'payment_method': None,
            'stripe_customer_id': None,
            'stripe_subscription_id': None
        }
        
    except Exception as e:
        logger.error(
            "get_user_subscription_error",
            extra={
                "user_id": user_id,
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        return None


def create_subscription(
    user_id: str,
    plan_type: PlanType,
    payment_method: Optional[str] = None,
    stripe_customer_id: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Tuple[bool, str, Optional[str]]:
    """
    Cria nova assinatura para usuário.
    
    Args:
        user_id: ID do usuário
        plan_type: Tipo de plano
        payment_method: Método de pagamento (opcional)
        stripe_customer_id: ID do cliente no Stripe (opcional)
        stripe_subscription_id: ID da assinatura no Stripe (opcional)
        start_date: Data de início (padrão: agora)
        end_date: Data de término (padrão: None para planos mensais)
        
    Returns:
        Tuple[sucesso, mensagem, subscription_id]
    """
    logger.info(
        "create_subscription_started",
        extra={
            "user_id": user_id,
            "plan_type": plan_type.value
        }
    )
    
    db = get_db()
    if not db:
        logger.error("create_subscription_failed: Banco offline")
        return False, "Banco Offline.", None
    
    # Validação de plano
    if plan_type not in PLAN_LIMITS:
        logger.warning(f"create_subscription_invalid_plan: {plan_type}")
        return False, f"Plano inválido: {plan_type}", None
    
    try:
        # Cancela assinaturas ativas anteriores
        cancel_active_subscriptions(user_id)
        
        # Define datas
        if start_date is None:
            start_date = datetime.now()
        
        if end_date is None and plan_type != PlanType.FREE:
            # Planos pagos: 1 mês a partir de start_date
            end_date = start_date + timedelta(days=30)
        
        # Cria nova assinatura
        subscription_data = {
            'user_id': user_id,
            'plan_type': plan_type.value,
            'status': SubscriptionStatus.ACTIVE.value,
            'start_date': start_date,
            'end_date': end_date,
            'payment_method': payment_method,
            'stripe_customer_id': stripe_customer_id,
            'stripe_subscription_id': stripe_subscription_id,
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP
        }
        
        subscriptions_ref = db.collection('subscriptions')
        doc_ref = subscriptions_ref.add(subscription_data)
        subscription_id = doc_ref[1].id
        
        logger.info(
            "create_subscription_success",
            extra={
                "user_id": user_id,
                "plan_type": plan_type.value,
                "subscription_id": subscription_id
            }
        )
        
        return True, f"Assinatura {plan_type.value} criada com sucesso!", subscription_id
        
    except Exception as e:
        logger.error(
            "create_subscription_error",
            extra={
                "user_id": user_id,
                "plan_type": plan_type.value,
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        return False, f"Erro ao criar assinatura: {str(e)}", None


def update_subscription(
    subscription_id: str,
    plan_type: Optional[PlanType] = None,
    status: Optional[SubscriptionStatus] = None,
    end_date: Optional[datetime] = None
) -> Tuple[bool, str]:
    """
    Atualiza assinatura existente.
    
    Args:
        subscription_id: ID da assinatura
        plan_type: Novo tipo de plano (opcional)
        status: Novo status (opcional)
        end_date: Nova data de término (opcional)
        
    Returns:
        Tuple[sucesso, mensagem]
    """
    logger.info(f"update_subscription_started: {subscription_id}")
    
    db = get_db()
    if not db:
        logger.error("update_subscription_failed: Banco offline")
        return False, "Banco Offline."
    
    try:
        subscription_ref = db.collection('subscriptions').document(subscription_id)
        subscription = subscription_ref.get()
        
        if not subscription.exists:
            logger.warning(f"update_subscription_not_found: {subscription_id}")
            return False, "Assinatura não encontrada."
        
        updates = {
            'updated_at': firestore.SERVER_TIMESTAMP
        }
        
        if plan_type:
            updates['plan_type'] = plan_type.value
        if status:
            updates['status'] = status.value
        if end_date:
            updates['end_date'] = end_date
        
        subscription_ref.update(updates)
        
        logger.info(f"update_subscription_success: {subscription_id}")
        return True, "Assinatura atualizada com sucesso!"
        
    except Exception as e:
        logger.error(
            "update_subscription_error",
            extra={
                "subscription_id": subscription_id,
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        return False, f"Erro ao atualizar assinatura: {str(e)}"


def cancel_active_subscriptions(user_id: str) -> bool:
    """
    Cancela todas as assinaturas ativas do usuário.
    
    Args:
        user_id: ID do usuário
        
    Returns:
        True se cancelou com sucesso
    """
    logger.info(f"cancel_active_subscriptions_started: {user_id}")
    
    db = get_db()
    if not db:
        logger.warning("cancel_active_subscriptions_failed: Banco offline")
        return False
    
    try:
        subscriptions_ref = db.collection('subscriptions')
        query = subscriptions_ref.where('user_id', '==', user_id)\
                                 .where('status', '==', SubscriptionStatus.ACTIVE.value)
        
        for doc in query.stream():
            doc.reference.update({
                'status': SubscriptionStatus.CANCELLED.value,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
        
        logger.info(f"cancel_active_subscriptions_success: {user_id}")
        return True
        
    except Exception as e:
        logger.error(
            "cancel_active_subscriptions_error",
            extra={
                "user_id": user_id,
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        return False


def get_plan_limits(plan_type: PlanType) -> Dict[str, Any]:
    """
    Retorna limites do plano especificado.
    
    Args:
        plan_type: Tipo de plano
        
    Returns:
        Dict com limites do plano
    """
    return PLAN_LIMITS.get(plan_type, PLAN_LIMITS[PlanType.FREE])


def check_subscription_expired(subscription: Dict[str, Any]) -> bool:
    """
    Verifica se assinatura está expirada.
    
    Args:
        subscription: Dict com dados da assinatura
        
    Returns:
        True se expirada, False caso contrário
    """
    if subscription.get('plan_type') == PlanType.FREE.value:
        return False  # Plano free nunca expira
    
    end_date = subscription.get('end_date')
    if end_date is None:
        return False  # Sem data de término = não expira
    
    if isinstance(end_date, datetime):
        return datetime.now() > end_date
    
    # Se for timestamp do Firestore
    if hasattr(end_date, 'timestamp'):
        return datetime.now() > datetime.fromtimestamp(end_date.timestamp())
    
    return False


def renew_subscription(subscription_id: str) -> Tuple[bool, str]:
    """
    Renova assinatura por mais 30 dias.
    
    Args:
        subscription_id: ID da assinatura
        
    Returns:
        Tuple[sucesso, mensagem]
    """
    logger.info(f"renew_subscription_started: {subscription_id}")
    
    db = get_db()
    if not db:
        logger.error("renew_subscription_failed: Banco offline")
        return False, "Banco Offline."
    
    try:
        subscription_ref = db.collection('subscriptions').document(subscription_id)
        subscription = subscription_ref.get()
        
        if not subscription.exists:
            return False, "Assinatura não encontrada."
        
        subscription_data = subscription.to_dict()
        current_end = subscription_data.get('end_date')
        
        # Calcula nova data de término
        if current_end:
            if isinstance(current_end, datetime):
                new_end = current_end + timedelta(days=30)
            elif hasattr(current_end, 'timestamp'):
                new_end = datetime.fromtimestamp(current_end.timestamp()) + timedelta(days=30)
            else:
                new_end = datetime.now() + timedelta(days=30)
        else:
            new_end = datetime.now() + timedelta(days=30)
        
        subscription_ref.update({
            'end_date': new_end,
            'status': SubscriptionStatus.ACTIVE.value,
            'updated_at': firestore.SERVER_TIMESTAMP
        })
        
        logger.info(f"renew_subscription_success: {subscription_id}")
        return True, "Assinatura renovada com sucesso!"
        
    except Exception as e:
        logger.error(
            "renew_subscription_error",
            extra={
                "subscription_id": subscription_id,
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        return False, f"Erro ao renovar assinatura: {str(e)}"

