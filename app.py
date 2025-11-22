import streamlit as st
import pandas as pd
# Importa o novo módulo de email
from modules import auth, database, data_engine, ui_components, report_generator, email_service
import io
import re

# 1. Configuração Inicial
st.set_page_config(page_title="Gold Rush Analytics", page_icon="🏭", layout="wide", initial_sidebar_state="expanded")
ui_components.load_custom_css()

# --- INTERCEPTADOR DE URL (VALIDAÇÃO DE TOKEN) ---
# Verifica se o usuário clicou num link de e-mail
query_params = st.query_params
if "verify_token" in query_params:
    token = query_params["verify_token"]
    with st.spinner("Validando chave de segurança..."):
        success, msg = database.verify_user_token(token)
        if success:
            st.success(f"✅ {msg}")
            st.balloons()
            st.info("Você já pode fazer login no formulário abaixo.")
        else:
            st.error(f"❌ Falha: {msg}")
    # Limpa a URL
    st.query_params.clear()

# Helper de Validação
def is_valid_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email) is not None

# -------------------------------------------------------
# VIEWS
# -------------------------------------------------------

def view_monitor(is_admin):
    with st.sidebar:
        st.markdown("### ⚙️ Parâmetros")
        ocean = st.slider("Frete Marítimo", 0, 300, 60, 10)
        icms = st.selectbox("ICMS", [18, 12, 7, 4])
        freight = st.slider("Frete Interno", 0.0, 0.5, 0.15, 0.01)
        margin = st.slider("Margem", 0, 20, 10)
        st.markdown("---"); st.button("Sair", key='lo1', on_click=auth.logout)

    st.title("Monitor de Custo Industrial")
    col_t, col_b = st.columns([3, 1])
    with col_t: st.caption("Commodity: Polipropileno (Homopolímero)")
    
    with st.spinner('Calculando...'):
        df_raw = data_engine.get_market_data()
        df = data_engine.calculate_cost_buildup(df_raw, ocean, freight, icms, margin)
        curr = df['PP_Price'].iloc[-1]
        var = (curr/df['PP_Price'].iloc[-7]-1)*100
        
        with col_b:
            sug = "Alta" if var > 0.5 else "Baixa" if var < -0.5 else "Estavel"
            pdf = report_generator.generate_pdf_report(df, curr, var, ocean, df['USD_BRL'].iloc[-1], sug)
            st.download_button("📄 Baixar Laudo", pdf, "Laudo.pdf", "application/pdf", use_container_width=True)
        
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Preço Final", f"R$ {curr:.2f}", f"{curr-df['PP_Price'].iloc[-2]:.2f}")
        c2.metric("Tendência", f"{var:.2f}%", delta_color="inverse")
        c3.metric("Frete", f"USD {ocean}"); c4.metric("Dólar", f"R$ {df['USD_BRL'].iloc[-1]:.4f}")
        
        ui_components.render_price_chart(df)
        ui_components.render_insight_card(var)

def view_calculator():
    with st.sidebar: st.header("💰 Calculadora"); st.button("Sair", key='lo2', on_click=auth.logout)
    st.title("💰 Calculadora Financeira")
    fair = data_engine.get_fair_price_snapshot()
    c1, c2 = st.columns(2)
    with c1:
        curr = st.number_input("Preço Pago", value=10.50)
        vol = st.number_input("Volume (Ton)", value=50) * 1000
    with c2:
        delta = curr - fair
        st.markdown(f"<div style='background:#262730;padding:15px;border-radius:8px;text-align:center'><span style='color:#AAA'>Preço Justo</span><br><span style='color:#FFD700;font-size:2rem'>R$ {fair:.2f}</span></div><br>", unsafe_allow_html=True)
        if delta > 0: st.markdown(f"<div class='loss-card'><h3 style='color:#FF4B4B'>🔴 Perda</h3><p style='color:white'>Acima em <b>{(delta/fair)*100:.1f}%</b>.</p><h2 style='color:#FF4B4B'>R$ {delta*vol:,.2f}</h2></div>", unsafe_allow_html=True)
        else: st.markdown(f"<div class='savings-card'><h3 style='color:#00CC96'>🟢 Economia</h3><p style='color:white'>Abaixo do mercado.</p><h2 style='color:#00CC96'>R$ {abs(delta)*vol:,.2f}</h2></div>", unsafe_allow_html=True)

