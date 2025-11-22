import streamlit as st
import pandas as pd
from modules import auth, database, data_engine, ui_components
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
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
    with st.sidebar:
        if is_admin: st.success(f"Admin: {st.session_state['user_name']}")
        else: st.info(f"Cliente: {st.session_state['user_name']}")
        if database.get_db(): st.caption("🟢 Online")
        st.header("⚙️ Parâmetros")
        ocean = st.slider("Frete Marítimo", 0, 300, 60, 10)
        icms = st.selectbox("ICMS", [18, 12, 7, 4])
        freight = st.slider("Frete Interno", 0.0, 0.5, 0.15, 0.01)
        margin = st.slider("Margem", 0, 20, 10)
        st.markdown("---"); st.button("Sair", key='lo1', on_click=auth.logout)

    st.title("Monitor de Custo Industrial: Polipropileno")
    with st.spinner('Calculando...'):
        df_raw = data_engine.get_market_data()
        df = data_engine.calculate_cost_buildup(df_raw, ocean, freight, icms, margin)
        
        curr = df['PP_Price'].iloc[-1]
        var = (curr/df['PP_Price'].iloc[-7]-1)*100
        
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Preço Final", f"R$ {curr:.2f}", f"{curr-df['PP_Price'].iloc[-2]:.2f}")
        c2.metric("Tendência", f"{var:.2f}%", delta_color="inverse")
        c3.metric("Frete", f"USD {ocean}"); c4.metric("Dólar", f"R$ {df['USD_BRL'].iloc[-1]:.4f}")
        
        ui_components.render_price_chart(df)
        ui_components.render_insight_card(var)

def view_calculator():
    with st.sidebar:
        st.header("💰 Calculadora"); st.button("Sair", key='lo2', on_click=auth.logout)
    st.title("💰 Calculadora Financeira")
    fair = data_engine.get_fair_price_snapshot()
    c1, c2 = st.columns(2)
    with c1:
        curr = st.number_input("Preço Pago (R$)", value=10.50, format="%.2f")
        vol = st.number_input("Volume (Ton)", value=50) * 1000
    with c2:
        delta = curr - fair
        st.markdown(f"<div style='background:#262730;padding:15px;border-radius:8px;text-align:center'><span style='color:#AAA'>Preço Justo</span><br><span style='color:#FFD700;font-size:2rem'>R$ {fair:.2f}</span></div><br>", unsafe_allow_html=True)
        if delta > 0:
            st.markdown(f"<div class='loss-card'><h3 style='color:#FF4B4B'>🔴 Ineficiência</h3><p style='color:white'>Acima em <b>{(delta/fair)*100:.1f}%</b>.</p><h2 style='color:#FF4B4B'>R$ {delta*vol:,.2f}</h2></div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='savings-card'><h3 style='color:#00CC96'>🟢 Ótima Compra</h3><p style='color:white'>Abaixo do mercado.</p><h2 style='color:#00CC96'>R$ {abs(delta)*vol:,.2f}</h2></div>", unsafe_allow_html=True)

def view_admin_users():
    with st.sidebar:
        st.header("👥 Usuários"); st.button("Sair", key='lo3', on_click=auth.logout)
    st.title("👥 Gestão de Acessos")
    with st.form("new"):
        c1, c2 = st.columns(2)
        u = c1.text_input("Login"); p = c1.text_input("Senha", type="password")
        n = c2.text_input("Nome"); r = c2.selectbox("Perfil", ["client", "admin"])
        m = st.multiselect("Módulos", ["Monitor", "Calculadora Financeira"], default=["Monitor"])
        if st.form_submit_button("Criar"):
            ok, msg = database.create_user(u, p, n, r, m)
            if ok: st.success(msg)
            else: st.error(msg)
    if st.button("Listar"):
        users = database.list_all_users()
        if users:
            df = pd.DataFrame(users)
            if 'modules' not in df.columns: df['modules'] = "['Monitor']"
            st.dataframe(df[['username', 'name', 'role', 'modules']], use_container_width=True)

def view_backtest():
    with st.sidebar:
        st.header("🧪 Lab"); st.button("Sair", key='lo4', on_click=auth.logout)
        wti = st.number_input("Coef WTI", value=0.014, format="%.4f")
        spr = st.number_input("Spread", value=0.35)
        mkp = st.number_input("Markup", value=1.45)
        yr = st.slider("Anos", 1, 5, 3)
    
    st.title("🧪 Laboratório de Backtest")
    df_hist = data_engine.get_market_data(yr*365)
    c1, c2 = st.columns([2, 1])
    with c1:
        df_hist['PP'] = ((df_hist['WTI']*wti)+spr)*df_hist['USD_BRL']*mkp
        fig, ax = plt.subplots(figsize=(10, 4)); fig.patch.set_facecolor('#0E1117'); ax.set_facecolor('#0E1117')
        ax.plot(df_hist.index, df_hist['PP'], color='#FFD700'); ax.tick_params(colors='#AAA', rotation=45)
        st.pyplot(fig, use_container_width=True)
    with c2:
        up = st.file_uploader("CSV", type="csv")
        if up:
            try:
                udf = pd.read_csv(up); udf['Data'] = pd.to_datetime(udf['Data']); udf = udf.set_index('Data').sort_index()
                comp, m, r, msg = data_engine.run_backtest_validation(df_hist, udf, wti, spr, mkp)
                if comp is not None:
                    st.success("Validado!"); st.metric("MAPE", f"{m*100:.1f}%"); st.metric("RMSE", f"R$ {r:.2f}")
                    st.line_chart(comp[['PP_Theoretical', 'Preco']], color=["#FFD700", "#00FF00"])
                else: st.warning(msg)
            except Exception as e: st.error(f"Erro: {e}")

def view_data_export():
    with st.sidebar:
        st.header("💾 Dados"); st.button("Sair", key='lo5', on_click=auth.logout)
    st.title("💾 Data Warehouse (Exportação)")
    
    days = st.slider("Período (Dias)", 30, 1825, 365)
    df = data_engine.get_market_data(days)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Registros", len(df))
    c2.metric("Início", df.index.min().strftime('%d/%m/%Y') if not df.empty else "-")
    c3.metric("Fim", df.index.max().strftime('%d/%m/%Y') if not df.empty else "-")
    
    st.dataframe(df, use_container_width=True, height=400)
    
    if not df.empty:
        # --- CORREÇÃO BLINDADA PARA EXCEL ---
        df_export = df.copy()
        
        # Convertendo o índice para STRING (Texto)
        # Isso remove qualquer ambiguidade de fuso horário ou tipo de objeto para o Excel
        df_export.index = df_export.index.strftime('%Y-%m-%d')
        df_export.index.name = 'Data'
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_export.to_excel(writer, sheet_name='Market Data')
            
        st.download_button(
            label="📄 Baixar Excel (.xlsx)",
            data=buffer.getvalue(),
            file_name="gold_rush_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# --- MAIN ---
if auth.check_session():
    r = st.session_state["user_role"]
    m = st.session_state.get("user_modules", ["Monitor"])
    opts = ["Monitor", "Calculadora Financeira", "Backtest", "Usuários", "Dados (XLSX)"] if r == "admin" else m
    
    if r == "admin": st.sidebar.title("Admin")
    else: st.sidebar.title("Menu")
    
    pg = st.sidebar.radio("Ir para:", opts)
    
    if pg == "Monitor": view_monitor(r=="admin")
    elif pg == "Calculadora Financeira": view_calculator()
    elif pg == "Backtest": view_backtest()
    elif pg == "Usuários": view_admin_users()
    elif pg == "Dados (XLSX)": view_data_export()