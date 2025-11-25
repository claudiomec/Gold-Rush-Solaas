import streamlit as st
import pandas as pd
from modules import auth, database, data_engine, ui_components, report_generator, email_service
import io
import re
import time

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
        st.markdown("### ⚙️ Parâmetros")
        ocean = st.slider("Frete Marítimo", 0, 300, 60, 10)
        icms = st.selectbox("ICMS", [18, 12, 7, 4])
        freight = st.slider("Frete Interno", 0.0, 0.5, 0.15, 0.01)
        margin = st.slider("Margem", 0, 20, 10)
        st.markdown("---"); st.button("Sair", key='lo1', on_click=auth.logout)

    st.title("Monitor de Custo Industrial")
    col_t, col_b = st.columns([3, 1])
    with col_t: st.caption("Commodity: Polipropileno")
    
    with st.spinner('Calculando...'):
        df = data_engine.calculate_cost_buildup(data_engine.get_market_data(), ocean, freight, icms, margin)
        
        curr = df['PP_Price'].iloc[-1]
        
        # BUG FIX: Cálculo de variação baseado em tempo (7 dias) e não em linhas fixas
        try:
            target_date = df.index[-1] - pd.Timedelta(days=7)
            # Busca o índice mais próximo da data alvo
            idx = df.index.get_indexer([target_date], method='nearest')[0]
            past_price = df['PP_Price'].iloc[idx]
            var = (curr / past_price - 1) * 100
        except Exception:
            var = 0.0
            
        with col_b:
            sug = "Alta" if var > 0.5 else "Baixa" if var < -0.5 else "Estavel"
            pdf = report_generator.generate_pdf_report(df, curr, var, ocean, df['USD_BRL'].iloc[-1], sug)
            st.download_button("📄 Baixar Laudo", pdf, "Laudo.pdf", "application/pdf", use_container_width=True)
        
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Preço Final", f"R$ {curr:.2f}")
        c2.metric("Tendência", f"{var:.2f}%", delta_color="inverse")
        c3.metric("Frete", f"USD {ocean}"); c4.metric("Dólar", f"R$ {df['USD_BRL'].iloc[-1]:.4f}")
        ui_components.render_price_chart(df); ui_components.render_insight_card(var)

def view_calculator():
    with st.sidebar: st.header("💰 Calculadora"); st.button("Sair", key='lo2', on_click=auth.logout)
    st.title("💰 Calculadora Financeira")
    fair = data_engine.get_fair_price_snapshot()
    c1, c2 = st.columns(2)
    with c1:
        curr = st.number_input("Preço Pago", value=10.50); vol = st.number_input("Volume (Ton)", value=50)*1000
    with c2:
        delta = curr - fair
        st.markdown(f"<div style='background:#262730;padding:15px;border-radius:8px;text-align:center'><span style='color:#AAA'>Preço Justo</span><br><span style='color:#FFD700;font-size:2rem'>R$ {fair:.2f}</span></div><br>", unsafe_allow_html=True)
        if delta > 0: st.markdown(f"<div class='loss-card'><h3 style='color:#FF4B4B'>🔴 Perda</h3><h2 style='color:#FF4B4B'>R$ {delta*vol:,.2f}</h2></div>", unsafe_allow_html=True)
        else: st.markdown(f"<div class='savings-card'><h3 style='color:#00CC96'>🟢 Economia</h3><h2 style='color:#00CC96'>R$ {abs(delta)*vol:,.2f}</h2></div>", unsafe_allow_html=True)

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

def view_backtest():
    st.title("🧪 Lab"); 
    with st.sidebar: st.button("Sair", key='lo4', on_click=auth.logout)
    # ... (código backtest resumido para brevidade) ...
    st.info("Módulo de calibração.")

def view_data_export():
    st.title("💾 Dados"); 
    with st.sidebar: st.button("Sair", key='lo5', on_click=auth.logout)
    df = data_engine.get_market_data(365)
    st.dataframe(df, use_container_width=True)

# --- MAIN ---
if not st.session_state.get("password_correct", False):
    # Login Screen
    c1,c2,c3 = st.columns([1,2,1])
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.image("https://cdn-icons-png.flaticon.com/512/2534/2534183.png", width=120)
        st.markdown("<h1 style='text-align: center;'>🔐 Gold Rush Access</h1>", unsafe_allow_html=True)
        with st.form("login"):
            u = st.text_input("Usuário"); p = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                r = auth.authenticate(u, p)
                if r and "error" in r: st.error(r["error"])
                elif r:
                    st.session_state.update({"password_correct": True, "user_role": r.get("role"), "user_name": r.get("name"), "user_modules": r.get("modules", ["Monitor"])})
                    st.rerun()
                else: st.error("Inválido.")
else:
    role = st.session_state["user_role"]
    with st.sidebar:
        if role == "admin": st.success(f"Admin: {st.session_state['user_name']}")
        else: st.info(f"Cliente: {st.session_state['user_name']}")
        pg = ui_components.render_sidebar_menu(role, st.session_state.get("user_modules", []))

    if pg == "LOGOUT_ACTION": auth.logout()
    elif pg == "Monitor": view_monitor(role=="admin")
    elif pg == "Calculadora Financeira": view_calculator()
    elif pg == "Usuários": view_admin_users()
    elif pg == "Dados (XLSX)": view_data_export()
    elif pg == "Backtest": view_backtest()