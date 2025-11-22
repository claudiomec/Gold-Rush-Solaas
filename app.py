import streamlit as st
import pandas as pd
from modules import auth, database, data_engine, ui_components
import io

# 1. Configuração Inicial
st.set_page_config(
    page_title="Gold Rush Analytics", 
    page_icon="🏭", 
    layout="wide", 
    initial_sidebar_state="expanded"
)
ui_components.load_custom_css()

# -------------------------------------------------------
# CONTROLADORES DE MÓDULO (Views)
# -------------------------------------------------------

def view_monitor(is_admin):
    # Sidebar de Parâmetros (Mantida nativa para performance, mas estilizada)
    with st.sidebar:
        st.markdown("### ⚙️ Parâmetros")
        ocean = st.slider("Frete Marítimo (USD)", 0, 300, 60, 10)
        icms = st.selectbox("ICMS (%)", [18, 12, 7, 4])
        freight = st.slider("Frete Interno (R$)", 0.0, 0.5, 0.15, 0.01)
        margin = st.slider("Margem (%)", 0, 20, 10)
        st.markdown("---")

    st.title("Monitor de Custo Industrial")
    st.caption("Commodity: Polipropileno (Homopolímero)")
    
    with st.spinner('Calculando cenários...'):
        df_raw = data_engine.get_market_data()
        df = data_engine.calculate_cost_buildup(df_raw, ocean, freight, icms, margin)
        
        curr = df['PP_Price'].iloc[-1]
        var = (curr/df['PP_Price'].iloc[-7]-1)*100
        
        # KPIs
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Preço Final", f"R$ {curr:.2f}", f"{curr-df['PP_Price'].iloc[-2]:.2f}")
        c2.metric("Tendência (7d)", f"{var:.2f}%", delta_color="inverse")
        c3.metric("Frete Marítimo", f"USD {ocean}")
        c4.metric("Dólar Base", f"R$ {df['USD_BRL'].iloc[-1]:.4f}")
        
        # Novo Gráfico Interativo (Plotly)
        ui_components.render_price_chart(df)
        
        # Novo Alerta Visual (SAC)
        ui_components.render_insight_card(var)

def view_calculator():
    st.title("💰 Calculadora Financeira")
    fair = data_engine.get_fair_price_snapshot()
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Seus Dados")
        curr = st.number_input("Preço Pago (R$)", value=10.50, format="%.2f")
        vol = st.number_input("Volume (Ton)", value=50) * 1000
    with c2:
        st.markdown("### Resultado")
        delta = curr - fair
        
        if delta > 0:
            st.markdown(f"<div class='loss-card'><h3 style='color:#FF4B4B'>🔴 Ineficiência</h3><p style='color:white'>Acima em <b>{(delta/fair)*100:.1f}%</b>.</p><h2 style='color:#FF4B4B'>R$ {delta*vol:,.2f} / mês</h2></div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='savings-card'><h3 style='color:#00CC96'>🟢 Ótima Compra</h3><p style='color:white'>Abaixo do mercado.</p><h2 style='color:#00CC96'>R$ {abs(delta)*vol:,.2f} / mês</h2></div>", unsafe_allow_html=True)

def view_admin_users():
    st.title("👥 Gestão de Acessos")
    
    tab1, tab2 = st.tabs(["Cadastrar Novo", "Listar Todos"])
    
    with tab1:
        with st.form("new"):
            c1, c2 = st.columns(2)
            u = c1.text_input("Login")
            p = c1.text_input("Senha", type="password")
            n = c2.text_input("Nome")
            r = c2.selectbox("Perfil", ["client", "admin"])
            m = st.multiselect("Módulos", ["Monitor", "Calculadora Financeira"], default=["Monitor"])
            if st.form_submit_button("Criar"):
                ok, msg = database.create_user(u, p, n, r, m)
                if ok: st.success(msg)
                else: st.error(msg)
    
    with tab2:
        if st.button("Atualizar Lista"):
            users = database.list_all_users()
            if users:
                df = pd.DataFrame(users)
                if 'modules' not in df.columns: df['modules'] = "['Monitor']"
                st.dataframe(df[['username', 'name', 'role', 'modules']], use_container_width=True)

def view_backtest():
    st.title("🧪 Laboratório de Backtest")
    with st.sidebar:
        st.header("Parâmetros Lab")
        wti = st.number_input("Coef WTI", value=0.014, format="%.4f")
        spr = st.number_input("Spread", value=0.35)
        mkp = st.number_input("Markup", value=1.45)
        yr = st.slider("Anos", 1, 5, 3)
    
    df_hist = data_engine.get_market_data(yr*365)
    
    # Usando Plotly aqui também para consistência
    import plotly.express as px
    df_hist['PP_Simulado'] = ((df_hist['WTI']*wti)+spr)*df_hist['USD_BRL']*mkp
    
    fig = px.line(df_hist, x=df_hist.index, y='PP_Simulado', title="Curva Teórica", color_discrete_sequence=['#FFD700'])
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#EEE'))
    st.plotly_chart(fig, use_container_width=True)

def view_data_export():
    st.title("💾 Data Warehouse (Exportação)")
    days = st.slider("Período (Dias)", 30, 1825, 365)
    df = data_engine.get_market_data(days)
    st.dataframe(df, use_container_width=True)
    
    if not df.empty:
        df_export = df.copy()
        # Garante conversão para string para evitar erro de fuso no Excel
        df_export.index = df_export.index.strftime('%Y-%m-%d')
        df_export.index.name = 'Data'
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_export.to_excel(writer, sheet_name='Market Data')
        st.download_button("📄 Baixar Excel (.xlsx)", data=buffer.getvalue(), file_name="gold_rush_data.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# --- ORQUESTRAÇÃO (MENU NOVO) ---
if auth.check_session():
    role = st.session_state["user_role"]
    
    # Menu Lateral Principal (SAC)
    with st.sidebar:
        if role == "admin":
            st.success(f"Admin: {st.session_state['user_name']}")
        else:
            st.info(f"Cliente: {st.session_state['user_name']}")
            
        # Renderiza o Menu Moderno e captura a seleção
        selected_page = ui_components.render_sidebar_menu(role, st.session_state.get("user_modules", []))

    # Lógica de Logout
    if selected_page == "LOGOUT_ACTION":
        auth.logout()
    
    # Roteamento
    elif selected_page == "Monitor": view_monitor(role=="admin")
    elif selected_page == "Calculadora Financeira": view_calculator()
    elif selected_page == "Backtest": view_backtest()
    elif selected_page == "Usuários": view_admin_users()
    elif selected_page == "Dados (XLSX)": view_data_export()