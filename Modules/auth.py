import streamlit as st
from modules.database import get_db

def authenticate(username, password):
    """
    Verifica credenciais no Firestore (Prioridade) ou Secrets (Backup).
    Retorna dict do usuário ou None.
    """
    # 1. Tentativa Banco de Dados
    db = get_db()
    if db:
        try:
            users_ref = db.collection('users')
            query = users_ref.where('username', '==', username).where('password', '==', password).stream()
            for doc in query:
                return doc.to_dict()
        except Exception as e:
            print(f"Auth DB Error: {e}")
    
    # 2. Tentativa Backup Local (Secrets)
    if "users" in st.secrets and username in st.secrets["users"]:
        if st.secrets["users"][username]["password"] == password:
            user_data = st.secrets["users"][username]
            # Garante compatibilidade de estrutura se não tiver módulos definidos
            if "modules" not in user_data:
                user_data = dict(user_data)
                user_data["modules"] = ["Monitor"]
            return user_data
            
    return None

def login_screen():
    """Renderiza a tela de login."""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.image("https://cdn-icons-png.flaticon.com/512/2534/2534183.png", width=120)
        st.markdown("<h1 style='text-align: center;'>🔐 Gold Rush Access</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #888;'>Inteligência de Mercado Industrial</p>", unsafe_allow_html=True)
        
        with st.form("login"):
            user = st.text_input("Usuário")
            password = st.text_input("Senha", type="password")
            
            if st.form_submit_button("Entrar", use_container_width=True):
                user_data = authenticate(user, password)
                if user_data:
                    st.session_state.update({
                        "password_correct": True,
                        "user_role": user_data.get("role", "client"),
                        "user_name": user_data.get("name", user),
                        "user_modules": user_data.get("modules", ["Monitor"])
                    })
                    st.rerun()
                else:
                    st.error("Credenciais inválidas.")

def check_session():
    """Verifica se há sessão ativa. Se não, mostra login."""
    if st.session_state.get("password_correct", False):
        return True
    login_screen()
    return False

def logout():
    """Encerra sessão."""
    st.session_state["password_correct"] = False
    st.rerun()