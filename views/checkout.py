"""
View de Checkout - Página de pagamento
"""
import streamlit as st
from modules import payment, subscription
from modules.subscription import PlanType

def view_checkout(plan_type: PlanType):
    """Página de checkout para assinatura."""
    st.title("💳 Checkout")
    
    user_id = st.session_state.get('user_name')
    if not user_id:
        st.error("Você precisa estar logado para fazer checkout.")
        st.info("Por favor, faça login primeiro.")
        return
    
    # Informações do plano
    plan_info = subscription.get_plan_limits(plan_type)
    plan_name = plan_type.value.capitalize()
    price = plan_info.get('price_monthly', 0)
    
    st.markdown(f"### Plano: {plan_name}")
    st.markdown(f"**Preço:** R$ {price:.2f}/mês")
    
    # URL de retorno
    base_url = st.secrets.get("app", {}).get("base_url", "https://gold-rush.streamlit.app")
    success_url = f"{base_url}/?checkout=success&session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{base_url}/?checkout=cancel"
    
    # Cria sessão de checkout
    if st.button("💳 Ir para Pagamento", use_container_width=True):
        with st.spinner("Processando..."):
            ok, msg, checkout_url = payment.create_checkout_session(
                user_id=user_id,
                plan_type=plan_type,
                success_url=success_url,
                cancel_url=cancel_url
            )
            
            if ok and checkout_url:
                st.success("Redirecionando para pagamento...")
                st.markdown(f"[Clique aqui para continuar]({checkout_url})")
                # Em produção, redirecionaria automaticamente
                # st.redirect(checkout_url)
            else:
                st.error(f"❌ {msg}")
    
    # Informações adicionais
    st.markdown("---")
    st.markdown("### ℹ️ Informações")
    st.info("""
    - Pagamento processado de forma segura via Stripe
    - Assinatura renovada automaticamente todo mês
    - Você pode cancelar a qualquer momento
    - Suporte disponível em caso de dúvidas
    """)

