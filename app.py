import streamlit as st
import pandas as pd
from modules import auth, database, data_engine, ui_components
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io # Necessário para criar o arquivo Excel na memória

# 1. Configuração Inicial
st.set_page_config(
    page_title="Gold Rush Analytics",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Carrega Estilos Visuais
ui_components.load_custom_css()

# -------------------------------------------------------
# CONTROLADORES DE MÓDULO (Views)
# -------------------------------------------------------

def view_monitor(is_admin):
    """Controlador da Tela de Monitoramento"""
    with st.sidebar:
        if is_admin: st.success(f"Admin: {st.session_state['user_name']}")
        else: st.info(f"Cliente: {st.session_state['user_name']}")
        
        # Status do Banco
        if database.get_db(): st.caption("🟢 Online")
        else: st.caption("🔴 Offline")
        
        st.header("⚙️ Parâmetros")
        ocean = st.slider("Frete Marítimo (USD)", 0, 300, 60, 10)
        icms = st.selectbox("ICMS (%)", [18, 12, 7, 4])
        freight = st.slider("Frete Interno (R$)", 0.0, 0.5, 0.15, 0.01)
        margin = st.slider("Margem (%)", 0, 20, 10)
        st.markdown("---")
        st.button("Sair", key='logout_mon', on_click=auth.logout)

    st.title("Monitor de Custo Industrial: Polipropileno")
    
    with st.spinner('Processando dados de mercado...'):
        # 1. Busca Dados
        raw_df = data_engine.get_market_data()
        
        # 2. Aplica Regras de Negócio
        processed_df = data_engine.calculate_cost_buildup(
            raw_df, ocean, freight, icms, margin
        )
        
        # 3. Prepara KPIs
        current = processed_df['PP_Price'].iloc[-1]
        var_pct = (current / processed_df['PP_Price'].iloc[-7] - 1) * 100
        
        # 4. Renderiza Interface
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Preço Final", f"R$ {current:.2f}", f"{current-processed_df['PP_Price'].iloc[-2]:.2f}")
        c2.metric("Tendência (7d)", f"{var_pct:.2f}%", delta_color="inverse")
        c3.metric("Frete Marítimo", f"USD {ocean}")
        c4.metric("Dólar Base", f"R$ {processed_df['USD_BRL'].iloc[-1]:.4f}")
        
        ui_components.render_price_chart(processed_df)
        ui_components.render_insight_card(var_pct)

def view_calculator():
    """Controlador da Calculadora Financeira"""
    with st.sidebar:
        st.header("💰 Calculadora")
        st.info("Módulo Premium")
        st.button("Sair", key='logout_calc', on_click=auth.logout)

    st.title("💰 Calculadora Financeira")
    fair_price = data_engine.get_fair_price_snapshot()
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Seus Dados")
        current = st.number_input("Preço Pago (R$/kg)", value=10.50, format="%.2f")
        vol = st.number_input("Volume (Ton)", value=50) * 1000
    
    with c2:
        st.subheader("Resultado")
        delta = current - fair_price
        st.markdown(f"<div style='background:#262730;padding:15px;border-radius:8px;text-align:center'><span style='color:#AAA'>Preço Justo</span><br><span style='color:#FFD700;font-size:2rem'>R$ {fair_price:.2f}</span></div><br>", unsafe_allow_html=True)
        
        if delta > 0:
            loss = delta * vol
            st.markdown(f"<div class='loss-card'><h3 style='color:#FF4B4B'>🔴 Ineficiência</h3><p style='color:white'>Acima em <b>{(delta/fair_price)*100:.1f}%</b>.</p><hr><p style='color:#DDD'>Perda Mensal:</p><h2 style='color:#FF4B4B'>R$ {loss:,.2f}</h2></div>", unsafe_allow_html=True)
        else:
            gain = abs(delta) * vol
            st.markdown(f"<div class='savings-card'><h3 style='color:#00CC96'>🟢 Ótima Compra</h3><p style='color:white'>Abaixo do mercado.</p><h2 style='color:#00CC96'>Economia: R$ {gain:,.2f}</h2></div>", unsafe_allow_html=True)

def view_admin_users():
    """Controlador de Gestão de Usuários"""
    with st.sidebar:
        st.header("👥 Usuários")
        st.button("Sair", key='logout_adm', on_click=auth.logout)

    st.title("👥 Gestão de Acessos")
    
    with st.form("new_user"):
        c1, c2 = st.columns(2)
        u = c1.text_input("Login"); p = c1.text_input("Senha", type="password")
        n = c2.text_input("Nome"); r = c2.selectbox("Perfil", ["client", "admin"])
        mod = st.multiselect("Módulos", ["Monitor", "Calculadora Financeira"], default=["Monitor"])
        
        if st.form_submit_button("Criar Usuário", use_container_width=True):
            ok, msg = database.create_user(u, p, n, r, mod)
            if ok: st.success(msg)
            else: st.error(msg)
            
    if st.button("🔄 Listar Usuários Cadastrados"):
        users = database.list_all_users()
        if users:
            df = pd.DataFrame(users)
            if 'modules' not in df.columns: df['modules'] = "['Monitor']"
            st.dataframe(df[['username', 'name', 'role', 'modules']], use_container_width=True)

def view_backtest():
    """Controlador de Backtest"""
    with st.sidebar:
        st.header("🧪 Lab de Fórmula")
        wti_coef = st.number_input("Coef. WTI", value=0.014, format="%.4f", step=0.001)
        spread = st.number_input("Spread ($)", value=0.35, format="%.2f", step=0.05)
        markup = st.number_input("Markup Brasil", value=1.45, format="%.2f", step=0.05)
        years = st.slider("Anos Históricos", 1, 5, 3)
        st.markdown("---"); st.button("Sair", key='logout_bk', on_click=auth.logout)

    st.title("🧪 Laboratório de Backtest")
    
    df_history = data_engine.get_market_data(years*365)
    
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.subheader("Curva Teórica")
        df_history['PP_Simulado'] = ((df_history['WTI'] * wti_coef) + spread) * df_history['USD_BRL'] * markup
        
        fig, ax = plt.subplots(figsize=(10, 4))
        fig.patch.set_facecolor('#0E1117'); ax.set_facecolor('#0E1117')
        ax.plot(df_history.index, df_history['PP_Simulado'], color='#FFD700', linewidth=2, label='Modelo')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%Y'))
        ax.tick_params(colors='#AAA', rotation=45)
        for s in ax.spines.values(): s.set_color('#333')
        ax.legend(facecolor='#1C1E24', labelcolor='white')
        st.pyplot(fig, use_container_width=True)
        
    with c2:
        st.subheader("Validação (Upload)")
        uploaded = st.file_uploader("CSV (Colunas: Data, Preco)", type="csv")
        
        if uploaded:
            try:
                user_df = pd.read_csv(uploaded)
                comp_df, mape, rmse, msg = data_engine.run_backtest_validation(
                    df_history, user_df, wti_coef, spread, markup
                )
                
                if comp_df is not None:
                    st.success("Validado!")
                    st.metric("Erro Médio (MAPE)", f"{mape*100:.1f}%")
                    st.metric("Erro (Reais)", f"R$ {rmse:.2f}")
                    st.line_chart(comp_df[['PP_Theoretical', 'Preco']], color=["#FFD700", "#00FF00"])
                else:
                    st.warning(msg)
            except Exception as e:
                st.error(f"Erro: {e}")

def view_data_export():
    """NOVO MÓDULO: Visualização e Exportação de Dados (Admin Only)"""
    with st.sidebar:
        st.header("💾 Dados Brutos")
        st.info("Acesso Restrito: Admin")
        st.button("Sair", key='logout_data', on_click=auth.logout)

    st.title("💾 Data Warehouse (Exportação)")
    st.markdown("Acesso direto aos dados históricos do robô ETL.")

    # Filtro de Período
    days = st.slider("Período de Análise (Dias)", 30, 365*5, 365, step=30)
    
    with st.spinner(f"Carregando registros dos últimos {days} dias..."):
        # Busca dados do banco
        df = data_engine.get_market_data(days_back=days)
        
        # Métricas Rápidas
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Registros", len(df))
        c2.metric("Data Inicial", df.index.min().strftime('%d/%m/%Y') if not df.empty else "-")
        c3.metric("Data Final", df.index.max().strftime('%d/%m/%Y') if not df.empty else "-")
        
        # Visualização da Tabela
        st.markdown("### 📋 Visualização Tabular")
        st.dataframe(df, use_container_width=True, height=400)
        
        # Botão de Exportação Excel
        if not df.empty:
            st.markdown("### 📥 Exportação")
            
            # Cria o arquivo Excel na memória RAM (buffer)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Market Data')
                
            st.download_button(
                label="📄 Baixar Planilha Excel (.xlsx)",
                data=buffer.getvalue(),
                file_name=f"gold_rush_data_export.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# -------------------------------------------------------
# FLUXO PRINCIPAL (Main Loop)
# -------------------------------------------------------

if auth.check_session():
    role = st.session_state["user_role"]
    user_modules = st.session_state.get("user_modules", ["Monitor"])
    
    if role == "admin":
        st.sidebar.title("Painel Admin")
        # Adicionada a opção "Dados (XLSX)" no menu do Admin
        opts = ["Monitor", "Calculadora Financeira", "Backtest", "Usuários", "Dados (XLSX)"]
    else:
        st.sidebar.title("Menu")
        opts = user_modules
    
    # Roteamento
    page = st.sidebar.radio("Navegação", opts)
    
    if page == "Monitor": view_monitor(is_admin=(role=="admin"))
    elif page == "Calculadora Financeira": view_calculator()
    elif page == "Backtest": view_backtest()
    elif page == "Usuários": view_admin_users()
    elif page == "Dados (XLSX)": view_data_export()