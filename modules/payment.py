"""
Módulo de Payment - Integração com gateway de pagamento
Responsável por processar pagamentos e gerenciar checkout.
"""
import streamlit as st
import logging
from typing import Optional, Dict, Any, Tuple
from modules.subscription import PlanType, create_subscription
from modules.database import get_db

# Configuração de logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Tenta importar Stripe (opcional)
try:
    import stripe
    HAS_STRIPE = True
except ImportError:
    HAS_STRIPE = False
    logger.warning("stripe não disponível. Funcionalidades de pagamento serão limitadas.")


# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

def get_stripe_key() -> Optional[str]:
    """Retorna chave do Stripe dos secrets."""
    try:
        if "stripe" in st.secrets:
            return st.secrets["stripe"].get("secret_key")
        return None
    except Exception:
        return None


def get_stripe_publishable_key() -> Optional[str]:
    """Retorna chave pública do Stripe dos secrets."""
    try:
        if "stripe" in st.secrets:
            return st.secrets["stripe"].get("publishable_key")
        return None
    except Exception:
        return None


# ============================================================================
# FUNÇÕES DE PAGAMENTO
# ============================================================================

def create_checkout_session(
    user_id: str,
    plan_type: PlanType,
    success_url: str,
    cancel_url: str
) -> Tuple[bool, str, Optional[str]]:
    """
    Cria sessão de checkout no Stripe.
    
    Args:
        user_id: ID do usuário
        plan_type: Tipo de plano
        success_url: URL de sucesso
        cancel_url: URL de cancelamento
        
    Returns:
        Tuple[sucesso, mensagem, checkout_url]
    """
    logger.info(
        "create_checkout_session_started",
        extra={
            "user_id": user_id,
            "plan_type": plan_type.value
        }
    )
    
    if not HAS_STRIPE:
        logger.warning("create_checkout_session_stripe_not_available")
        return False, "Stripe não configurado. Entre em contato com o suporte.", None
    
    stripe_key = get_stripe_key()
    if not stripe_key:
        logger.warning("create_checkout_session_no_stripe_key")
        return False, "Chave do Stripe não configurada.", None
    
    try:
        stripe.api_key = stripe_key
        
        # Preços dos planos (em centavos)
        plan_prices = {
            PlanType.STARTER: 29900,  # R$ 299.00
            PlanType.PROFESSIONAL: 79900,  # R$ 799.00
        }
        
        if plan_type not in plan_prices:
            return False, f"Plano {plan_type.value} não disponível para checkout online.", None
        
        # Cria sessão de checkout
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'brl',
                    'product_data': {
                        'name': f'Gold Rush Analytics - {plan_type.value.capitalize()}',
                        'description': f'Assinatura mensal do plano {plan_type.value.capitalize()}'
                    },
                    'unit_amount': plan_prices[plan_type],
                    'recurring': {
                        'interval': 'month'
                    }
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'user_id': user_id,
                'plan_type': plan_type.value
            },
            customer_email=user_id  # Assume que user_id é o email
        )
        
        checkout_url = checkout_session.url
        session_id = checkout_session.id
        
        logger.info(
            "create_checkout_session_success",
            extra={
                "user_id": user_id,
                "plan_type": plan_type.value,
                "session_id": session_id
            }
        )
        
        return True, "Checkout criado com sucesso!", checkout_url
        
    except Exception as e:
        logger.error(
            "create_checkout_session_error",
            extra={
                "user_id": user_id,
                "plan_type": plan_type.value,
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        return False, f"Erro ao criar checkout: {str(e)}", None


def handle_payment_success(session_id: str) -> Tuple[bool, str]:
    """
    Processa pagamento bem-sucedido.
    
    Args:
        session_id: ID da sessão do Stripe
        
    Returns:
        Tuple[sucesso, mensagem]
    """
    logger.info(f"handle_payment_success_started: {session_id}")
    
    if not HAS_STRIPE:
        return False, "Stripe não configurado."
    
    stripe_key = get_stripe_key()
    if not stripe_key:
        return False, "Chave do Stripe não configurada."
    
    try:
        stripe.api_key = stripe_key
        session = stripe.checkout.Session.retrieve(session_id)
        
        user_id = session.metadata.get('user_id')
        plan_type_str = session.metadata.get('plan_type')
        
        if not user_id or not plan_type_str:
            return False, "Dados da sessão inválidos."
        
        plan_type = PlanType(plan_type_str)
        customer_id = session.customer
        
        # Cria assinatura
        ok, msg, sub_id = create_subscription(
            user_id=user_id,
            plan_type=plan_type,
            payment_method='stripe',
            stripe_customer_id=customer_id,
            stripe_subscription_id=session.subscription
        )
        
        if ok:
            logger.info(f"handle_payment_success: {user_id}, {plan_type.value}")
            return True, f"Pagamento processado! Plano {plan_type.value} ativado."
        else:
            return False, f"Erro ao criar assinatura: {msg}"
        
    except Exception as e:
        logger.error(
            "handle_payment_success_error",
            extra={
                "session_id": session_id,
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        return False, f"Erro ao processar pagamento: {str(e)}"


def cancel_subscription_payment(stripe_subscription_id: str) -> Tuple[bool, str]:
    """
    Cancela assinatura no Stripe.
    
    Args:
        stripe_subscription_id: ID da assinatura no Stripe
        
    Returns:
        Tuple[sucesso, mensagem]
    """
    logger.info(f"cancel_subscription_payment_started: {stripe_subscription_id}")
    
    if not HAS_STRIPE:
        return False, "Stripe não configurado."
    
    stripe_key = get_stripe_key()
    if not stripe_key:
        return False, "Chave do Stripe não configurada."
    
    try:
        stripe.api_key = stripe_key
        subscription = stripe.Subscription.retrieve(stripe_subscription_id)
        subscription.cancel()
        
        logger.info(f"cancel_subscription_payment_success: {stripe_subscription_id}")
        return True, "Assinatura cancelada com sucesso!"
        
    except Exception as e:
        logger.error(
            "cancel_subscription_payment_error",
            extra={
                "stripe_subscription_id": stripe_subscription_id,
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        return False, f"Erro ao cancelar assinatura: {str(e)}"


def get_payment_status(stripe_subscription_id: str) -> Optional[Dict[str, Any]]:
    """
    Busca status do pagamento no Stripe.
    
    Args:
        stripe_subscription_id: ID da assinatura no Stripe
        
    Returns:
        Dict com status do pagamento ou None
    """
    if not HAS_STRIPE:
        return None
    
    stripe_key = get_stripe_key()
    if not stripe_key:
        return None
    
    try:
        stripe.api_key = stripe_key
        subscription = stripe.Subscription.retrieve(stripe_subscription_id)
        
        return {
            'status': subscription.status,
            'current_period_end': subscription.current_period_end,
            'cancel_at_period_end': subscription.cancel_at_period_end
        }
        
    except Exception as e:
        logger.error(
            "get_payment_status_error",
            extra={
                "stripe_subscription_id": stripe_subscription_id,
                "error": str(e)
            },
            exc_info=True
        )
        return None

