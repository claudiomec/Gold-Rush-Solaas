"""
View de Planos e Preços
"""
import streamlit as st
import pandas as pd
from modules import ui_components, subscription, plan_limits
from modules.subscription import PlanType

def view_pricing():
    """Página de planos e preços."""
    st.title("💎 Planos e Preços")
    st.markdown("**Escolha o plano ideal para suas necessidades**")
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Planos
    col1, col2, col3, col4 = st.columns(4)
    
    # Plano Free
    with col1:
        st.markdown("""
            <div style="
                background: linear-gradient(135deg, rgba(26, 35, 50, 0.95), rgba(20, 27, 45, 0.95));
                border: 1px solid rgba(255, 215, 0, 0.2);
                border-radius: 16px;
                padding: 2rem;
                height: 100%;
                text-align: center;
            ">
                <h3 style="color: #FFD700; margin-bottom: 1rem;">Free</h3>
                <div style="font-size: 2.5rem; font-weight: 700; color: #FFFFFF; margin: 1rem 0;">
                    R$ 0
                    <span style="font-size: 1rem; color: #B8C5D6;">/mês</span>
                </div>
                <ul style="text-align: left; color: #B8C5D6; padding-left: 1.5rem; margin: 1.5rem 0;">
                    <li>1 usuário</li>
                    <li>Dados últimos 30 dias</li>
                    <li>5 relatórios/mês</li>
                    <li>Suporte por email</li>
                </ul>
        """, unsafe_allow_html=True)
        
        if st.button("Começar Grátis", key="btn_free", use_container_width=True):
            user_id = st.session_state.get('user_name')
            if user_id:
                ok, msg, sub_id = subscription.create_subscription(user_id, PlanType.FREE)
                if ok:
                    st.success("✅ Plano Free ativado!")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")
            else:
                st.warning("Você precisa estar logado para alterar seu plano.")
        st.markdown("""
            </div>
        """, unsafe_allow_html=True)
    
    # Plano Starter
    with col2:
        st.markdown("""
            <div style="
                background: linear-gradient(135deg, rgba(255, 215, 0, 0.1), rgba(255, 165, 0, 0.05));
                border: 2px solid rgba(255, 215, 0, 0.5);
                border-radius: 16px;
                padding: 2rem;
                height: 100%;
                text-align: center;
                position: relative;
            ">
                <div style="
                    position: absolute;
                    top: -12px;
                    left: 50%;
                    transform: translateX(-50%);
                    background: linear-gradient(135deg, #FFD700, #FFA500);
                    color: #000;
                    padding: 4px 16px;
                    border-radius: 20px;
                    font-size: 0.75rem;
                    font-weight: 700;
                ">MAIS POPULAR</div>
                <h3 style="color: #FFD700; margin-top: 1rem; margin-bottom: 1rem;">Starter</h3>
                <div style="font-size: 2.5rem; font-weight: 700; color: #FFFFFF; margin: 1rem 0;">
                    R$ 299
                    <span style="font-size: 1rem; color: #B8C5D6;">/mês</span>
                </div>
                <ul style="text-align: left; color: #B8C5D6; padding-left: 1.5rem; margin: 1.5rem 0;">
                    <li>3 usuários</li>
                    <li>Dados últimos 90 dias</li>
                    <li>20 relatórios/mês</li>
                    <li>Suporte prioritário</li>
                </ul>
        """, unsafe_allow_html=True)
        
        if st.button("Assinar Agora", key="btn_starter", use_container_width=True):
            user_id = st.session_state.get('user_name')
            if user_id:
                try:
                    from modules import payment
                    from modules.subscription import PlanType
                    base_url = "https://gold-rush.streamlit.app"  # TODO: Pegar de config
                    success_url = f"{base_url}/?checkout=success&session_id={{CHECKOUT_SESSION_ID}}"
                    cancel_url = f"{base_url}/?checkout=cancel"
                    
                    ok, msg, checkout_url = payment.create_checkout_session(
                        user_id=user_id,
                        plan_type=PlanType.STARTER,
                        success_url=success_url,
                        cancel_url=cancel_url
                    )
                    
                    if ok and checkout_url:
                        st.success("💳 Redirecionando para checkout...")
                        st.markdown(f"[Clique aqui para continuar o pagamento]({checkout_url})")
                    else:
                        st.warning(f"⚠️ {msg}")
                except Exception as e:
                    st.warning(f"⚠️ Integração com gateway de pagamento em desenvolvimento. Erro: {e}")
            else:
                st.warning("Você precisa estar logado para assinar um plano.")
        st.markdown("""
            </div>
        """, unsafe_allow_html=True)
    
    # Plano Professional
    with col3:
        st.markdown("""
            <div style="
                background: linear-gradient(135deg, rgba(26, 35, 50, 0.95), rgba(20, 27, 45, 0.95));
                border: 1px solid rgba(255, 215, 0, 0.2);
                border-radius: 16px;
                padding: 2rem;
                height: 100%;
                text-align: center;
            ">
                <h3 style="color: #FFD700; margin-bottom: 1rem;">Professional</h3>
                <div style="font-size: 2.5rem; font-weight: 700; color: #FFFFFF; margin: 1rem 0;">
                    R$ 799
                    <span style="font-size: 1rem; color: #B8C5D6;">/mês</span>
                </div>
                <ul style="text-align: left; color: #B8C5D6; padding-left: 1.5rem; margin: 1.5rem 0;">
                    <li>10 usuários</li>
                    <li>Dados completos</li>
                    <li>Relatórios ilimitados</li>
                    <li>API access</li>
                    <li>Suporte prioritário</li>
                </ul>
        """, unsafe_allow_html=True)
        
        if st.button("Assinar Agora", key="btn_professional", use_container_width=True):
            user_id = st.session_state.get('user_name')
            if user_id:
                try:
                    from modules import payment
                    from modules.subscription import PlanType
                    base_url = "https://gold-rush.streamlit.app"  # TODO: Pegar de config
                    success_url = f"{base_url}/?checkout=success&session_id={{CHECKOUT_SESSION_ID}}"
                    cancel_url = f"{base_url}/?checkout=cancel"
                    
                    ok, msg, checkout_url = payment.create_checkout_session(
                        user_id=user_id,
                        plan_type=PlanType.PROFESSIONAL,
                        success_url=success_url,
                        cancel_url=cancel_url
                    )
                    
                    if ok and checkout_url:
                        st.success("💳 Redirecionando para checkout...")
                        st.markdown(f"[Clique aqui para continuar o pagamento]({checkout_url})")
                    else:
                        st.warning(f"⚠️ {msg}")
                except Exception as e:
                    st.warning(f"⚠️ Integração com gateway de pagamento em desenvolvimento. Erro: {e}")
            else:
                st.warning("Você precisa estar logado para assinar um plano.")
        st.markdown("""
            </div>
        """, unsafe_allow_html=True)
    
    # Plano Enterprise
    with col4:
        st.markdown("""
            <div style="
                background: linear-gradient(135deg, rgba(26, 35, 50, 0.95), rgba(20, 27, 45, 0.95));
                border: 1px solid rgba(255, 215, 0, 0.2);
                border-radius: 16px;
                padding: 2rem;
                height: 100%;
                text-align: center;
            ">
                <h3 style="color: #FFD700; margin-bottom: 1rem;">Enterprise</h3>
                <div style="font-size: 2.5rem; font-weight: 700; color: #FFFFFF; margin: 1rem 0;">
                    Custom
                </div>
                <ul style="text-align: left; color: #B8C5D6; padding-left: 1.5rem; margin: 1.5rem 0;">
                    <li>Usuários ilimitados</li>
                    <li>Todos os recursos</li>
                    <li>Integrações custom</li>
                    <li>Suporte dedicado</li>
                    <li>SLA garantido</li>
                </ul>
        """, unsafe_allow_html=True)
        
        if st.button("Falar com Vendas", key="btn_enterprise", use_container_width=True):
            st.info("📧 Entre em contato: vendas@goldrush.com")
        st.markdown("""
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # Informações do plano atual
    user_id = st.session_state.get('user_name')
    if user_id:
        try:
            plan_info = plan_limits.get_user_plan_info(user_id)
            st.markdown("### 📦 Seu Plano Atual")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Plano", plan_info['plan_name'])
            with col2:
                reports_remaining = plan_info['usage']['reports_remaining']
                if reports_remaining is not None:
                    st.metric("Relatórios Restantes", reports_remaining)
                else:
                    st.metric("Relatórios", "Ilimitado")
            with col3:
                max_days = plan_info['limits'].get('max_history_days')
                if max_days:
                    st.metric("Histórico", f"{max_days} dias")
                else:
                    st.metric("Histórico", "Completo")
        except Exception as e:
            st.warning(f"Erro ao carregar informações do plano: {e}")
    
    # Comparação de recursos
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📊 Comparação de Recursos")
    
    comparison_data = {
        "Recurso": ["Usuários", "Histórico de Dados", "Relatórios/Mês", "API Access", "Suporte", "Integrações"],
        "Free": ["1", "30 dias", "5", "❌", "Email", "❌"],
        "Starter": ["3", "90 dias", "20", "❌", "Prioritário", "❌"],
        "Professional": ["10", "Completo", "Ilimitado", "✅", "Prioritário", "✅"],
        "Enterprise": ["Ilimitado", "Completo", "Ilimitado", "✅", "Dedicado", "✅"]
    }
    
    st.dataframe(pd.DataFrame(comparison_data), use_container_width=True, hide_index=True)