def view_admin_users():
    st.title("👥 Gestão de Acessos")
    t1, t2 = st.tabs(["Novo Usuário", "Base de Usuários"])
    
    with t1:
        with st.form("new"):
            c1, c2 = st.columns(2)
            u = c1.text_input("Login")
            p = c1.text_input("Senha Provisória", type="password")
            n = c2.text_input("Nome"); email = c2.text_input("E-mail (Obrigatório)")
            r = st.selectbox("Perfil", ["client", "admin"])
            m = st.multiselect("Módulos", ["Monitor", "Calculadora Financeira"], default=["Monitor"])
            
            if st.form_submit_button("Criar e Enviar Convite"):
                if not u or not p or not n or not email: st.warning("Preencha todos os campos.")
                elif not is_valid_email(email): st.error("E-mail inválido.")
                else:
                    # 1. Cria no Banco
                    ok, msg, token = database.create_user(u, email, p, n, r, m)
                    if ok:
                        # 2. Envia E-mail
                        # ATENÇÃO: Mude a URL para localhost:8501 se estiver testando localmente
                        link = f"https://gold-rush.streamlit.app/?verify_token={token}"
                        sent, mail_msg = email_service.send_verification_email(email, link)
                        
                        if sent:
                            st.success(f"✅ Usuário criado! Link enviado para {email}")
                        else:
                            st.warning(f"Usuário criado, mas falha no e-mail: {mail_msg}. Token: {token}")
                    else:
                        st.error(msg)
    
    with t2:
        if st.button("Atualizar"):
            users = database.list_all_users()
            if users:
                df = pd.DataFrame(users)
                cols = ['username', 'email', 'role', 'verified']
                show = [c for c in cols if c in df.columns]
                st.dataframe(df[show], use_container_width=True)

# --- MAIN LOOP ---
if not st.session_state.get("password_correct", False):
    # Tela de Login
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.image("https://cdn-icons-png.flaticon.com/512/2534/2534183.png", width=120)
        st.markdown("<h1 style='text-align: center;'>🔐 Gold Rush Access</h1>", unsafe_allow_html=True)
        
        with st.form("login"):
            u = st.text_input("Usuário"); p = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                auth_resp = auth.authenticate(u, p)
                if auth_resp and "error" in auth_resp:
                    st.error(auth_resp["error"]) # Mostra erro de verificação
                elif auth_resp:
                    st.session_state.update({
                        "password_correct": True, 
                        "user_role": auth_resp.get("role", "client"), 
                        "user_name": auth_resp.get("name", u),
                        "user_modules": auth_resp.get("modules", ["Monitor"]) 
                    })
                    st.rerun()
                else: st.error("Credenciais inválidas.")
else:
    # Área Logada
    role = st.session_state["user_role"]
    with st.sidebar:
        if role == "admin": st.success(f"Admin: {st.session_state['user_name']}")
        else: st.info(f"Cliente: {st.session_state['user_name']}")
        pg = ui_components.render_sidebar_menu(role, st.session_state.get("user_modules", []))

    if pg == "LOGOUT_ACTION": auth.logout()
    elif pg == "Monitor": view_monitor(role=="admin")
    elif pg == "Calculadora Financeira": view_calculator()
    elif pg == "Usuários": view_admin_users()
    elif pg == "Dados (XLSX)": from modules.app import view_data_export; view_data_export() # Placeholder
    elif pg == "Backtest": from modules.app import view_backtest; view_backtest() # Placeholder