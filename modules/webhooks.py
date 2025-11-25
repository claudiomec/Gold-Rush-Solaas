"""
Módulo de Webhooks - Processamento de eventos de pagamento
Responsável por processar webhooks do Stripe e outros gateways.
"""
import streamlit as st
import logging
import hmac
import hashlib
from typing import Optional, Dict, Any, Tuple
from modules.subscription import PlanType, create_subscription, update_subscription, SubscriptionStatus
from modules.payment import get_stripe_key
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
    logger.warning("stripe não disponível. Webhooks não funcionarão.")


# ============================================================================
# VERIFICAÇÃO DE WEBHOOK
# ============================================================================

def verify_stripe_webhook(payload: bytes, signature: str) -> bool:
    """
    Verifica assinatura do webhook do Stripe.
    
    Args:
        payload: Corpo da requisição (bytes)
        signature: Assinatura do header
        
    Returns:
        True se válido, False caso contrário
    """
    if not HAS_STRIPE:
        return False
    
    try:
        webhook_secret = st.secrets.get("stripe", {}).get("webhook_secret")
        if not webhook_secret:
            logger.warning("verify_stripe_webhook_no_secret")
            return False
        
        stripe.Webhook.construct_event(
            payload,
            signature,
            webhook_secret
        )
        return True
        
    except ValueError:
        logger.warning("verify_stripe_webhook_invalid_payload")
        return False
    except stripe.error.SignatureVerificationError:
        logger.warning("verify_stripe_webhook_invalid_signature")
        return False
    except Exception as e:
        logger.error(
            "verify_stripe_webhook_error",
            extra={
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        return False


# ============================================================================
# PROCESSAMENTO DE EVENTOS
# ============================================================================

def handle_stripe_event(event_type: str, event_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Processa evento do Stripe.
    
    Args:
        event_type: Tipo do evento
        event_data: Dados do evento
        
    Returns:
        Tuple[sucesso, mensagem]
    """
    logger.info(
        "handle_stripe_event_started",
        extra={
            "event_type": event_type
        }
    )
    
    try:
        if event_type == 'checkout.session.completed':
            # Checkout completado
            session = event_data.get('object', {})
            user_id = session.get('metadata', {}).get('user_id')
            plan_type_str = session.get('metadata', {}).get('plan_type')
            customer_id = session.get('customer')
            subscription_id = session.get('subscription')
            
            if user_id and plan_type_str:
                plan_type = PlanType(plan_type_str)
                ok, msg, sub_id = create_subscription(
                    user_id=user_id,
                    plan_type=plan_type,
                    payment_method='stripe',
                    stripe_customer_id=customer_id,
                    stripe_subscription_id=subscription_id
                )
                
                if ok:
                    logger.info(f"handle_stripe_event_subscription_created: {user_id}, {plan_type.value}")
                    return True, f"Assinatura criada: {plan_type.value}"
                else:
                    return False, f"Erro ao criar assinatura: {msg}"
        
        elif event_type == 'customer.subscription.updated':
            # Assinatura atualizada
            subscription = event_data.get('object', {})
            subscription_id = subscription.get('id')
            status = subscription.get('status')
            
            # Busca assinatura no Firestore
            db = get_db()
            if db:
                subscriptions_ref = db.collection('subscriptions')
                query = subscriptions_ref.where('stripe_subscription_id', '==', subscription_id).limit(1)
                docs = list(query.stream())
                
                if docs:
                    doc_ref = docs[0].reference
                    updates = {}
                    
                    if status == 'active':
                        updates['status'] = SubscriptionStatus.ACTIVE.value
                    elif status in ['canceled', 'unpaid', 'past_due']:
                        updates['status'] = SubscriptionStatus.CANCELLED.value
                    
                    if updates:
                        doc_ref.update(updates)
                        logger.info(f"handle_stripe_event_subscription_updated: {subscription_id}")
                        return True, "Assinatura atualizada"
        
        elif event_type == 'customer.subscription.deleted':
            # Assinatura cancelada
            subscription = event_data.get('object', {})
            subscription_id = subscription.get('id')
            
            # Cancela assinatura no Firestore
            db = get_db()
            if db:
                subscriptions_ref = db.collection('subscriptions')
                query = subscriptions_ref.where('stripe_subscription_id', '==', subscription_id).limit(1)
                docs = list(query.stream())
                
                if docs:
                    doc_ref = docs[0].reference
                    doc_ref.update({
                        'status': SubscriptionStatus.CANCELLED.value
                    })
                    logger.info(f"handle_stripe_event_subscription_deleted: {subscription_id}")
                    return True, "Assinatura cancelada"
        
        elif event_type == 'invoice.payment_succeeded':
            # Pagamento bem-sucedido
            invoice = event_data.get('object', {})
            subscription_id = invoice.get('subscription')
            
            # Renova assinatura se necessário
            db = get_db()
            if db:
                subscriptions_ref = db.collection('subscriptions')
                query = subscriptions_ref.where('stripe_subscription_id', '==', subscription_id).limit(1)
                docs = list(query.stream())
                
                if docs:
                    subscription_data = docs[0].to_dict()
                    from modules.subscription import renew_subscription
                    ok, msg = renew_subscription(docs[0].id)
                    if ok:
                        logger.info(f"handle_stripe_event_subscription_renewed: {subscription_id}")
                        return True, "Assinatura renovada"
        
        elif event_type == 'invoice.payment_failed':
            # Pagamento falhou
            invoice = event_data.get('object', {})
            subscription_id = invoice.get('subscription')
            
            logger.warning(f"handle_stripe_event_payment_failed: {subscription_id}")
            # TODO: Enviar notificação ao usuário
        
        else:
            logger.debug(f"handle_stripe_event_unhandled: {event_type}")
            return True, f"Evento {event_type} não requer ação"
        
        return True, "Evento processado"
        
    except Exception as e:
        logger.error(
            "handle_stripe_event_error",
            extra={
                "event_type": event_type,
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        return False, f"Erro ao processar evento: {str(e)}"


def process_webhook(
    payload: bytes,
    signature: Optional[str] = None,
    source: str = 'stripe'
) -> Tuple[bool, str]:
    """
    Processa webhook genérico.
    
    Args:
        payload: Corpo da requisição
        signature: Assinatura (opcional)
        source: Fonte do webhook ('stripe', 'pagseguro', etc.)
        
    Returns:
        Tuple[sucesso, mensagem]
    """
    logger.info(f"process_webhook_started: {source}")
    
    if source == 'stripe':
        if not signature:
            return False, "Assinatura do webhook necessária"
        
        if not verify_stripe_webhook(payload, signature):
            return False, "Assinatura inválida"
        
        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                st.secrets.get("stripe", {}).get("webhook_secret")
            )
            
            event_type = event['type']
            event_data = event['data']
            
            return handle_stripe_event(event_type, event_data)
            
        except Exception as e:
            logger.error(
                "process_webhook_stripe_error",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                exc_info=True
            )
            return False, f"Erro ao processar webhook: {str(e)}"
    
    else:
        return False, f"Fonte de webhook não suportada: {source}"

