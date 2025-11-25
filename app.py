import streamlit as st
import pandas as pd
import logging
from modules import auth, database, data_engine, ui_components, report_generator, email_service, analytics, notifications, filters, help, subscription, plan_limits
try:
    from views import pricing
except ImportError:
    # Fallback se views não existir
    pricing = None
from datetime import datetime
import io
import re
import time

# Configuração de logging
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Gold Rush Analytics", page_icon="🏭", layout="wide", initial_sidebar_state="expanded")
ui_components.load_custom_css()

# --- INTERCEPTADOR DE TOKEN ---
qp = st.query_params
if "verify_token" in qp:
    with st.spinner("Validando..."):
        ok, msg = database.verify_user_token(qp["verify_token"])
        if ok: 
            st.success(f"✅ {msg}")
            st.balloons()
        else: st.error(f"❌ {msg}")
    st.query_params.clear()

def is_valid_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email) is not None

# --- VIEWS ---
def view_monitor(is_admin):
    with st.sidebar:
        st.markdown("### ⚙️ Parâmetros de Cálculo")
        st.markdown("---")
        ocean = st.slider("🌊 Frete Marítimo (USD)", 0, 300, 60, 10, help="Custo do frete marítimo em dólares")
        icms = st.selectbox("📊 ICMS (%)", [18, 12, 7, 4], help="Alíquota de ICMS aplicável")
        freight = st.slider("🚚 Frete Interno", 0.0, 0.5, 0.15, 0.01, help="Taxa de frete interno")
        margin = st.slider("💼 Margem (%)", 0, 20, 10, help="Margem de lucro desejada")
        st.markdown("---")
        
        # Filtros rápidos
        period, trend = filters.render_quick_filters()
        st.markdown("---")
        st.button("🚪 Sair", key='lo1', on_click=auth.logout, use_container_width=True)

    st.title("📊 Monitor de Custo Industrial")
    col_t, col_b = st.columns([3, 1])
    with col_t: 
        st.markdown("**Commodity:** <span style='color: #FFD700; font-weight: 600;'>Polipropileno</span>", unsafe_allow_html=True)
    
    # Verifica limites do plano
    user_id = st.session_state.get('user_name')
    if user_id:
        plan_info = plan_limits.get_user_plan_info(user_id)
        max_days = plan_info['limits'].get('max_history_days')
        if max_days:
            st.info(f"📦 Plano {plan_info['plan_name']}: Acessando últimos {max_days} dias de dados")
    
    with st.spinner('⚙️ Calculando métricas...'):
        # Aplica limite de histórico baseado no plano
        days_back = 180  # Padrão
        if user_id:
            plan_info = plan_limits.get_user_plan_info(user_id)
            max_days = plan_info['limits'].get('max_history_days')
            if max_days:
                days_back = min(days_back, max_days)
        
        df_raw = data_engine.get_market_data(days_back=days_back)
        df = data_engine.calculate_cost_buildup(df_raw, ocean, freight, icms, margin)
        
        # Aplica filtros rápidos
        df = filters.apply_quick_filters(df, period, trend)
        
        if df.empty:
            st.warning("⚠️ Nenhum dado encontrado com os filtros selecionados.")
            return
        
        curr = df['PP_Price'].iloc[-1]
        var = (curr/df['PP_Price'].iloc[-7]-1)*100 if len(df) >= 7 else 0
        
        with col_b:
            # Verifica limite de relatórios
            user_id = st.session_state.get('user_name')
            can_generate, error_msg, reports_remaining = plan_limits.check_reports_limit(user_id) if user_id else (True, None, None)
            
            if can_generate:
                sug = "Alta" if var > 0.5 else "Baixa" if var < -0.5 else "Estavel"
                pdf = report_generator.generate_pdf_report(df, curr, var, ocean, df['USD_BRL'].iloc[-1], sug)
                help_text = "Baixe o relatório completo em PDF"
                if reports_remaining is not None:
                    help_text += f" ({reports_remaining} restantes este mês)"
                st.download_button(
                    "📄 Baixar Laudo PDF", 
                    pdf, 
                    "Laudo_Gold_Rush.pdf", 
                    "application/pdf", 
                    use_container_width=True,
                    help=help_text
                )
            else:
                st.error(f"🚫 {error_msg}")
                if user_id:
                    plan_info = plan_limits.get_user_plan_info(user_id)
                    if plan_info['plan_type'] != 'enterprise':
                        st.info("💡 Faça upgrade do seu plano para gerar mais relatórios!")
        
        # Métricas modernas
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            ui_components.render_modern_card(
                "Preço Final", 
                f"R$ {curr:.2f}",
                "Preço atual do commodity",
                "💰",
                "gold"
            )
        with c2:
            trend_icon = "📈" if var > 0 else "📉" if var < 0 else "➡️"
            trend_color = "red" if var > 0.5 else "green" if var < -0.5 else "blue"
            ui_components.render_modern_card(
                "Tendência", 
                f"{var:+.2f}%",
                "Variação semanal",
                trend_icon,
                trend_color
            )
        with c3:
            ui_components.render_modern_card(
                "Frete Marítimo", 
                f"USD {ocean}",
                "Custo do transporte",
                "🌊",
                "blue"
            )
        with c4:
            ui_components.render_modern_card(
                "Taxa USD/BRL", 
                f"R$ {df['USD_BRL'].iloc[-1]:.4f}",
                "Cotação atual",
                "💵",
                "gold"
            )
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Métricas de Confiança (NOVO)
        try:
            confidence_metrics = data_engine.calculate_price_confidence(df, curr)
            if confidence_metrics:
                st.markdown("### 🎯 Confiança nos Dados")
                conf_col1, conf_col2, conf_col3 = st.columns(3)
                
                with conf_col1:
                    confidence_score = confidence_metrics.get('confidence_score', 0)
                    confidence_color = "green" if confidence_score >= 0.8 else "orange" if confidence_score >= 0.6 else "red"
                    ui_components.render_modern_card(
                        "Score de Confiança",
                        f"{confidence_score:.1%}",
                        confidence_metrics.get('recommendation', ''),
                        "🎯",
                        confidence_color
                    )
                
                with conf_col2:
                    freshness = confidence_metrics.get('data_freshness_days', 'N/A')
                    freshness_text = f"{freshness} dias" if isinstance(freshness, int) else "N/A"
                    ui_components.render_modern_card(
                        "Atualidade dos Dados",
                        freshness_text,
                        "Dias desde última atualização",
                        "📅",
                        "blue"
                    )
                
                with conf_col3:
                    completeness = confidence_metrics.get('data_completeness', 0)
                    ui_components.render_modern_card(
                        "Completude",
                        f"{completeness:.1%}",
                        "Percentual de dados completos",
                        "📊",
                        "gold"
                    )
                
                # Recomendação
                if confidence_score < 0.6:
                    st.warning(f"⚠️ **Atenção:** {confidence_metrics.get('recommendation', '')}")
                elif confidence_score >= 0.8:
                    st.success(f"✅ {confidence_metrics.get('recommendation', '')}")
                else:
                    st.info(f"ℹ️ {confidence_metrics.get('recommendation', '')}")
                
                st.markdown("<br>", unsafe_allow_html=True)
        except Exception as e:
            logger.warning(f"Erro ao calcular métricas de confiança: {e}")
        
        # Opção de visualização avançada
        show_advanced = st.checkbox("📊 Mostrar gráfico avançado com métricas", value=False)
        
        if show_advanced:
            ui_components.render_advanced_metrics_chart(df)
        else:
            ui_components.render_price_chart(df, show_advanced=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Análise de Sensibilidade (NOVO)
        with st.expander("🔬 Análise de Sensibilidade dos Parâmetros"):
            st.markdown("**Veja como cada parâmetro afeta o preço final**")
            
            if st.button("Calcular Análise de Sensibilidade", use_container_width=True):
                with st.spinner("Calculando impacto de cada parâmetro..."):
                    try:
                        base_params = {
                            'ocean_freight': ocean,
                            'freight_internal': freight,
                            'icms': icms,
                            'margin': margin
                        }
                        
                        ranges = {
                            'ocean_freight': (-10, +10),
                            'icms': (-2, +2),
                            'margin': (-2, +2),
                            'freight_internal': (-0.05, +0.05)
                        }
                        
                        sensitivity_df = data_engine.sensitivity_analysis(base_params, ranges)
                        
                        if not sensitivity_df.empty:
                            st.markdown("#### 📈 Impacto no Preço Final")
                            st.dataframe(
                                sensitivity_df[['parameter', 'change', 'price_impact', 'price_impact_pct', 'sensitivity_rank']],
                                use_container_width=True,
                                hide_index=True
                            )
                            
                            # Gráfico de sensibilidade
                            if 'price_impact_pct' in sensitivity_df.columns:
                                st.bar_chart(
                                    sensitivity_df.groupby('parameter')['sensitivity_rank'].max().sort_values(ascending=False),
                                    height=300
                                )
                            
                            st.info("💡 **Interpretação:** Valores maiores indicam maior impacto no preço final quando o parâmetro varia.")
                        else:
                            st.warning("Não foi possível calcular a análise de sensibilidade no momento.")
                    except Exception as e:
                        st.error(f"Erro ao calcular análise de sensibilidade: {e}")
        
        ui_components.render_insight_card(var)

def view_calculator():
    with st.sidebar: 
        st.markdown("### 💰 Calculadora Financeira")
        st.markdown("---")
        st.button("🚪 Sair", key='lo2', on_click=auth.logout, use_container_width=True)
    
    st.title("💰 Calculadora Financeira")
    st.markdown("**Calcule o impacto financeiro da sua compra comparando com o preço justo de mercado**")
    st.markdown("<br>", unsafe_allow_html=True)
    
    fair = data_engine.get_fair_price_snapshot()
    c1, c2 = st.columns([1, 1])
    
    with c1:
        st.markdown("### 📝 Dados da Compra")
        curr = st.number_input(
            "💵 Preço Pago (R$/kg)", 
            value=10.50, 
            min_value=0.0, 
            step=0.01,
            help="Preço que você pagou ou pretende pagar"
        )
        vol_ton = st.number_input(
            "📦 Volume (Toneladas)", 
            value=50.0, 
            min_value=0.0, 
            step=0.1,
            help="Quantidade em toneladas"
        )
        vol = vol_ton * 1000  # Converter para kg
    
    with c2:
        st.markdown("### 💎 Análise de Mercado")
        delta = curr - fair
        
        # Card de Preço Justo
        ui_components.render_modern_card(
            "Preço Justo de Mercado",
            f"R$ {fair:.2f}",
            "Baseado em análise de custos",
            "⭐",
            "gold"
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Card de Resultado
        if delta > 0:
            loss_amount = delta * vol
            ui_components.render_modern_card(
                "🔴 Perda Potencial",
                f"R$ {loss_amount:,.2f}",
                f"Você pagou R$ {delta:.2f}/kg acima do justo",
                "⚠️",
                "red"
            )
            st.warning(f"💡 **Recomendação:** Considere negociar ou aguardar uma melhor oportunidade de compra.")
        elif delta < 0:
            savings_amount = abs(delta) * vol
            ui_components.render_modern_card(
                "🟢 Economia Realizada",
                f"R$ {savings_amount:,.2f}",
                f"Você economizou R$ {abs(delta):.2f}/kg",
                "✅",
                "green"
            )
            st.success(f"🎉 **Excelente negócio!** Você está comprando abaixo do preço justo de mercado.")
        else:
            ui_components.render_modern_card(
                "⚖️ Preço Equilibrado",
                "R$ 0,00",
                "Preço alinhado com o mercado",
                "✓",
                "blue"
            )
            st.info("💡 **Análise:** Seu preço está alinhado com o mercado justo.")

def view_admin_users():
    st.title("👥 Gestão de Acessos")
    t1, t2, t3 = st.tabs(["Novo", "Editar / Corrigir", "Listar"])
    
    # ABA 1: Novo
    with t1:
        with st.form("new"):
            c1, c2 = st.columns(2)
            u = c1.text_input("Login (E-mail)"); p = c1.text_input("Senha", type="password")
            n = c2.text_input("Nome"); r = c2.selectbox("Perfil", ["client", "admin"])
            m = st.multiselect("Módulos", ["Monitor", "Calculadora Financeira"], ["Monitor"])
            if st.form_submit_button("Criar"):
                if not is_valid_email(u): st.error("E-mail inválido.")
                else:
                    ok, msg, token = database.create_user(u, u, p, n, r, m)
                    if ok:
                        # Ajuste a URL para produção
                        link = f"https://gold-rush.streamlit.app/?verify_token={token}"
                        email_service.send_verification_email(u, link)
                        st.success(f"Usuário criado! E-mail enviado para {u}")
                    else: st.error(msg)

    # ABA 2: Editar (Atualizada)
    with t2:
        st.caption("Se alterar o e-mail, o usuário será bloqueado até revalidar.")
        users = database.list_all_users()
        if users:
            opts = {f"{u['username']} - {u.get('name','')}": u for u in users}
            sel = st.selectbox("Selecione:", list(opts.keys()))
            if sel:
                data = opts[sel]
                with st.form("edit"):
                    st.markdown(f"**Original:** `{data['username']}`")
                    # Campo E-mail Editável
                    new_email = st.text_input("E-mail (Login)", value=data.get('email', data['username']))
                    new_name = st.text_input("Nome", value=data.get('name',''))
                    new_role = st.selectbox("Perfil", ["client", "admin"], index=0 if data.get('role')=='client' else 1)
                    
                    curr_mod = data.get('modules', ["Monitor"])
                    if isinstance(curr_mod, str): curr_mod = ["Monitor"]
                    new_mod = st.multiselect("Módulos", ["Monitor", "Calculadora Financeira"], default=curr_mod)
                    
                    if st.form_submit_button("Salvar Alterações"):
                        if not is_valid_email(new_email):
                            st.error("E-mail inválido.")
                        else:
                            # Chama update com lógica de revalidação
                            ok, msg, token = database.update_user(data['username'], new_email, new_name, new_role, new_mod)
                            
                            if ok:
                                st.success(f"✅ {msg}")
                                # Se retornou token, significa que o email mudou -> Envia validação
                                if token:
                                    link = f"https://gold-rush.streamlit.app/?verify_token={token}"
                                    sent, mail_msg = email_service.send_verification_email(new_email, link)
                                    if sent: st.info(f"📧 Link de revalidação enviado para {new_email}")
                                    else: st.warning(f"Falha no envio de e-mail: {mail_msg}")
                                
                                time.sleep(2)
                                st.rerun()
                            else:
                                st.error(msg)

    # ABA 3: Listar
    with t3:
        if st.button("Atualizar"):
            us = database.list_all_users()
            if us: st.dataframe(pd.DataFrame(us)[['username', 'name', 'email', 'verified', 'role']], use_container_width=True)

def view_dashboard():
    """Dashboard de métricas e analytics do usuário."""
    with st.sidebar:
        st.markdown("### 📊 Dashboard")
        st.markdown("---")
        st.button("🚪 Sair", key='lo_dash', on_click=auth.logout, use_container_width=True)
    
    st.title("📊 Dashboard de Métricas")
    
    col_title, col_help = st.columns([4, 1])
    with col_title:
        st.markdown("**Visão geral do valor entregue e métricas de uso**")
    with col_help:
        if st.button("❓ Ajuda", use_container_width=True):
            st.session_state['show_help'] = True
    
    if st.session_state.get('show_help', False):
        with st.expander("📚 Guia e FAQ", expanded=True):
            help.render_quick_guide()
            st.markdown("---")
            help.render_faq()
            if st.button("Fechar Ajuda"):
                st.session_state['show_help'] = False
                st.rerun()
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Busca métricas do usuário
    metrics = analytics.get_user_metrics()
    usage_stats = analytics.get_usage_stats()
    
    if not metrics:
        st.warning("⚠️ Não foi possível carregar métricas no momento.")
        return
    
    # KPIs Principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        ui_components.render_modern_card(
            "Preço Atual",
            f"R$ {metrics.get('current_price', 0):.2f}",
            "Última cotação",
            "💰",
            "gold"
        )
    
    with col2:
        change_pct = metrics.get('price_change_pct', 0)
        change_icon = "📈" if change_pct > 0 else "📉" if change_pct < 0 else "➡️"
        change_color = "red" if change_pct > 0 else "green" if change_pct < 0 else "blue"
        ui_components.render_modern_card(
            "Variação Total",
            f"{change_pct:+.2f}%",
            f"Nos últimos {metrics.get('total_days_tracked', 0)} dias",
            change_icon,
            change_color
        )
    
    with col3:
        ui_components.render_modern_card(
            "Preço Médio",
            f"R$ {metrics.get('average_price', 0):.2f}",
            "Média histórica",
            "📊",
            "blue"
        )
    
    with col4:
        ui_components.render_modern_card(
            "Dados Rastreados",
            f"{metrics.get('data_points', 0)}",
            "Pontos de dados",
            "📈",
            "green"
        )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Análise de Economia
    st.markdown("### 💰 Análise de Economia Potencial")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        fair_price = data_engine.get_fair_price_snapshot()
        current_price = metrics.get('current_price', 0)
        
        if current_price > 0 and fair_price > 0:
            savings_data = analytics.calculate_savings_potential(current_price, fair_price, 1000)
            
            if savings_data['status'] == 'savings':
                ui_components.render_modern_card(
                    "🟢 Economia Potencial",
                    f"R$ {savings_data['savings']:,.2f}",
                    f"Por tonelada ({savings_data['savings_pct']:.2f}% abaixo do justo)",
                    "✅",
                    "green"
                )
            elif savings_data['status'] == 'loss':
                ui_components.render_modern_card(
                    "🔴 Perda Potencial",
                    f"R$ {savings_data['savings']:,.2f}",
                    f"Por tonelada ({savings_data['savings_pct']:.2f}% acima do justo)",
                    "⚠️",
                    "red"
                )
            else:
                ui_components.render_modern_card(
                    "⚖️ Preço Equilibrado",
                    "R$ 0,00",
                    "Alinhado com o mercado justo",
                    "✓",
                    "blue"
                )
    
    with col_b:
        st.markdown("#### 📈 Insights")
        if metrics.get('price_change_pct', 0) > 5:
            st.success("💡 **Oportunidade:** Preços em alta significativa. Considere antecipar compras.")
        elif metrics.get('price_change_pct', 0) < -5:
            st.info("💡 **Oportunidade:** Preços em queda. Pode ser um bom momento para comprar.")
        else:
            st.info("💡 **Mercado estável.** Mantenha sua programação normal de compras.")
    
    # Estatísticas de Uso
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📊 Estatísticas de Uso")
    
    col_u1, col_u2, col_u3 = st.columns(3)
    
    with col_u1:
        st.metric("Relatórios Gerados", usage_stats.get('reports_generated', 0))
    
    with col_u2:
        last_access = usage_stats.get('last_access', datetime.now())
        if isinstance(last_access, datetime):
            st.metric("Último Acesso", last_access.strftime("%d/%m/%Y"))
        else:
            st.metric("Último Acesso", "Hoje")
    
    with col_u3:
        st.metric("Total de Sessões", usage_stats.get('total_sessions', 0))
    
    # Gráfico de tendência
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📈 Tendência de Preços")
    
    # Aplica limite de histórico baseado no plano
    user_id = st.session_state.get('user_name')
    days_back = 90  # Padrão
    if user_id:
        plan_info = plan_limits.get_user_plan_info(user_id)
        max_days = plan_info['limits'].get('max_history_days')
        if max_days:
            days_back = min(days_back, max_days)
    
    df = data_engine.get_market_data(days_back=days_back)
    if not df.empty and 'PP_Price' in df.columns:
        ui_components.render_price_chart(df)
    else:
        st.info("Dados de mercado não disponíveis no momento.")

def view_backtest():
    st.title("🧪 Lab"); 
    with st.sidebar: st.button("Sair", key='lo4', on_click=auth.logout)
    # ... (código backtest resumido para brevidade) ...
    st.info("Módulo de calibração.")

def view_data_export():
    st.title("💾 Dados"); 
    with st.sidebar: 
        st.button("Sair", key='lo5', on_click=auth.logout)
        st.markdown("---")
        period, trend = filters.render_quick_filters()
    
    # Aplica limite de histórico baseado no plano
    user_id = st.session_state.get('user_name')
    days_back = 365  # Padrão
    if user_id:
        plan_info = plan_limits.get_user_plan_info(user_id)
        max_days = plan_info['limits'].get('max_history_days')
        if max_days:
            days_back = min(days_back, max_days)
            st.info(f"📦 Plano {plan_info['plan_name']}: Acessando últimos {max_days} dias de dados")
    
    df = data_engine.get_market_data(days_back=days_back)
    
    # Aplica filtros
    df = filters.apply_quick_filters(df, period, trend)
    
    # Filtros avançados
    st.markdown("<br>", unsafe_allow_html=True)
    df = filters.render_data_filters(df)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.dataframe(df, use_container_width=True)
    
    # Estatísticas
    if not df.empty:
        st.markdown("### 📊 Estatísticas")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Registros", len(df))
        with col2:
            if 'PP_Price' in df.columns:
                st.metric("Preço Médio", f"R$ {df['PP_Price'].mean():.2f}")
        with col3:
            if isinstance(df.index, pd.DatetimeIndex):
                st.metric("Período", f"{df.index.min().strftime('%d/%m/%Y')} - {df.index.max().strftime('%d/%m/%Y')}")

# --- MAIN ---
if not st.session_state.get("password_correct", False):
    # Login Screen Moderno
    st.markdown("""
        <style>
        .login-container {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 80vh;
            padding: 2rem;
        }
        .login-card {
            background: linear-gradient(135deg, rgba(26, 35, 50, 0.95) 0%, rgba(20, 27, 45, 0.95) 100%);
            border: 1px solid rgba(255, 215, 0, 0.2);
            border-radius: 24px;
            padding: 3rem;
            max-width: 450px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5),
                        0 0 0 1px rgba(255, 215, 0, 0.1) inset;
            animation: slideIn 0.6s ease-out;
        }
        @keyframes slideIn {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .login-logo {
            text-align: center;
            margin-bottom: 2rem;
        }
        .login-title {
            text-align: center;
            color: #FFD700;
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            text-shadow: 0 0 20px rgba(255, 215, 0, 0.3);
        }
        .login-subtitle {
            text-align: center;
            color: #B8C5D6;
            font-size: 0.95rem;
            margin-bottom: 2rem;
        }
        </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
            <div class="login-container">
                <div class="login-card">
                    <div class="login-logo">
                        <div style="font-size: 4rem; margin-bottom: 1rem;">🏭</div>
                    </div>
                    <h1 class="login-title">Gold Rush Analytics</h1>
                    <p class="login-subtitle">Acesso ao Sistema de Monitoramento Industrial</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        with st.form("login", clear_on_submit=False):
            st.markdown("<br>", unsafe_allow_html=True)
            u = st.text_input("📧 E-mail", placeholder="seu@email.com")
            p = st.text_input("🔒 Senha", type="password", placeholder="••••••••")
            st.markdown("<br>", unsafe_allow_html=True)
            
            submitted = st.form_submit_button("🚀 Entrar", use_container_width=True)
            
            if submitted:
                with st.spinner("🔐 Autenticando..."):
                    r = auth.authenticate(u, p)
                    if r and "error" in r: 
                        st.error(f"❌ {r['error']}")
                    elif r:
                        st.success(f"✅ Bem-vindo, {r.get('name', 'Usuário')}!")
                        st.session_state.update({
                            "password_correct": True, 
                            "user_role": r.get("role"), 
                            "user_name": r.get("name"), 
                            "user_modules": r.get("modules", ["Monitor"])
                        })
                        time.sleep(0.5)
                        st.rerun()
                    else: 
                        st.error("❌ Credenciais inválidas. Verifique seu e-mail e senha.")
else:
    role = st.session_state["user_role"]
    with st.sidebar:
        # Header da Sidebar Moderno
        st.markdown("""
            <div style="
                background: linear-gradient(135deg, rgba(255, 215, 0, 0.1), rgba(255, 165, 0, 0.05));
                border: 1px solid rgba(255, 215, 0, 0.2);
                border-radius: 12px;
                padding: 1rem;
                margin-bottom: 1.5rem;
                text-align: center;
            ">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">🏭</div>
                <div style="color: #FFD700; font-weight: 700; font-size: 1.1rem;">Gold Rush</div>
                <div style="color: #B8C5D6; font-size: 0.85rem; margin-top: 0.25rem;">Analytics Platform</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Badge de Usuário
        user_name = st.session_state.get('user_name', 'Usuário')
        if role == "admin": 
            st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, rgba(255, 82, 82, 0.15), rgba(244, 67, 54, 0.1));
                    border: 1px solid rgba(255, 82, 82, 0.3);
                    border-radius: 10px;
                    padding: 0.75rem;
                    margin-bottom: 1rem;
                    text-align: center;
                ">
                    <div style="color: #FF5252; font-weight: 600;">👑 Administrador</div>
                    <div style="color: #FFFFFF; font-size: 0.9rem; margin-top: 0.25rem;">{user_name}</div>
                </div>
            """, unsafe_allow_html=True)
        else: 
            st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, rgba(68, 138, 255, 0.15), rgba(33, 150, 243, 0.1));
                    border: 1px solid rgba(68, 138, 255, 0.3);
                    border-radius: 10px;
                    padding: 0.75rem;
                    margin-bottom: 1rem;
                    text-align: center;
                ">
                    <div style="color: #448AFF; font-weight: 600;">👤 Cliente</div>
                    <div style="color: #FFFFFF; font-size: 0.9rem; margin-top: 0.25rem;">{user_name}</div>
                </div>
            """, unsafe_allow_html=True)
        
        # Renderiza sino de notificações
        notifications.render_notification_bell()
        
        # Informações do plano do usuário
        user_id = st.session_state.get('user_name')
        if user_id:
            try:
                plan_info = plan_limits.get_user_plan_info(user_id)
                plan_name = plan_info['plan_name']
                plan_type = plan_info['plan_type']
                
                # Cor baseada no plano
                if plan_type == 'enterprise':
                    plan_color = "#FFD700"
                elif plan_type == 'professional':
                    plan_color = "#00E676"
                elif plan_type == 'starter':
                    plan_color = "#448AFF"
                else:
                    plan_color = "#B8C5D6"
                
                st.markdown(f"""
                    <div style="
                        background: linear-gradient(135deg, rgba(26, 35, 50, 0.95), rgba(20, 27, 45, 0.95));
                        border: 1px solid {plan_color};
                        border-radius: 10px;
                        padding: 0.75rem;
                        margin-bottom: 1rem;
                        text-align: center;
                    ">
                        <div style="color: {plan_color}; font-weight: 600; font-size: 0.9rem;">📦 Plano {plan_name}</div>
                        {f'<div style="color: #B8C5D6; font-size: 0.75rem; margin-top: 0.25rem;">{plan_info["usage"]["reports_remaining"]} relatórios restantes</div>' if plan_info["usage"]["reports_remaining"] is not None else ''}
                    </div>
                """, unsafe_allow_html=True)
            except Exception as e:
                logger.warning(f"Erro ao buscar informações do plano: {e}")
        
        pg = ui_components.render_sidebar_menu(role, st.session_state.get("user_modules", []))

    # Verifica se é página de notificações via query params
    if st.query_params.get("page") == "notifications":
        notifications.render_notifications_page()
    elif pg == "LOGOUT_ACTION": auth.logout()
    elif pg == "Dashboard": view_dashboard()
    elif pg == "Monitor": view_monitor(role=="admin")
    elif pg == "Calculadora Financeira": view_calculator()
    elif pg == "Usuários": view_admin_users()
    elif pg == "Dados (XLSX)": view_data_export()
    elif pg == "Backtest": view_backtest()
    elif pg == "Planos":
        if pricing:
            pricing.view_pricing()
        else:
            st.error("Módulo de planos não disponível")