"""
View de Planos e Preços
"""
import streamlit as st
from modules import ui_components

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
                <button style="
                    width: 100%;
                    padding: 12px;
                    background: linear-gradient(135deg, #FFD700, #FFA500);
                    color: #000;
                    border: none;
                    border-radius: 8px;
                    font-weight: 600;
                    cursor: pointer;
                ">Começar Grátis</button>
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
                <button style="
                    width: 100%;
                    padding: 12px;
                    background: linear-gradient(135deg, #FFD700, #FFA500);
                    color: #000;
                    border: none;
                    border-radius: 8px;
                    font-weight: 600;
                    cursor: pointer;
                ">Assinar Agora</button>
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
                <button style="
                    width: 100%;
                    padding: 12px;
                    background: linear-gradient(135deg, #FFD700, #FFA500);
                    color: #000;
                    border: none;
                    border-radius: 8px;
                    font-weight: 600;
                    cursor: pointer;
                ">Assinar Agora</button>
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
                <button style="
                    width: 100%;
                    padding: 12px;
                    background: linear-gradient(135deg, #FFD700, #FFA500);
                    color: #000;
                    border: none;
                    border-radius: 8px;
                    font-weight: 600;
                    cursor: pointer;
                ">Falar com Vendas</button>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # Comparação de recursos
    st.markdown("### 📊 Comparação de Recursos")
    
    comparison_data = {
        "Recurso": ["Usuários", "Histórico de Dados", "Relatórios/Mês", "API Access", "Suporte", "Integrações"],
        "Free": ["1", "30 dias", "5", "❌", "Email", "❌"],
        "Starter": ["3", "90 dias", "20", "❌", "Prioritário", "❌"],
        "Professional": ["10", "Completo", "Ilimitado", "✅", "Prioritário", "✅"],
        "Enterprise": ["Ilimitado", "Completo", "Ilimitado", "✅", "Dedicado", "✅"]
    }
    
    st.dataframe(pd.DataFrame(comparison_data), use_container_width=True, hide_index=True)

